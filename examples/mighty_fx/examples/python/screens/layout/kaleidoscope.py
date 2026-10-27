import gc
import math
import random
import sys
import time

from mighty_fx import MightyFX, SPCE
from picovector import color, image, mat3, shape
from screens import SCREEN_TYPES, Tile

"""
Turn a kaleidoscope, from a set of small frames drawn once at startup.

tile=Tile.MIRROR reverses every other repeat, so the panel shows one window of art and three
reflections meeting at the folds. A whole turn of the beads closes the loop exactly.

Every frame is drawn at startup at a quarter of the panel's pixels each, so X4 antialiasing
costs a few seconds once and nothing per frame.

Press "Boot" to exit the program.

Section: Animation
"""

# Constants
ROTATION = 90            # Quarter turn, to suit how the screen is mounted
FRAMES = 48              # Frames in a whole turn, and so how smoothly it turns
BEADS = 44               # Pieces of colour in the circle
HOLD = 2                 # Panel frames each one is shown for, which sets the pace
ANTIALIAS = image.X4     # Affordable here, since every frame is drawn before the loop starts

# The background is the light through a kaleidoscope, and jewel colours read against it where neons wash out
BACKGROUND = color.rgb(242, 236, 222)
JEWEL_COLOURS = (color.rgb(214, 40, 96), color.rgb(240, 150, 20), color.rgb(20, 170, 165),
                 color.rgb(110, 70, 210), color.rgb(60, 180, 75), color.rgb(226, 196, 50))

# One of each jewel at unit radius about the origin, made once and placed by matrix
JEWELS = (shape.circle(0, 0, 1), shape.regular_polygon(0, 0, 1, 3),
          shape.regular_polygon(0, 0, 1, 4), shape.regular_polygon(0, 0, 1, 5),
          shape.regular_polygon(0, 0, 1, 6), shape.star(0, 0, 5, 0.45, 1),
          shape.ellipse(0, 0, 1, 0.55), shape.squircle(0, 0, 1))

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a, rotation=ROTATION)

# The window is a quarter of the panel as turned, so its four reflections fill it
TILE_W, TILE_H = screen.height // 2, screen.width // 2

# The circle reaches the window's far corner, sized in frame pixels so nothing is scaled
CIRCLE = round(math.sqrt(TILE_W * TILE_W + TILE_H * TILE_H))

# A thin line down each fold, as a real kaleidoscope shows its mirrors. The reflection doubles it
SEAM = color.rgb(208, 200, 184)
SEAM_DOWN = shape.rectangle(0, 0, 1, TILE_H)
SEAM_ACROSS = shape.rectangle(0, 0, TILE_W, 1)


# Every bead's place, scattered afresh each run.
# A square-rooted random radius spreads the beads evenly over the area
STRING = []
for _ in range(BEADS):
    # Add a bead at a random place in the circle, with its own size, colour, jewel and tilt
    STRING.append((CIRCLE * math.sqrt(random.random()),
                   random.uniform(0, 2 * math.pi),
                   random.uniform(CIRCLE * 0.025, CIRCLE * 0.1),
                   random.choice(JEWEL_COLOURS),
                   random.choice(JEWELS),
                   random.uniform(0, 360)))


def draw_window(canvas, turn):
    """Draw the window with the beads this far round, skipping beads the reflections already show."""
    canvas.pen = BACKGROUND
    canvas.clear()
    for radius, angle, half, colour, jewel, spin in STRING:
        around = angle + 2 * math.pi * turn
        x, y = radius * math.cos(around), radius * math.sin(around)
        if not (-half < x < TILE_W + half and -half < y < TILE_H + half):
            continue

        # A bead turns as it travels as on a real wheel, at no extra cost in the matrix
        canvas.pen = colour
        jewel.transform = mat3().translate(x, y).rotate(spin + turn * 360).scale(half)
        canvas.shape(jewel)

    # Over the beads, since a mirror's edge is in front of what it reflects
    canvas.pen = SEAM
    canvas.shape(SEAM_DOWN)
    canvas.shape(SEAM_ACROSS)


# The set is drawn once, one frame per step of the turn
gc.collect()
before = gc.mem_free()
print(f"> Drawing {FRAMES} frames of {TILE_W}x{TILE_H} ...")
started = time.ticks_ms()
wheel = []
for step in range(FRAMES):
    frame = image(TILE_W, TILE_H)
    frame.antialias = ANTIALIAS
    draw_window(frame, step / FRAMES)
    wheel.append(frame)
took = time.ticks_diff(time.ticks_ms(), started)
gc.collect()
print(f"the set holds {(before - gc.mem_free()) // 1024}KB and took {took / 1000:.1f}s,"
      f" against {FRAMES * screen.width * screen.height * 4 // 1024}KB of panel-sized frames")

frames = 0

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Four mirrored reflections of the window, offset one window along and down
        # so the circle's middle lands in the panel's middle
        screen.update(wheel[frames // HOLD % FRAMES],
                      offset=(TILE_W, TILE_H), tile=Tile.MIRROR, bg_color=BACKGROUND)
        frames += 1

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
