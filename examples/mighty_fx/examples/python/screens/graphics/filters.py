import sys
import time

from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import color, font, image, rect

"""
Show one picture under eleven filters side by side, to compare what each one does.

A filter rewrites every pixel of the image it is called on, so each cell is filtered in a
small image of its own and blitted into place.

An image offers more filters than these, among them c64, cga, chromatic, contrast, duotone,
glitch, grid, noise, onebit, palette_dither, saturation, vignette, wave and zoom.

Press "Boot" to exit the program.

Section: Drawing from code
"""

# Constants for drawing
BACKGROUND = color.rgb(10, 12, 16)      # Behind the grid
LABEL = color.white                     # The names under each cell
ACROSS = 3                              # Cells across the panel
DOWN = 4                                # And down it
LABEL_TALL = 10                         # Rows kept clear at the foot of a cell for its name
PICTURE = "/examples/assets/gold_macaw_card.png"
LABEL_FACE = font.winds                 # The narrowest ROM pixel face, drawn at its own size

# Each filter's label, method and settings, which suit a picture this small
FILTERS = (("none", None, ()),
           ("dither", "dither", ()),
           ("blur", "blur", (2,)),
           ("bloom", "bloom", ()),
           ("crt", "crt", (2, 0.6)),
           ("phosphor", "phosphor", (color.rgb(51, 255, 51),)),
           ("invert", "invert", ()),
           ("mono", "monochrome", ()),
           ("gameboy", "gameboy", ()),
           ("nightvision", "nightvision", ()),
           ("edgeglow", "edgeglow", ()),
           ("synthwave", "synthwave", ()))

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a)

canvas = screen.canvas()
canvas.font = LABEL_FACE

CELL = round(canvas.width / ACROSS), round(canvas.height / DOWN)
TALL = CELL[1] - LABEL_TALL

try:
    picture = image.load(PICTURE)
except (ValueError, OSError):
    mighty.shutdown()
    raise RuntimeError(f"'{PICTURE}' is missing or corrupt! Check it is on the board") from None

print(f"{picture.width}x{picture.height} under {len(FILTERS) - 1} filters,"
      f" {CELL[0]}x{TALL} a cell")

# One scratch image for every cell, refilled from the picture before each filter
scratch = image(CELL[0], TALL)
FITS = rect(0, 0, CELL[0], TALL)

# The picture cropped to the cell's shape about its middle, so no cell comes out squashed. A cell is
# wider than the square picture, so the crop takes a little off its top and foot
FIT = picture.width, round(picture.width * TALL / CELL[0])
WHOLE = rect(0, (picture.height - FIT[1]) // 2, FIT[0], FIT[1])

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    canvas.pen = BACKGROUND
    canvas.clear()

    for index, (name, filtered, settings) in enumerate(FILTERS):
        scratch.blit(picture, WHOLE, FITS)
        if filtered is not None:
            getattr(scratch, filtered)(*settings)   # Called by its name, with its settings

        across = (index % ACROSS) * CELL[0]
        down = (index // ACROSS) * CELL[1]
        canvas.blit(scratch, FITS, rect(across, down, CELL[0], TALL))

        # This face draws three rows below the position it is given, so the band holds it
        canvas.pen = LABEL
        canvas.text(name, across + 2, down + TALL - 2)

    screen.update(canvas)

    # Nothing moves, so the panel holds its frame and this only waits
    while not mighty.boot_pressed():
        time.sleep(0.05)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
