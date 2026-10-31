import sys

from mighty_fx import MightyFX, SPCE
from picovector import color, image, shape, vec2
from screens import SCREEN_TYPES, Tile

"""
Fill the panel from a tile whose edges do not meet, using a mirrored repeat so they do.

The tile is a wedge, dark on one side and bright on the other with an arrow across it, so a
plain repeat puts bright hard against dark at every seam.

tile= takes a value per axis. Tile.MIRROR across the panel turns each sideways seam into a
reflection, and the two modes alternate every few seconds.

Press "Boot" to exit the program.
"""

# Constants
ROTATION = 90                    # Quarter turn, to suit how the screen is mounted
TILE = 40                        # The wedge is square, and this is its side
HOLD = 66                        # Frames each mode is held for, about three seconds
INSET = 8                        # How far the arrow sits inside the tile
DARK = color.rgb(16, 16, 40)     # The wedge's shaded side
LIGHT = color.rgb(214, 84, 60)   # And its lit one
MARK = color.rgb(255, 240, 130)  # The arrow, which points the way the wedge brightens
ANTIALIAS = image.X4             # Affordable, the tile being drawn once before the loop starts

# Plain across, then mirrored across, so the same source is seen both ways
MODES = (True, Tile.MIRROR)

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a, rotation=ROTATION)

# One wedge, which the driver repeats to fill the panel
wedge = screen.canvas(TILE, TILE)
wedge.antialias = ANTIALIAS
print(f"a {TILE}x{TILE} wedge filling {screen.height}x{screen.width}")

# A column at a time from dark to light, so the tile's two sides have nothing in common
for x in range(TILE):
    wedge.pen = color.mix(DARK, LIGHT, round(x * 255 / (TILE - 1)))
    wedge.shape(shape.rectangle(x, 0, 1, TILE))

# An arrow pointing the way the wedge brightens, so a reflected copy is plain to see
wedge.pen = MARK
wedge.shape(shape.custom([vec2(INSET, INSET),
                          vec2(INSET, TILE - INSET),
                          vec2(TILE - INSET, TILE // 2)]))

frames = 0

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        across = MODES[frames // HOLD % len(MODES)]

        # Down the panel the tile joins itself, so only the across axis ever changes
        screen.update(wedge, tile=(across, True))
        frames += 1

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
