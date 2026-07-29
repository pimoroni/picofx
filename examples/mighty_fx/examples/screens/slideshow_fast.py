import os
import time
from mighty_fx import MightyFX, SPCE
from picovector import image, color, rect

"""
Plays a slideshow of .PNG images from a folder very fast by passing images directly to the screen.
"""

# Constants
IMAGE_FOLDER = "/images"     # The folder on your Mighty FX that the images are stored in

# Create a MightyFX object with a screen set on SP/CE port A
mighty = MightyFX(spce_a=SPCE.SCREEN_154)
screen = mighty.screen_a


# Attempt to load all images in the given folder
images = []
try:
    files = os.listdir(IMAGE_FOLDER)
except OSError:
    files = []

for i, file in enumerate(files):
    file = file.rsplit("/", 1)[-1]
    try:
        name, ext = file.rsplit(".", 1)
        if ext == "png":
            images.append(image.load(f"{IMAGE_FOLDER}/{name}.png"))
    except Exception:
        pass

if len(images) == 0:
    raise RuntimeError(f"No images found! Copy your PNGs to your '{IMAGE_FOLDER}' folder (create it if missing)")


index = -1  # Start with -1 so that the first image gets shown

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():

        # Move along to the next image index, and wrap it into the range of available images
        index = (index + 1) % len(images)
        img = images[index]

        # Update the screen with the latest image
        screen.update(img, v_sync=True)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
