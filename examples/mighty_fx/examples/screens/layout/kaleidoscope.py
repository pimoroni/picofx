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

tile=Tile.MIRROR repeats a source like tile=True does, but reverses every other repeat, so
each seam is a reflection instead of a join. The panel therefore shows one quarter of art and
three reflections of it meeting at the folds, which is what a kaleidoscope does with mirrors.

The art is a circle of beads, scattered afresh on every run, and each frame is the window a
kaleidoscope would actually see: one corner of the window is the middle of the circle, where
the mirrors meet. Every frame turns the beads a little further round, and after a whole turn
the set is back where it started, so the loop closes exactly.

A bead crossing the edge of the window is drawn as far as it goes and its reflection
finishes it, which is a bead touching a mirror. Nothing has to be arranged to avoid the
edges: the mirrors take care of them.

The frames live in the heap, since nothing draws to them again and the fast SRAM is better
left for anything that does. Each is a quarter of the pixels of a panel-sized frame, which
is what makes a whole turn of them affordable at all.

Drawing before the loop rather than in it also buys the quality: X4 antialiasing is four
times the rasterising, which is a few seconds once at startup and nothing at all per frame.

How fast it turns is FRAMES against HOLD: more frames is a finer step and more memory, and a
longer hold slows the turn without costing anything but smoothness. A whole turn here takes
about four seconds.

Press "Boot" to exit the program.
"""

# Constants
ROTATION = 90            # Quarter turn, to suit how the screen is mounted
FRAMES = 48              # Frames in a whole turn, and so how smoothly it turns
BEADS = 44               # Pieces of colour in the circle
HOLD = 2                 # Panel frames each one is shown for, which sets the pace
ANTIALIAS = image.X4     # Affordable here, since every frame is drawn before the loop starts

# A kaleidoscope is held up to the light, so the ground is the light coming through it and
# the beads are what stands in the way. The inks are jewel colours rather than neons, which
# is what reads against a lit ground: a bright one washes out against it
GROUND = color.rgb(242, 236, 222)
INKS = (color.rgb(214, 40, 96), color.rgb(240, 150, 20), color.rgb(20, 170, 165),
        color.rgb(110, 70, 210), color.rgb(60, 180, 75), color.rgb(226, 196, 50))

# One of each jewel, cut at a radius of one about the origin and placed by matrix later. A
# shape costs far more to make than a matrix does, so the whole set is made here and every
# bead borrows from it
JEWELS = (shape.circle(0, 0, 1), shape.regular_polygon(0, 0, 1, 3),
          shape.regular_polygon(0, 0, 1, 4), shape.regular_polygon(0, 0, 1, 5),
          shape.regular_polygon(0, 0, 1, 6), shape.star(0, 0, 5, 0.45, 1),
          shape.ellipse(0, 0, 1, 0.55), shape.squircle(0, 0, 1))

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a)

# The window has to be a quarter of the panel for its four reflections to fill the panel
# exactly, so it comes from the panel and not from a pair of numbers. The quarter turn
# swaps the sides, this being the panel as it is mounted rather than as it is wired
TILE_W, TILE_H = screen.height // 2, screen.width // 2

# The circle reaches the window's far corner, the furthest point from the middle that the
# mirrors show. Taking the radius from the window keeps a pixel of the circle a pixel of the
# frame, with no scaling anywhere
CIRCLE = round(math.sqrt(TILE_W * TILE_W + TILE_H * TILE_H))

# A real kaleidoscope shows its mirrors as two thin lines where they meet, so the window
# takes one along each of the edges the folds run down. The reflection lays its own line
# alongside, which is why one pixel each is enough to read
SEAM = color.rgb(208, 200, 184)
SEAM_DOWN = shape.rectangle(0, 0, 1, TILE_H)
SEAM_ACROSS = shape.rectangle(0, 0, TILE_W, 1)


# Where every bead sits in the circle, scattered afresh on each run, so no two turns of
# the kaleidoscope are the same one. Radius goes by the square root of a random number, so
# the beads spread evenly over the area instead of crowding the middle, and each bead takes
# a spin of its own to start from
STRING = []
for _ in range(BEADS):
    STRING.append((CIRCLE * math.sqrt(random.random()),
                   random.uniform(0, 2 * math.pi),
                   random.uniform(CIRCLE * 0.025, CIRCLE * 0.1),
                   random.choice(INKS),
                   random.choice(JEWELS),
                   random.uniform(0, 360)))


def draw_window(canvas, turn):
    """The window as it looks with the beads this far round, in tile pixels.

    Only the beads that reach into the window are drawn. The rest are what the reflections
    are already showing, so drawing them would be drawing the same beads twice.
    """
    canvas.pen = GROUND
    canvas.clear()
    for radius, angle, half, ink, jewel, spin in STRING:
        around = angle + 2 * math.pi * turn
        x, y = radius * math.cos(around), radius * math.sin(around)
        if not (-half < x < TILE_W + half and -half < y < TILE_H + half):
            continue

        # A bead turns with the wheel as well as travelling round it, since a jewel carried
        # round on a real one keeps its face to the middle. The turn goes into the matrix
        # with the placement, so it costs a jewel with corners nothing over a round one
        canvas.pen = ink
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
        # Both axes mirrored, so the panel is four reflections of the window meeting at the
        # folds, and the window underneath them is the only thing that changes.
        #
        # The offset puts the folds in the right place: a window placed one of itself along
        # and down lands the middle of the circle in the middle of the panel. Without it a
        # fold runs through the middle instead.
        screen.update(wheel[frames // HOLD % FRAMES], rotation=ROTATION,
                      tile=Tile.MIRROR, bg_color=GROUND, offset=(TILE_W, TILE_H))
        frames += 1

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
