import time
from mighty_fx import MightyFX, SPCE
from picovector import image

"""
Alternates between two .PNG images from a folder with different 'on' and 'off' times.
Images must be the same resolution as the screen
"""

# Constants
IMAGE_FOLDER = "/images"    # The folder on your Mighty FX that the images are stored in
OFF_IMAGE = "test.png"      # The name of 'off' image
ON_IMAGE = "test2.png"      # The name of the 'on' image
OFF_DURATION = 1.5
ON_DURATION = 0.5

# Create a MightyFX object with a screen set on SP/CE port A
mighty = MightyFX(spce_a=SPCE.SCREEN_280)
screen = mighty.screen_a


# Attempt to load all images in the given folder
try:
    off_image = image.load(f"{IMAGE_FOLDER}/{OFF_IMAGE}")
    on_image = image.load(f"{IMAGE_FOLDER}/{ON_IMAGE}")
except (ValueError, OSError):
    raise RuntimeError(f"One or both images are missing or corrupt! Copy valid '{OFF_IMAGE}' and '{ON_IMAGE}' PNGs to your '{IMAGE_FOLDER}' folder (create it if missing)") from None

on = False

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        if on:
            screen.update(on_image)
            time.sleep(ON_DURATION)
        else:
            screen.update(off_image)
            time.sleep(OFF_DURATION)

        on = not on

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
