import os
import time
from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import image, color, rect

"""
Plays a slideshow of .PNG images from a folder, drawn through a canvas held in SRAM
"""

# Constants
IMAGE_FOLDER = "/images"     # The folder on your Mighty FX that the images are stored in
SLIDESHOW_DURATION = 0.1     # How long each image is displayed for, in seconds

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# Access the screen and create a canvas to draw to. canvas() places it in SRAM,
# which the screen converts from about twice as fast as the regular heap
canvas = screen.canvas()


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


index = -1  # Start with -1 so that the first image gets shown

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():

        # Move along to the next image index, and wrap it into the range of available images
        index = (index + 1) % len(images)
        img = images[index]

        # Clear the canvas to white
        canvas.pen = color.white
        canvas.clear()

        # Draw the selected image, stretched to fill the canvas
        canvas.blit(img, rect(0, 0, img.width, img.height), rect(0, 0, screen.width, screen.height))

        # Update the screen with the latest canvas
        screen.update(canvas)

        # Have the image shown for a short time
        time.sleep(SLIDESHOW_DURATION)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
