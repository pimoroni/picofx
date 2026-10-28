from picovector import color, font, image, shape, tween, vec2

"""
Drawing: Tweens
What each easing curve does, with a marker running along every one of them at once.
Section: Drawing from code
"""

# Entry: screenA: graphics file=tweens.py

# Constants for drawing
BACKGROUND = color.rgb(10, 12, 16)      # Behind everything
GRID = color.rgb(50, 60, 80)            # The box each curve is drawn in
CURVE = color.rgb(120, 200, 255)        # The curve itself
MARKER = color.white                    # And where the progress has reached on it
ACROSS = 2                              # Cells across the panel
SAMPLES = 24                            # Points a curve is drawn from
CYCLE_MS = 2600                         # How long the marker takes to run a curve
PAD = 4                                 # Between a cell's edge and its box
TRACE = 1.3                             # How thick a curve is drawn
LABEL_FACE = font.winds                 # The narrowest ROM pixel face

CURVES = (("linear", tween.LINEAR), ("sine", tween.SINE_OUT), ("quad", tween.QUAD_OUT),
          ("cubic", tween.CUBIC_OUT), ("quart", tween.QUART_OUT), ("quint", tween.QUINT_OUT),
          ("expo", tween.EXPO_OUT), ("circ", tween.CIRC_OUT), ("back", tween.BACK_OUT),
          ("bounce", tween.BOUNCE_OUT))

tweens = [(name, tween(0.0, 1.0, easing=easing)) for name, easing in CURVES]

DOWN = -(-len(CURVES) // ACROSS)        # Rows, rounded up

# A cell's size and the grid every frame starts from, set on the first call from the canvas
CELL = None
backdrop = None


def box(index):
    """Find the rectangle a curve is plotted in, and the row of lettering under it."""
    left = (index % ACROSS) * CELL[0] + PAD
    top = (index // ACROSS) * CELL[1] + PAD
    return left, top, CELL[0] - PAD * 2, CELL[1] - PAD * 2 - LABEL_FACE.height


def setup(canvas):
    """Size the cells to the canvas and draw the fixed grid once."""
    global CELL, backdrop
    CELL = canvas.width / ACROSS, canvas.height / DOWN
    canvas.antialias = image.X4

    backdrop = image(canvas.width, canvas.height)
    backdrop.font = LABEL_FACE
    backdrop.pen = BACKGROUND
    backdrop.clear()

    for index, (name, moved) in enumerate(tweens):
        left, top, wide, tall = box(index)

        backdrop.antialias = image.OFF
        backdrop.pen = GRID
        backdrop.rectangle(round(left), round(top), round(wide), round(tall))
        backdrop.pen = MARKER
        backdrop.text(name, round(left), round(top + tall + 1))

        backdrop.antialias = image.X4
        backdrop.pen = CURVE
        traced = [vec2(left + wide * step / (SAMPLES - 1),
                       top + tall * (1 - moved.at(step / (SAMPLES - 1))))
                  for step in range(SAMPLES)]
        backdrop.shape(shape.custom(traced).stroke(TRACE, shape.ALIGN_CENTER | shape.PATH_OPEN))


def draw(canvas, elapsed):
    if backdrop is None:
        setup(canvas)

    canvas.blit(backdrop, 0, 0)

    progress = (elapsed * 1000 % CYCLE_MS) / CYCLE_MS

    canvas.pen = MARKER
    for index, (_, moved) in enumerate(tweens):
        left, top, wide, tall = box(index)
        canvas.circle(left + wide * progress, top + tall * (1 - moved.at(progress)), 2)
