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
    splat = worldgen.generate_world(image= _image, prompt=_input.get('prompt')) #Generate 3D world in form of splat

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

if __name__ == '__main__':
    runpod.serverless.start({'handler': handler })
