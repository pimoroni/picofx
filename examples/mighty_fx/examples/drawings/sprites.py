from picovector import brush, color, font, image, mat3, rect, shape, spritesheet

"""
Drawing: Sprites
The same sprite drawn with blit() and with an image pen, which can also turn it.
Section: Drawing from code
"""

# Entry: screenA: graphics file=sprites.py interval=60

# Constants for drawing
BACKGROUND = color.rgb(12, 14, 20)
LABEL = color.white
SPRITE_PATH = "/examples/assets/pirate_face.gif"
LABEL_FACE = font.winds
WIDTHS = (18, 28, 40, 54)
TURNS = (0, 30, 60)
TURNED_AT = 48
TOP_DOWN = 0.30
TURN_DOWN = 0.68

try:
    sprite = spritesheet.load(SPRITE_PATH).sprite(0)
except OSError:
    raise RuntimeError(f"'{SPRITE_PATH}' is missing! Check it is on the drive") from None

drawn = False


def spread(width, count):
    """Space that many things evenly across the canvas, returning where each centres."""
    step = width / (count + 1)
    return [(index + 1) * step for index in range(count)]


def draw(canvas, _elapsed):
    global drawn
    # Nothing moves, so the sprites are drawn once and the canvas keeps them
    if drawn:
        return
    drawn = True

    canvas.antialias = image.X4
    canvas.font = LABEL_FACE
    canvas.pen = BACKGROUND
    canvas.clear()

    down = canvas.height * TOP_DOWN
    for across, wide in zip(spread(canvas.width, len(WIDTHS)), WIDTHS):
        canvas.blit(sprite, rect(round(across - wide / 2), round(down - wide / 2), wide, wide))

    # The sprite as a pen filling a shape whose transform turns it. A matrix on the pen would tile
    down = canvas.height * TURN_DOWN
    canvas.pen = brush.image(sprite)
    box = shape.rectangle(0, 0, sprite.width, sprite.height)
    for across, turn in zip(spread(canvas.width, len(TURNS)), TURNS):
        box.transform = (mat3().translate(across, down).rotate(turn)
                         .scale(TURNED_AT / sprite.width)
                         .translate(-sprite.width / 2, -sprite.height / 2))
        canvas.shape(box)

    canvas.pen = LABEL
    canvas.text(f"blit: one sprite at {WIDTHS} px", 4, round(canvas.height * TOP_DOWN + 40))
    canvas.text(f"brush.image: one sprite at {TURNS} degrees", 4,
                round(canvas.height * TURN_DOWN + 40))
