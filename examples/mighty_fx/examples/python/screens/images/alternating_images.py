import time
from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import image

"""
Alternate between two PNG pictures, each shown for its own time.

Press "Boot" to exit the program.
"""

# Constants
IMAGE_FOLDER = "/examples/assets"  # The folder the images are in
FIRST_IMAGE = "gold_macaw_card.png"        # The name of the first image
SECOND_IMAGE = "red_macaw_card.png"        # The name of the second image
FIRST_DURATION = 1.5                       # Seconds the first image is shown for
SECOND_DURATION = 0.5                      # And the second

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)


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
