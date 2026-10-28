from picovector import color, spritesheet

"""
Drawing: Bouncing logo
A logo bouncing around the screen, recoloured at each edge, the drifting background showing through.
Section: Animation
"""

# Entry: screenA rotation=90: graphics file=bouncing_logo.py fps=50

# Constants for drawing
LOGO_PATH = "/examples/assets/pirate_face.gif"  # The logo to bounce
HOLLOW_LOGO = True      # Whether the logo's darkest colour is left open for the background
STEP = 3                # How many pixels the logo moves each frame
BG_VALUE = 48           # How bright the background shades are out of 255
HUE_SHIFT = 2           # How far the background hue moves each frame, out of 256
COLORS = (color.rgb(0, 96, 255), color.rgb(255, 32, 96), color.rgb(64, 208, 32),
          color.rgb(255, 176, 0), color.rgb(160, 64, 255))

try:
    logo = spritesheet.load(LOGO_PATH).sprite(0)
except OSError:
    raise RuntimeError(f"'{LOGO_PATH}' is missing! Check it is on the drive") from None

palette = logo.palette

opaque = [i for i in range(logo.palette_size) if palette[i].a != 0]
darkest = min(opaque, key=lambda i: palette[i].r + palette[i].g + palette[i].b)
brighter = [i for i in opaque if i != darkest]

if HOLLOW_LOGO:
    palette[darkest] = color.transparent


def recolor(new_color):
    """Recolour the logo by rewriting every brighter entry of its colour table."""
    for i in brighter:
        palette[i] = new_color


limit_x = limit_y = None
x, y = 0, 0
step_x, step_y = STEP, STEP
index = 0
hue = 0

recolor(COLORS[index])


def draw(canvas, _elapsed):
    global limit_x, limit_y, x, y, step_x, step_y, index, hue
    if limit_x is None:
        limit_x = canvas.width - logo.width
        limit_y = canvas.height - logo.height

    # The entry's offset and background are fixed, so the background is filled and the logo
    # blitted at its place each call
    canvas.pen = color.hsv(hue, 255, BG_VALUE)
    canvas.clear()
    canvas.blit(logo, x, y)

    x += step_x
    y += step_y
    hue = (hue + HUE_SHIFT) % 256

    if x <= 0 or x >= limit_x:
        x = min(max(x, 0), limit_x)
        step_x = -step_x
        index = (index + 1) % len(COLORS)
        recolor(COLORS[index])

    if y <= 0 or y >= limit_y:
        y = min(max(y, 0), limit_y)
        step_y = -step_y
        index = (index + 1) % len(COLORS)
        recolor(COLORS[index])
