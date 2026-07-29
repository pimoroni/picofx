import os
import time
from mighty_fx import MightyFX, SPCE
from picovector import image, color
from collections import OrderedDict

"""
Plays a slideshow of .PNG images from several folders, with a short press of the boot
button turning the images, and a long press moving on to the next folder
"""

# The folders on your Mighty FX that the images are stored in, each with the time to
# show a frame for and the (x, y) offset to place it at, where None centres an axis
CONFIG = OrderedDict({
    "/fireplace": {
        "sleep_ms": 60,
        "offset": (None, 0),
    },
    "/car": {
        "sleep_ms": 60,
        "offset": (None, None),
    },
})

LONG_PRESS_MS = 1000    # How long the boot button must be held to change folder, in milliseconds

FOLDERS = list(CONFIG.keys())

# Create a MightyFX object with a screen set on SP/CE port A
mighty = MightyFX(spce_a=SPCE.SCREEN_280)
screen = mighty.screen_a

# Power the servo strip whilst loading, to show the board is busy
mighty.enable_servo_strip()


# Attempt to load all images in the given folder
def load_images(folder):
    images = []
    try:
        files = os.listdir(folder)
    except OSError:
        files = []

    for file in files:
        try:
            name, ext = file.rsplit(".", 1)
            if ext.lower() == "png":
                images.append(image.load(f"{folder}/{name}.{ext}"))
        except (ValueError, OSError):
            print(f"Failed to load: {folder}/{file}")

    return images


folders_images = [load_images(folder) for folder in FOLDERS]

if not any(folders_images):
    raise RuntimeError(f"No images loaded! Copy valid PNGs to your {', '.join(FOLDERS)} folders (create them if missing)")

# Start on the first folder that actually has images
active_folder = 0
while not folders_images[active_folder]:
    active_folder = (active_folder + 1) % len(FOLDERS)

images = folders_images[active_folder]
sleep_delay_ms = CONFIG[FOLDERS[active_folder]]["sleep_ms"]
offset = CONFIG[FOLDERS[active_folder]]["offset"]

mighty.disable_servo_strips()


index = -1  # Start with -1 so that the first image gets shown
rotation = 0
pressed_start = None
long_press_done = False

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while True:
        pressed = mighty.boot_pressed()
        now = time.ticks_ms()

        if pressed:
            if pressed_start is None:
                pressed_start = now
                long_press_done = False

            # Move on to the next folder with images as soon as the press is long enough
            elif not long_press_done and time.ticks_diff(now, pressed_start) >= LONG_PRESS_MS:
                active_folder = (active_folder + 1) % len(FOLDERS)
                while not folders_images[active_folder]:
                    active_folder = (active_folder + 1) % len(FOLDERS)

                images = folders_images[active_folder]
                sleep_delay_ms = CONFIG[FOLDERS[active_folder]]["sleep_ms"]
                offset = CONFIG[FOLDERS[active_folder]]["offset"]
                index = -1
                long_press_done = True
        else:
            # Turn the images a quarter turn if the press ended before it became a long one
            if pressed_start is not None and not long_press_done:
                if time.ticks_diff(now, pressed_start) < LONG_PRESS_MS:
                    rotation = (rotation + 90) % 360

            pressed_start = None
            long_press_done = False

        frame_start = time.ticks_ms()

        # Move along to the next image index, and wrap it into the range of available images
        index = (index + 1) % len(images)
        img = images[index]

        # Update the screen with the latest image
        screen.update(img, rotation=rotation, mirror=False, v_sync=True,
                      bg_color=color.white, offset=offset)

        # Have the image shown for the rest of its time, if any is left
        elapsed = time.ticks_diff(time.ticks_ms(), frame_start)
        remaining = sleep_delay_ms - elapsed
        if remaining > 0:
            time.sleep_ms(remaining)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
