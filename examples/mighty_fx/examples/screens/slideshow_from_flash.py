import os
import time
from mighty_fx import MightyFX, SPCE
from picovector import image, color

"""
Plays a slideshow of .PNG images from a folder, loading each one as it is shown, so
the folder can hold more images than there is memory to keep at once
"""

# Constants
IMAGE_FOLDER = "/frames"      # The folder on your Mighty FX that the images are stored in
IMAGE_WIDTH = 320           # The width the images are stored at, in pixels
IMAGE_HEIGHT = 240          # The height the images are stored at, in pixels
SLEEP_DELAY_MS = 100        # How long each image is displayed for, in milliseconds

# Create a MightyFX object with a screen set on SP/CE port A
mighty = MightyFX(spce_a=SPCE.SCREEN_280)
screen = mighty.screen_a


# Attempt to find all images in the given folder, keeping only their paths
paths = []
try:
    files = sorted(os.listdir(IMAGE_FOLDER))
except OSError:
    files = []

for file in files:
    file = file.rsplit("/", 1)[-1]
    try:
        name, ext = file.rsplit(".", 1)
        if ext.lower() == "png":
            paths.append(f"{IMAGE_FOLDER}/{name}.{ext}")
    except ValueError:
        pass

if len(paths) == 0:
    raise RuntimeError(f"No images found! Copy valid PNGs to your '{IMAGE_FOLDER}' folder (create it if missing)")


index = -1  # Start with -1 so that the first image gets shown

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        frame_start = time.ticks_ms()

        # Move along to the next image index, and wrap it into the range of available images
        index = (index + 1) % len(paths)

        # Decode the image at half size, which is a quarter of the pixels to read from flash
        img = image.load(paths[index], IMAGE_WIDTH // 2, IMAGE_HEIGHT // 2)

        # Update the screen with the latest image, doubling it back up to full size
        screen.update(img, rotation=90, mirror=False, pixel_double=True, v_sync=True,
                      bg_color=color.white)

        # Have the image shown for the rest of its time, if any is left
        elapsed = time.ticks_diff(time.ticks_ms(), frame_start)
        remaining = SLEEP_DELAY_MS - elapsed
        if remaining > 0:
            time.sleep_ms(remaining)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
