import time
from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import image

"""
Alternates between two .PNG images from a folder, each shown for its own duration.
Images must be the same resolution as the screen
"""

# Constants
IMAGE_FOLDER = "/examples/assets"  # The folder the images are in, beside this example
FIRST_IMAGE = "gold_macaw_card.png"        # The name of the first image
SECOND_IMAGE = "red_macaw_card.png"        # The name of the second image
FIRST_DURATION = 1.5
SECOND_DURATION = 0.5

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)


# Attempt to load all images in the given folder
try:
    first_image = image.load(f"{IMAGE_FOLDER}/{FIRST_IMAGE}")
    second_image = image.load(f"{IMAGE_FOLDER}/{SECOND_IMAGE}")
except (ValueError, OSError):
    raise RuntimeError(f"One or both images are missing or corrupt! Check '{FIRST_IMAGE}' and '{SECOND_IMAGE}' are valid PNGs in '{IMAGE_FOLDER}'") from None

showing_second = False

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        if showing_second:
            screen.update(second_image)
            time.sleep(SECOND_DURATION)
        else:
            screen.update(first_image)
            time.sleep(FIRST_DURATION)

        showing_second = not showing_second

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
