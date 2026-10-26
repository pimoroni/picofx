import sys

from mighty_fx import MightyFX, SPCE
from picovector import color, shape
from screens import SCREEN_TYPES

"""
Fill the whole panel with a brick wall drawn from a tile of 32 by 32 pixels.

That tile is a seventy-fifth of the full-size image a wall covering the panel would need, so
tiling is the difference between an asset that fits anywhere and one that has to be budgeted for.

A running bond keeps the tile small, two courses being everything the pattern does. The brick
starting halfway along the upper course is drawn at both ends of the tile, as a shape crossing an
edge must appear at the opposite edge too.

Press "Boot" to exit the program.
"""

# Constants
ROTATION = 90            # Quarter turn, to suit how the screen is mounted
BRICK_W = 32             # A brick and its mortar, which is the tile's width
BRICK_H = 16             # A course, two of which is the tile's height
MORTAR = 3               # How wide the gaps between bricks are
STEP = 1                 # Pixels the wall slides each frame, to show it has no seam
FACE = color.rgb(168, 68, 52)
FACE_TOP = color.rgb(196, 96, 76)     # The weathered top edge of a brick
FACE_FOOT = color.rgb(132, 48, 38)    # And its shaded foot
GROUT = color.rgb(196, 188, 172)

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a, rotation=ROTATION)

# Two courses of one brick, and the driver makes a wall of it
wall = screen.canvas(BRICK_W, BRICK_H * 2)
print(f"a {BRICK_W}x{BRICK_H * 2} wall tile, {BRICK_W * BRICK_H * 2 * 4 // 1024}KB,"
      f" filling {screen.height}x{screen.width}")


def brick(x, y):
    """Draw one brick at (x, y), its face laid over the mortar with a lit top and dark foot."""
    width, height = BRICK_W - MORTAR, BRICK_H - MORTAR
    wall.pen = FACE_TOP
    wall.shape(shape.rectangle(x, y, width, height))
    wall.pen = FACE
    wall.shape(shape.rectangle(x, y + 1, width, height - 2))
    wall.pen = FACE_FOOT
    wall.shape(shape.rectangle(x, y + height - 1, width, 1))


# Mortar first, since every brick is laid over it and the gaps are what is left showing
wall.pen = GROUT
wall.clear()

# The lower course from the edge, the upper half a brick along and drawn at both ends
brick(0, 0)
brick(BRICK_W // 2, BRICK_H)
brick(BRICK_W // 2 - BRICK_W, BRICK_H)

frames = 0

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Slide the wall to show it has no seam
        screen.update(wall, offset=(-frames * STEP, -frames * STEP), tile=True)
        frames += 1

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
