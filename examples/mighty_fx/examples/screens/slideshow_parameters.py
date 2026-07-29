import os
import time
from mighty_fx import MightyFX, SPCE
from picovector import image, color

"""
Plays a slideshow of .PNG images from a folder with different rotations, mirroring, and sizesS
"""

# Constants
IMAGE_FOLDER = "/images"     # The folder on your Mighty FX that the images are stored in

# Create a MightyFX object with a screen set on SP/CE port A
mighty = MightyFX(spce_a=SPCE.SCREEN_280)
screen = mighty.screen_a


# Attempt to load all images in the given folder
images = []
try:
    files = os.listdir(IMAGE_FOLDER)
except OSError:
    files = []

for file in files:
    file = file.rsplit("/", 1)[-1]
    try:
        name, ext = file.rsplit(".", 1)
        if ext == "png":
            images.append(image.load(f"{IMAGE_FOLDER}/{name}.png"))
    except (ValueError, OSError):
        pass

if len(images) == 0:
    raise RuntimeError(f"No images loaded! Copy valid PNGs to your '{IMAGE_FOLDER}' folder (create it if missing)")

index = 0
img = images[index]

hue = 0

rotation = 0
mirror = False
dbl = False

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():

        hue += 5
        hue %= 256

        # Update the screen with the latest canvas
        screen.update(img, rotation=rotation, mirror=mirror, v_sync=True, bg_color=color.hsv(hue, 255, 255), pixel_double=dbl)
        time.sleep(0.25)

        rotation += 90
        if rotation >= 360:
            rotation -= 360

            mirror = not mirror
            if not mirror:
                dbl = not dbl
                if not dbl:
                    # Move along to the next image index, and wrap it into the range of available images
                    index = (index + 1) % len(images)
                    img = images[index]

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
