import sys
import time

from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import color, font, image, rect

"""
One picture under eleven filters, so the difference is a glance rather than a guess.

A filter is a call on an image and it rewrites every pixel already there, so nothing can be
added to a picture after one runs. That is why each cell here is filtered in a small image
of its own and then blitted into place: filtering the panel would take the whole grid with
it, labels and all.

The list is data rather than eleven calls, so a name and its settings sit together and
another filter is one more line. An image offers more than these: c64, cga, chromatic,
contrast, duotone, glitch, grid, noise, onebit, palette_dither, saturation, vignette, wave
and zoom are all there to try the same way.

Press "Boot" to exit the program.
"""

# Constants for drawing
GROUND = color.rgb(10, 12, 16)          # Behind the grid
LABEL = color.white                     # The names under each cell
ACROSS = 3                              # Cells across the panel
DOWN = 4                                # And down it
LABEL_TALL = 10                         # Rows kept clear at the foot of a cell for its name
PICTURE = "/examples/assets/gold_macaw_card.png"
LABEL_FACE = "winds"                    # The narrowest ROM pixel face, drawn at its own size

# Each filter, and what to pass it. Every one of these was run on the board to see that its
# settings suit a picture this small
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
canvas.font = getattr(font, LABEL_FACE)

CELL = round(canvas.width / ACROSS), round(canvas.height / DOWN)
TALL = CELL[1] - LABEL_TALL

picture = image.load(PICTURE)
print(f"{picture.width}x{picture.height} under {len(FILTERS) - 1} filters,"
      f" {CELL[0]}x{TALL} a cell")

# One scratch, used for every cell in turn: a filter rewrites what it is given, so each cell
# starts from the picture again rather than from the cell before it
scratch = image(CELL[0], TALL)
FITS = rect(0, 0, CELL[0], TALL)

# The picture cropped to the cell's shape about its middle, so no cell comes out squashed
if picture.width * TALL > picture.height * CELL[0]:
    FIT = round(picture.height * CELL[0] / TALL), picture.height
else:
    FIT = picture.width, round(picture.width * TALL / CELL[0])

WHOLE = rect((picture.width - FIT[0]) // 2, (picture.height - FIT[1]) // 2, FIT[0], FIT[1])

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    canvas.pen = GROUND
    canvas.clear()

    for index, (name, filtered, settings) in enumerate(FILTERS):
        scratch.blit(picture, WHOLE, FITS)
        if filtered is not None:
            getattr(scratch, filtered)(*settings)

        across = (index % ACROSS) * CELL[0]
        down = (index // ACROSS) * CELL[1]
        canvas.blit(scratch, FITS, rect(across, down, CELL[0], TALL))

        # This face inks three rows below the position it is given, so the band holds it
        canvas.pen = LABEL
        canvas.text(name, across + 2, down + TALL - 2)

    screen.update(canvas)

    # Nothing moves, so the panel holds its frame and this only waits
    while not mighty.boot_pressed():
        time.sleep(0.05)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
