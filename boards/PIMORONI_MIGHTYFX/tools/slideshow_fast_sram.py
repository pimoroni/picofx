# Plays a slideshow from an SRAM-backed canvas, to measure what the faster source
# buys the conversion.
#
# The GC heap is PSRAM-only on this board, so a plain image() is read over XIP and
# conversion costs about twice as much per pixel. buffer() hands out the SRAM
# region the GC never gets, and load_into() decodes each PNG straight into it, so
# no allocation happens per frame.
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across
# to run it.

import os
import time
import machine
import spidisplay
from mighty_fx import MightyFX, SPCE
from picovector import image, color
from screens import Screen280

# 37.5MHz needs clk_peri at 150MHz, as the SPI peripheral can only reach clk_peri / 2
SETTINGS = {"width": 240, "height": 320, "bitdepth": 12, "framerate": 50,
            "baudrate": 37_500_000, "band_lines": 16, "cache_columns": 16, "spi_frame_bits": 16}

IMAGE_FOLDER = "/images_r"
CANVAS_WIDTH = 320
CANVAS_HEIGHT = 240
ROTATION = 90
SLEEP_DELAY = 0.1

machine.freq(150_000_000, 150_000_000)

mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a, **SETTINGS)
display = screen.display

# The images are landscape and the panel is portrait, so the canvas matches the
# source and the rotation happens on the way out
canvas = image(CANVAS_WIDTH, CANVAS_HEIGHT,
               spidisplay.buffer(CANVAS_WIDTH * CANVAS_HEIGHT * 4))  # RGBA8888
canvas.pen = color.blue
canvas.clear()

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
        if ext == "png":
            paths.append(f"{IMAGE_FOLDER}/{name}.png")
    except ValueError:
        pass

if len(paths) == 0:
    raise RuntimeError(f"No images found! Copy valid PNGs to your '{IMAGE_FOLDER}' folder (create it if missing)")

index = -1  # Start with -1 so that the first image gets shown

try:
    # Both are fixed at construction, so they are reported once
    print(f"{screen.width}x{screen.height}, {display.band_rows()} rows per band,"
          f" baud {display.baudrate()}")

    while not mighty.boot_pressed():

        # Move along to the next image index, and wrap it into the range of available images
        index = (index + 1) % len(paths)

        # Decode into the canvas, scaled to its bounds. A source smaller than the
        # canvas covers only its top left, leaving the rest of the last frame
        canvas.load_into(paths[index])

        screen.update(canvas, rotation=ROTATION, mirror=False,
                      bg_color=color.white)

        s = display.stats()
        print(f"convert_total={s.convert_total_us}us stall={s.stall_us}us")

        time.sleep(SLEEP_DELAY)

finally:
    mighty.shutdown()
