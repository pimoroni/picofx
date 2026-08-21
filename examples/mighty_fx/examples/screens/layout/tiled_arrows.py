import sys

from mighty_fx import MightyFX, SPCE
from picovector import color, image, shape, vec2
from screens import SCREEN_TYPES, Tile

"""
Fill the panel from a tile that cannot join itself, and let a mirrored repeat rescue it.

The tile is a wedge, dark on one side and bright on the other with an arrow across it, so its
left and right edges have nothing in common and a plain repeat puts bright hard against dark at
every seam.

tile takes a value per axis: Tile.MIRROR reverses every other copy across the panel, turning each
sideways seam into a reflection, while down the panel the tile joins itself and stays a plain
repeat. The two modes alternate every few seconds, which is the comparison.

Press "Boot" to exit the program.
"""

# Constants
ROTATION = 90                    # Quarter turn, to suit how the screen is mounted
TILE = 40                        # The wedge is square, and this is its side
HOLD = 66                        # Frames each mode is held for, about three seconds
INSET = 8                        # How far the arrow sits inside the tile
DARK = (16, 16, 40)              # The wedge's shaded side
LIGHT = (214, 84, 60)            # And its lit one
MARK = color.rgb(255, 240, 130)  # The arrow, which points the way the wedge brightens
ANTIALIAS = image.X4             # Affordable, the tile being drawn once before the loop starts

# Plain across, then mirrored across, so the same source is seen both ways
MODES = (True, Tile.MIRROR)

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a)

# One wedge, which the driver repeats to fill the panel
wedge = screen.canvas(TILE, TILE)
wedge.antialias = ANTIALIAS
print(f"a {TILE}x{TILE} wedge filling {screen.height}x{screen.width}")

# A column at a time from dark to light, so the tile's two sides have nothing in common
for x in range(TILE):
    along = x / (TILE - 1)
    wedge.pen = color.rgb(round(DARK[0] + (LIGHT[0] - DARK[0]) * along),
                          round(DARK[1] + (LIGHT[1] - DARK[1]) * along),
                          round(DARK[2] + (LIGHT[2] - DARK[2]) * along))
    wedge.shape(shape.rectangle(x, 0, 1, TILE))

# An arrow pointing the way the wedge brightens, so a reflected copy is plain to see
wedge.pen = MARK
wedge.shape(shape.custom([vec2(INSET, INSET),
                          vec2(INSET, TILE - INSET),
                          vec2(TILE - INSET, TILE // 2)]))

frames = 0
shown = None

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        across = MODES[frames // HOLD % len(MODES)]
        if across != shown:
            print("mirrored across" if across == Tile.MIRROR else "repeated across")
            shown = across

        # Down the panel the tile joins itself, so only the across axis ever changes
        screen.update(wedge, rotation=ROTATION, tile=(across, True))
        frames += 1

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
