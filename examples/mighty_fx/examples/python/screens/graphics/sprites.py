import sys
import time

from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import brush, color, font, image, mat3, rect, shape, spritesheet

"""
Put the same sprite on the panel two ways, because one of them can turn it and one cannot.

blit() copies a sprite into a rectangle and scales it to whatever size that rectangle is,
which is the cheap way and what the top row does. What it will not do is turn one.

For that the sprite becomes a pen, brush.image, filling a rectangle whose transform does the
turning, which is the bottom row. It costs more than a blit and it can do anything a
transform can, so the same call would skew or mirror it as easily.

A single frame GIF arrives as a spritesheet of one sprite, which is how a palettised source
brings its colour table along. Being palettised is also why nothing here fades: setting
alpha on a sprite changes nothing a blit lays down, since a blit of a palettised source
writes palette entries rather than blending. Fading wants a truecolour source.

Press "Boot" to exit the program.
"""

# Constants for drawing
GROUND = color.rgb(12, 14, 20)          # Behind the sprites
LABEL = color.white                     # The names of the two rows
SPRITE_PATH = "/examples/assets/pirate_face.gif"
LABEL_FACE = "winds"                    # The narrowest ROM pixel face
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
canvas.font = getattr(font, LABEL_FACE)

# A sprite out of a sheet, which is what a single frame GIF loads as
sprite = spritesheet.load(SPRITE_PATH).sprite(0)
print(f"a {sprite.width}x{sprite.height} sprite with {sprite.palette_size} colours,"
      f" blitted at {WIDTHS} and turned {TURNS}")


def spread(count):
    """Where each of that many things centres, spaced evenly across the panel."""
    step = canvas.width / (count + 1)
    return [(index + 1) * step for index in range(count)]


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    canvas.pen = GROUND
    canvas.clear()

    # Scaled by the rectangle it is blitted into, which is all a blit needs
    down = canvas.height * TOP_DOWN
    for across, wide in zip(spread(len(WIDTHS)), WIDTHS):
        canvas.blit(sprite, rect(round(across - wide / 2), round(down - wide / 2), wide, wide))

    # Turned, which needs the sprite as a pen and a shape to carry the transform. The pen is
    # given no transform of its own: it fills the shape's own space, so the picture arrives
    # once and turns with it. Handed a matrix as well, it would tile instead
    down = canvas.height * TURN_DOWN
    for across, turn in zip(spread(len(TURNS)), TURNS):
        canvas.pen = brush.image(sprite)
        box = shape.rectangle(0, 0, sprite.width, sprite.height)
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
