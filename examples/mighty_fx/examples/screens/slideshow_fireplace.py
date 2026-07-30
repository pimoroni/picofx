import os
import time
from mighty_fx import MightyFX, SPCE
from picovector import image, color

"""
Plays a looping animation of .PNG frames from a folder, with the boot button turning it
"""

# Constants
IMAGE_FOLDER = "/fireplace"     # The folder on your Mighty FX that the frames are stored in
FRAME_DURATION = 0.01           # How long each frame is displayed for, in seconds

# Create a MightyFX object with a screen set on SP/CE port A
mighty = MightyFX(spce_a=SPCE.SCREEN_280)
screen = mighty.screen_a

# Power the servo strip whilst loading, to show the board is busy
mighty.enable_servo_strips()


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

mighty.disable_servo_strips()


index = -1  # Start with -1 so that the first frame gets shown
rotation = 0
pressed_last = False

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while True:
        pressed = mighty.boot_pressed()

        # Move along to the next frame index, and wrap it into the range of available frames
        index = (index + 1) % len(images)
        img = images[index]

        # Update the screen with the latest frame, held against the top of the screen
        screen.update(img, rotation=rotation, mirror=False, v_sync=True,
                      bg_color=color.white, offset=(None, 0))

        # Have the frame shown for a short time
        time.sleep(FRAME_DURATION)

        # Turn the animation a quarter turn each time the button is newly pressed
        if pressed and not pressed_last:
            rotation = (rotation + 90) % 360

        pressed_last = pressed

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
