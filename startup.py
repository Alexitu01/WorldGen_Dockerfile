from worldgen import WorldGen
import runpod
from PIL import Image
from datetime import datetime
import torch
import os
from io import BytesIO
import base64

device = torch.device("cuda" if torch.cuda.is_available() else "cpu") # Defines the device based on a strong enough gpu
worldgen = WorldGen(mode="i2s", device=device, low_vram=False) # Worldgen setup

async def handler(event):
    
    _input = event['input']
    #Turn the uploaded bytestring of the image into the image type that worldgen expects: 'Image' object from PIL
    _image = Image.open(BytesIO(base64.b64decode(_input.get('image'))))
    _image.load()
    splat = worldgen.generate_world(image= _image, prompt=_input.get('prompt')) #Generate 3D world in form of splat

    #Define a unique name for the .ply file with the current time.
    filename = str(datetime.now().timestamp()) + ".ply"
    splat.save(filename) #save the .ply file
        
    # Get the file that was saved (This is the only way to get a pointer to the .ply file - worldgen documentation only allows receiving 
    # the generated .ply file if it is specifically written to the disk)
    with open(filename, "rb") as f:
        data = f.read()
    
    #Remove because of lStimited space
    os.remove(filename)
    
    
    return {"base64_result": base64.b64encode(data).decode("ascii")}

if __name__ == '__main__':
    runpod.serverless.start({'handler': handler })