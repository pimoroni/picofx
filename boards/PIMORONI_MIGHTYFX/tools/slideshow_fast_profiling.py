# Reports the per-frame timings of a slideshow, to compare screen settings.
#
# profile() gives (pre_us, convert_us, te_wait_us, frame_us) for the last frame,
# and stats() gives (convert_total_us, stall_us, bands, write_start_us, baudrate).
# A stall near zero means conversion is the constraint; a stall that dominates
# means the wire is.
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across
# to run it. Swap the SETTINGS line for one of the others to compare.

import os
import time
import machine
from mighty_fx import MightyFX, SPCE, ScreenDef
from picovector import image, color

# Panel window and baud rate pairs. 37.5MHz needs clk_peri at 150MHz, as the SPI
# peripheral can only reach clk_peri / 2, so 24MHz is the ceiling at 48MHz.
SETTINGS_240x320_24MHZ = ScreenDef(24_000_000, 12, 46, 5, 240, 320, 5, 16)
SETTINGS_240x320_37MHZ = ScreenDef(37_500_000, 12, 57, 16, 240, 320, 16, 16)
SETTINGS_240x240_24MHZ = ScreenDef(24_000_000, 12, 55, 5, 240, 240, 5, 16)
SETTINGS_240x240_37MHZ = ScreenDef(37_500_000, 12, 67, 16, 240, 240, 16, 16)

SETTINGS = SETTINGS_240x240_37MHZ

IMAGE_FOLDER = "/images_r"
ROTATION = 90
MIRROR = False
SLEEP_DELAY = 0.1

machine.freq(150_000_000, 150_000_000)

mighty = MightyFX(spce_a=SPCE.SCREEN_280, sdef_a=SETTINGS)
screen = mighty.screen_a
display = screen._display

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

try:
    while not mighty.boot_pressed():

        # Move along to the next image index, and wrap it into the range of available images
        index = (index + 1) % len(images)
        img = images[index]

        screen.update(img, rotation=ROTATION, mirror=MIRROR, pixel_double=False,
                      v_sync=True, bg_color=color.white)

        pre_us, convert_us, te_wait_us, frame_us = display.profile()
        convert_total_us, stall_us, bands, write_start_us, baudrate = display.stats()
        print(f"pre={pre_us}us convert={convert_us}us te_wait={te_wait_us}us frame={frame_us}us "
              f"convert_total={convert_total_us}us stall={stall_us}us bands={bands} baud={baudrate}")

        time.sleep(SLEEP_DELAY)

finally:
    mighty.shutdown()
