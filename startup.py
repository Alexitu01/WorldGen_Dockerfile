from spag4d import SPAG4D
import runpod
from PIL import Image
from datetime import datetime
import torch
import os
from io import BytesIO
import base64
import subprocess
import sys
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# Download model weights on first run - writes to persistent volume
# Skipped if weights already exist from a previous run
def ensure_models():
    model_dir = os.environ.get("SPAG4D_MODEL_DIR", "/runpod-volume/spag4d_models")
    marker = os.path.join(model_dir, ".models_downloaded")
    if not os.path.exists(marker):
        print("Downloading SPAG4D model weights...")
        subprocess.run(
            [sys.executable, "-m", "spag4d", "download-models"],
            check=True
        )
        open(marker, "w").close()
        print("Model weights downloaded.")
    else:
        print("Model weights already present, skipping download.")
 
ensure_models()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# Initialise SPAG4D once at startup
converter = SPAG4D(device=device)

async def handler(event):
    
    _input = event['input']
    #Turn the uploaded bytestring of the image into the image type that worldgen expects: 'Image' object from PIL
    _image = Image.open(BytesIO(base64.b64decode(_input.get('image'))))
    _image.load()

    #Define a unique name for the .ply file with the current time.
    filename = str(datetime.now().timestamp()) + ".ply"
    
    # Convert panoramic image to Gaussian splat .ply
    # stride=1 gives full resolution output, optimized later
    # scale_factor can be tuned - 1.5 is SPAG4D's default
    result = converter.convert(
        input_path=_image,
        output_path=filename,
        stride=1,
        scale_factor=1.5,
    )
    
    print(f"Generated {result.splat_count:,} splats")
        
    # Get the file that was saved (This is the only way to get a pointer to the .ply file - worldgen documentation only allows receiving 
    # the generated .ply file if it is specifically written to the disk)
    with open(filename, "rb") as f:
        data = f.read()
    
    #Remove because of lStimited space
    os.remove(filename)
    
    
    return {"base64_result": base64.b64encode(data).decode("ascii")}

def get_drive_service():
    # os.environ["..."] gets the service account credentials in base64 format
    # b64decode() decoedes the base64 into bytes
    # decode("utf-8") turns the bytes into a Python str containing the credentials in JSON TEXT
    # json.loads() turns the 'str' into a dict object
    sa_info = json.loads(base64.b64decode(os.environ["GDRIVE_SA_JSON_B64"]).decode("utf-8"))
    
    # This defines the credentials in the correct format that the "build()" method expects:
    # It uses the module service_account, which has the class Credentials, which contains the 
    # method 'from_service_account_info' which according to the docs: "Creates a Credentials instance from parsed service account info"
    creds = service_account.Credentials.from_service_account_info(
        sa_info,
        #Scopes defines what the credentials can give access to - in this 'drive' gives access to everything.
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    #This constructs the resource that allows interaction with the google api.
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def upload_to_drive(filename):
    #Gets the id for the correct folder
    folder_id = os.environ["GDRIVE_FOLDER_ID"]
    
    try:
        service = get_drive_service()
        
        #Json format of the file's name, and what folder to put it in.
        #(Folder is put in an array, because 'parents' infers multiple folders)
        meta_info = {"name": filename, "parents": [folder_id]}
        
        #This tells whatever gets this object, to wrap the file bytes in an uplaod stream object
        #so the file is sent in chunks instead of one big and heavy chunk.
        media = MediaFileUpload(filename, mimetype="application/octet-stream", resumable =True)
        #Creates files with the relevant information, and then returns the field "id".
        create_files = service.files().create(body = meta_info, media_body =media, fields="id").execute()
        file_id = create_files["id"]
        
        #After the file is uploaded it needs to change permissions on the file, so anyone can read it.
        service.permissions().create(fileId=file_id, body={"type": "anyone", "role": "reader"}).execute()

        #Return the file_id and the download url.
        return {
            "file_id": file_id,
            "download_url": f"https://drive.google.com/uc?export=download&id={file_id}"
        }
    except Exception as e:
        return {"error_message": str(e)}

if __name__ == '__main__':
    runpod.serverless.start({'handler': handler })
