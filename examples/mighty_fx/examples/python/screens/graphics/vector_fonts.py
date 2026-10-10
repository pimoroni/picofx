import os
import sys
import time

from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import color, font, image

"""
Draw every vector face in ROM at three sizes, each one writing its own name, a band to a face.

A vector face is described as outlines rather than pixels, so the size is an argument at the
point of drawing rather than a property of the face. That is the whole difference from the
pixel faces, which come at one size each and no other: see pixel_fonts.py.

Each size is said beside its line in a pixel face, so the label stays the same size while the
lettering beside it grows.

A face is loaded from its file with font.load, so ROM is not the only place one can live. A
face beside an example, or on the drive, loads exactly the same way.

Press "Boot" to exit the program.
"""

# Constants for drawing
GROUND = color.navy                     # Behind everything
INK = color.white                       # The faces themselves
# Everything is drawn in one white, so a small face is no fainter than a large one
RULE = color.rgb(70, 90, 130)           # The lines dividing one face from the next
FACES = "/rom/fonts"                    # Where the vector faces live
LABEL_FACE = "winds"                    # A ROM pixel face, so a label never changes size
SIZES = (15, 22, 29)                    # What each face is drawn at, filling its band
# Each face draws its own name, so what a line says and what it looks like are one thing
MARGIN = 6
GAP = 2                                 # Between one line and the next
BAND_PAD = 2                            # Between a band and the one above it
SAID_AFTER = 6                          # Between a line and the size said beside it

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a)

canvas = screen.canvas()
canvas.antialias = image.X4

label_face = getattr(font, LABEL_FACE)

# Every .af file in ROM, loaded and kept with the name to call it by
faces = [(name[:-3], font.load(f"{FACES}/{name}"))
         for name in sorted(n for n in os.listdir(FACES) if n.endswith(".af"))]

BAND = canvas.height / len(faces)
print(f"{len(faces)} vector faces at {SIZES}, {BAND:.0f}px a band:"
      f" {', '.join(name for name, _ in faces)}")

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    canvas.pen = GROUND
    canvas.clear()

    for index, (name, face) in enumerate(faces):
        down = index * BAND + BAND_PAD

        # A line between one face's band and the next, so the three sizes above it read as
        # one face rather than as a run of lettering that happens to grow
        if index:
            canvas.pen = RULE
            canvas.rectangle(0, round(index * BAND), canvas.width, 1)

        for size in SIZES:
            canvas.font = face
            canvas.pen = INK
            canvas.text(name, MARGIN, round(down), font_size=size)

            # Said in the pixel face at the foot of the line it belongs to, so the sizes read
            # as a column of the same lettering however large the samples get
            wide = canvas.measure_text(name, font_size=size)[0]
            canvas.font = label_face
            canvas.pen = INK
            canvas.text(f"{size}px", round(MARGIN + wide + SAID_AFTER),
                        round(down + size - label_face.height))

            down += size + GAP

    screen.update(canvas)

    # Nothing moves, so the panel holds its frame and this only waits
    while not mighty.boot_pressed():
        time.sleep(0.05)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
