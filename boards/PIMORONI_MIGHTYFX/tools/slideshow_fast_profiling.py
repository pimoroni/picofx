# Reports the per-frame timings of a slideshow, to compare screen settings.
#
# stats() reports the last frame by field name. A stall near zero means conversion
# is the constraint; a stall that dominates means the wire is.
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across
# to run it. Swap the SETTINGS line for one of the others to compare.

import os
import time
import machine
from mighty_fx import MightyFX, SPCE
from picovector import image, color
from screens import Screen280

# Panel window and baud rate pairs, as keyword overrides for the screen class.
# 37.5MHz needs clk_peri at 150MHz, since the SPI peripheral only reaches
# clk_peri / 2, so 24MHz is the ceiling at 48MHz.
#
# These pin what the profiles would otherwise choose, so a run compares like with
# like when a setting is deliberately moved off its measured winner.
SETTINGS_240x320_24MHZ = {"width": 240, "height": 320, "bitdepth": 12, "framerate": 46,
                          "baudrate": 24_000_000, "band_lines": 4, "cache_columns": 4}
SETTINGS_240x320_37MHZ = {"width": 240, "height": 320, "bitdepth": 12, "framerate": 55,
                          "baudrate": 37_500_000, "band_lines": 12, "cache_columns": 12}
SETTINGS_240x240_24MHZ = {"width": 240, "height": 240, "bitdepth": 12, "framerate": 60,
                          "baudrate": 24_000_000, "band_lines": 2, "cache_columns": 0}
SETTINGS_240x240_37MHZ = {"width": 240, "height": 240, "bitdepth": 12, "framerate": 60,
                          "baudrate": 37_500_000, "band_lines": 12, "cache_columns": 12}

SETTINGS = SETTINGS_240x240_37MHZ

IMAGE_FOLDER = "/images_r"
ROTATION = 90
MIRROR = False
SLEEP_DELAY = 0.1

machine.freq(150_000_000, 150_000_000)

mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a, **SETTINGS)
display = screen.__display

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
    # Both are fixed at construction, so they are reported once
    print(f"{screen.width}x{screen.height}, {display.band_rows()} rows per band,"
          f" baud {display.baudrate()}")

    while not mighty.boot_pressed():

        # Move along to the next image index, and wrap it into the range of available images
        index = (index + 1) % len(images)
        img = images[index]

        screen.update(img, rotation=ROTATION, mirror=MIRROR, pixel_double=False,
                      bg_color=color.white)

        s = display.stats()
        print(f"pre={s.pre_us}us convert={s.convert_us}us te_wait={s.te_wait_us}us "
              f"frame={s.frame_us}us convert_total={s.convert_total_us}us stall={s.stall_us}us")

        time.sleep(SLEEP_DELAY)

finally:
    mighty.shutdown()
