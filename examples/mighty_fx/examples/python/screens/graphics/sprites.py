import sys
import time

from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import brush, color, font, image, mat3, rect, shape, spritesheet

"""
Draw the same sprite with blit() and with an image pen, which can also turn it.

blit() copies a sprite into a rectangle and scales it to whatever size that rectangle is,
which is the cheap way and what the top row does. What it will not do is turn one.

For that the sprite becomes a brush.image pen filling a rectangle whose transform turns it, as
the bottom row does. It costs more than a blit, and can skew or mirror as easily.

Press "Boot" to exit the program.
"""

# Constants for drawing
BACKGROUND = color.rgb(12, 14, 20)      # Behind the sprites
LABEL = color.white                     # The names of the two rows
SPRITE_PATH = "/examples/assets/pirate_face.gif"
LABEL_FACE = font.winds                 # The narrowest ROM pixel face
WIDTHS = (18, 28, 40, 54)               # What the top row blits the sprite at, in pixels
TURNS = (0, 30, 60)                     # Degrees the bottom row turns it
TURNED_AT = 48                          # And how large, the turning needing room around it
TOP_DOWN = 0.30                         # Where the blitted row sits, of the panel's height
TURN_DOWN = 0.68                        # And the turned one

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a)

canvas = screen.canvas()
canvas.antialias = image.X4
canvas.font = LABEL_FACE

# A sprite out of a sheet, which is what a single frame GIF loads as
try:
    sprite = spritesheet.load(SPRITE_PATH).sprite(0)
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{SPRITE_PATH}' is missing! Check it is on the board") from None

print(f"a {sprite.width}x{sprite.height} sprite with {sprite.palette_size} colours,"
      f" blitted at {WIDTHS} and turned {TURNS}")


def spread(count):
    """Space that many things evenly across the panel, returning where each centres."""
    step = canvas.width / (count + 1)
    return [(index + 1) * step for index in range(count)]


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    canvas.pen = BACKGROUND
    canvas.clear()

    # Scaled by the rectangle it is blitted into, which is all a blit needs
    down = canvas.height * TOP_DOWN
    for across, wide in zip(spread(len(WIDTHS)), WIDTHS):
        canvas.blit(sprite, rect(round(across - wide / 2), round(down - wide / 2), wide, wide))

    # The sprite as a pen filling a shape whose transform turns it. A matrix on the pen would tile
    down = canvas.height * TURN_DOWN
    canvas.pen = brush.image(sprite)
    box = shape.rectangle(0, 0, sprite.width, sprite.height)
    for across, turn in zip(spread(len(TURNS)), TURNS):
        # Right to left, the sprite is centred on the origin, scaled, turned, then placed
        box.transform = (mat3().translate(across, down).rotate(turn)
                         .scale(TURNED_AT / sprite.width)
                         .translate(-sprite.width / 2, -sprite.height / 2))
        canvas.shape(box)

    canvas.pen = LABEL
    canvas.text(f"blit: one sprite at {WIDTHS} px", 4, round(canvas.height * TOP_DOWN + 40))
    canvas.text(f"brush.image: one sprite at {TURNS} degrees", 4,
                round(canvas.height * TURN_DOWN + 40))

    screen.update(canvas)

    # Nothing moves, so the panel holds its frame and this only waits
    while not mighty.boot_pressed():
        time.sleep(0.05)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
