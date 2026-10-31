import sys
import time
from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import image

"""
Alternate between two PNG pictures, each shown for its own time.

Press "Boot" to exit the program.

Args: Screen size = 2.8, Rotation = 0
"""

# Constants
IMAGE_FOLDER = "/examples/assets"  # The folder the images are in
FIRST_IMAGE = "gold_macaw_card.png"        # The name of the first image
SECOND_IMAGE = "red_macaw_card.png"        # The name of the second image
FIRST_DURATION = 1.5                       # Seconds the first image is shown for
SECOND_DURATION = 0.5                      # And the second

# Which screen is on the port, "2.8" or "1.54", and how far it is turned, 0, 90, 180 or 270, or
# what the effects file passes in args, the size first
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ROTATION = 0 if not sys.argv[2:] else int(sys.argv[2])
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a, rotation=ROTATION)


# Load both images
try:
    first_image = image.load(f"{IMAGE_FOLDER}/{FIRST_IMAGE}")
    second_image = image.load(f"{IMAGE_FOLDER}/{SECOND_IMAGE}")
except (ValueError, OSError):
    mighty.shutdown()
    raise RuntimeError(f"'{IMAGE_FOLDER}/{FIRST_IMAGE}' or '{IMAGE_FOLDER}/{SECOND_IMAGE}' is missing or corrupt! Check both are on the board") from None

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
