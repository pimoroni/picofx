import math
import random
from picovector import color, image, mat3, shape

"""
Drawing: Kaleidoscope
A turning kaleidoscope, from a set of small frames drawn once at the start.
Section: Animation
"""

# Entry: screenA rotation=90 offset=160|120 tile=mirror bg=F2ECDE: graphics file=kaleidoscope.py width=160 height=120

# Constants
FRAMES = 48              # Frames in a whole turn, and so how smoothly it turns
BEADS = 44               # Pieces of colour in the circle
HOLD = 2                 # Calls each frame is shown for, which sets the pace
ANTIALIAS = image.X4

BACKGROUND = color.rgb(242, 236, 222)
JEWEL_COLOURS = (color.rgb(214, 40, 96), color.rgb(240, 150, 20), color.rgb(20, 170, 165),
                 color.rgb(110, 70, 210), color.rgb(60, 180, 75), color.rgb(226, 196, 50))

JEWELS = (shape.circle(0, 0, 1), shape.regular_polygon(0, 0, 1, 3),
          shape.regular_polygon(0, 0, 1, 4), shape.regular_polygon(0, 0, 1, 5),
          shape.regular_polygon(0, 0, 1, 6), shape.star(0, 0, 5, 0.45, 1),
          shape.ellipse(0, 0, 1, 0.55), shape.squircle(0, 0, 1))

# The window, a quarter of a 2.8" panel turned, stated as the module body cannot see the canvas.
# The entry's width and height must match
TILE_W, TILE_H = 160, 120

CIRCLE = round(math.sqrt(TILE_W * TILE_W + TILE_H * TILE_H))

SEAM = color.rgb(208, 200, 184)
SEAM_DOWN = shape.rectangle(0, 0, 1, TILE_H)
SEAM_ACROSS = shape.rectangle(0, 0, TILE_W, 1)

STRING = []
for _ in range(BEADS):
    STRING.append((CIRCLE * math.sqrt(random.random()),
                   random.uniform(0, 2 * math.pi),
                   random.uniform(CIRCLE * 0.025, CIRCLE * 0.1),
                   random.choice(JEWEL_COLOURS),
                   random.choice(JEWELS),
                   random.uniform(0, 360)))


def draw_window(target, turn):
    """Draw the window with the beads this far round, skipping beads the reflections already show."""
    target.pen = BACKGROUND
    target.clear()
    for radius, angle, half, colour, jewel, spin in STRING:
        around = angle + 2 * math.pi * turn
        x, y = radius * math.cos(around), radius * math.sin(around)
        if not (-half < x < TILE_W + half and -half < y < TILE_H + half):
            continue
        target.pen = colour
        jewel.transform = mat3().translate(x, y).rotate(spin + turn * 360).scale(half)
        target.shape(jewel)

    target.pen = SEAM
    target.shape(SEAM_DOWN)
    target.shape(SEAM_ACROSS)


# The set is drawn once, one frame per step of the turn, before the first call
wheel = []
for step in range(FRAMES):
    frame = image(TILE_W, TILE_H)
    frame.antialias = ANTIALIAS
    draw_window(frame, step / FRAMES)
    wheel.append(frame)

calls = 0


def draw(canvas, _elapsed):
    global calls
    if calls == 0 and (canvas.width, canvas.height) != (TILE_W, TILE_H):
        raise ValueError(f"this drawing needs width={TILE_W} height={TILE_H} on its entry, "
                         f"and was given {canvas.width}x{canvas.height}")
    canvas.blit(wheel[calls // HOLD % FRAMES], 0, 0)
    calls += 1
