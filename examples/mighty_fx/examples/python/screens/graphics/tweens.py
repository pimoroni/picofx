import sys

from mighty_fx import MightyFX, SPCE
from timing import Pacer
from screens import SCREEN_TYPES
from picovector import color, font, image, shape, tween, vec2

"""
Plot what each easing curve does, with a marker running along every one of them at once.

A tween maps a progress from 0 to 1 onto a value between two endpoints along the curve it
was made with, and at() takes the progress.

Each family is shown in its OUT form. IN and INOUT forms exist too, such as tween.QUAD_INOUT.

The endpoints do not have to be numbers. A vec2, a rect or a mat3 works as well, so one tween
can carry a position, a box or a whole transform.

Press "Boot" to exit the program.
"""

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

# One curve per family, each in the form that eases towards the end
CURVES = (("linear", tween.LINEAR), ("sine", tween.SINE_OUT), ("quad", tween.QUAD_OUT),
          ("cubic", tween.CUBIC_OUT), ("quart", tween.QUART_OUT), ("quint", tween.QUINT_OUT),
          ("expo", tween.EXPO_OUT), ("circ", tween.CIRC_OUT), ("back", tween.BACK_OUT),
          ("bounce", tween.BOUNCE_OUT))

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a)

canvas = screen.canvas()
canvas.antialias = image.X4

# A tween from 0 to 1 for each curve, built once and asked for any progress
tweens = [(name, tween(0.0, 1.0, easing=easing)) for name, easing in CURVES]

DOWN = -(-len(CURVES) // ACROSS)        # Rows, rounded up
CELL = canvas.width / ACROSS, canvas.height / DOWN


def box(index):
    """Find the rectangle a curve is plotted in, and the row of lettering under it."""
    left = (index % ACROSS) * CELL[0] + PAD
    top = (index // ACROSS) * CELL[1] + PAD
    return left, top, CELL[0] - PAD * 2, CELL[1] - PAD * 2 - LABEL_FACE.height


# Every curve is fixed, so the grid is drawn once and blitted as each frame's background
backdrop = image(canvas.width, canvas.height)
backdrop.font = LABEL_FACE
backdrop.pen = BACKGROUND
backdrop.clear()

for index, (name, moved) in enumerate(tweens):
    left, top, wide, tall = box(index)

    # Boxes and lettering are square to the pixels, so antialiasing would only soften them
    backdrop.antialias = image.OFF
    backdrop.pen = GRID
    backdrop.rectangle(round(left), round(top), round(wide), round(tall))
    backdrop.pen = MARKER
    backdrop.text(name, round(left), round(top + tall + 1))

    # Only the curve is at an angle, so only it is antialiased. An overshoot is drawn above its box
    backdrop.antialias = image.X4
    backdrop.pen = CURVE
    # Sampled across the box, with a value of 1 at its top as y counts down the panel
    traced = [vec2(left + wide * step / (SAMPLES - 1),
                   top + tall * (1 - moved.at(step / (SAMPLES - 1))))
              for step in range(SAMPLES)]
    backdrop.shape(shape.custom(traced).stroke(TRACE, shape.ALIGN_CENTER | shape.PATH_OPEN))

print(f"{len(tweens)} curves, {SAMPLES} points each, a marker every {CYCLE_MS}ms")

pacer = Pacer()

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        canvas.blit(backdrop, 0, 0)

        # Where every marker is, all of them reading the one progress
        progress = (pacer.elapsed % CYCLE_MS) / CYCLE_MS

        canvas.pen = MARKER
        for index, (_, moved) in enumerate(tweens):
            left, top, wide, tall = box(index)
            canvas.circle(left + wide * progress, top + tall * (1 - moved.at(progress)), 2)

        screen.update(canvas)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
