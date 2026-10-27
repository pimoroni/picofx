import os
import sys
import time

from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import color, font, image

"""
Draw every vector face in ROM at three sizes, each writing its own name.

A vector face is drawn from outlines, so text() sizes it. A pixel face is fixed (pixel_fonts.py).

A face is loaded from its file with font.load, so ROM is not the only place one can live. A
face beside an example, or on the drive, loads exactly the same way.

Press "Boot" to exit the program.

Section: Drawing from code
"""

# Constants for drawing
BACKGROUND = color.navy                 # Behind everything
TEXT_COLOUR = color.white               # The faces themselves
RULE = color.rgb(70, 90, 130)           # The lines dividing one face from the next
FACES = "/rom/fonts"                    # Where the vector faces live
LABEL_FACE = font.winds                 # A ROM pixel face, so a label never changes size
SIZES = (15, 22, 29)                    # What each face is drawn at, filling its band
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

# Every .af file in ROM, loaded and kept with the name to call it by
faces = [(name[:-3], font.load(f"{FACES}/{name}"))
         for name in sorted(n for n in os.listdir(FACES) if n.endswith(".af"))]

BAND = canvas.height / len(faces)
print(f"{len(faces)} vector faces at {SIZES}, {BAND:.0f}px a band:"
      f" {', '.join(name for name, _ in faces)}")

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    canvas.pen = BACKGROUND
    canvas.clear()

    for index, (name, face) in enumerate(faces):
        down = index * BAND + BAND_PAD

        # Rule a line above every band but the first
        if index:
            canvas.pen = RULE
            canvas.rectangle(0, round(index * BAND), canvas.width, 1)

        canvas.pen = TEXT_COLOUR
        for size in SIZES:
            canvas.font = face
            canvas.text(name, MARGIN, round(down), font_size=size)

            # The size, in a pixel face so it never grows
            wide = canvas.measure_text(name, font_size=size)[0]
            canvas.font = LABEL_FACE
            canvas.text(f"{size}px", round(MARGIN + wide + SAID_AFTER),
                        round(down + size - LABEL_FACE.height))

            down += size + GAP

    screen.update(canvas)

    # Nothing moves, so the panel holds its frame and this only waits
    while not mighty.boot_pressed():
        time.sleep(0.05)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
