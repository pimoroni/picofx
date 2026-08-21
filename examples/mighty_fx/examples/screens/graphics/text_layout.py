import sys
import time

from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import color, font, image, rect

"""
Let a box place the lettering, instead of working out where to put it.

text() takes a rect instead of a position, and align says which corner or edge the lettering
settles against, nine combinations of a horizontal and a vertical, all here at once. The last box
is given more words than it has room for, and overflow=ELLIPSES trims what does not fit.

Align works on the em box the face declares, not the ink inside it, and a face leaves room above
its capitals for accents. So top alignment only looks like it where the word reaches that high:
measured here, "Hello" leaves seven rows empty above it and "Ähoj" leaves one. The vertical middle
inherits the same gap and lands the ink low by half of it.

Press "Boot" to exit the program.
"""

# Constants for drawing
GROUND = color.rgb(10, 12, 16)          # Behind everything
BOX = color.rgb(18, 22, 30)             # A box's own ground
EDGE = color.rgb(70, 90, 110)           # Its border
INK = color.rgb(235, 230, 215)          # The lettering inside it
LABEL = color.rgb(150, 170, 190)        # And the name of the alignment
ACROSS = 3                              # Boxes across, one per horizontal alignment
DOWN = 3                                # And down, one per vertical
PAD = 3                                 # Between a box and its neighbour
INSET = 4                               # Between a box's border and the rect the lettering aligns in
LABEL_TALL = 9                          # Rows a name takes under its box
SPILL_TALL = 76                         # The overflow box at the foot of the panel
BODY_FACE = "more"                      # The tallest ROM pixel face, and it has the accents
LABEL_FACE = "winds"                    # The narrowest ROM pixel face, for the names

MESSAGE = "Ähoj"
PARAGRAPH = ("This paragraph is far longer than its box can hold, which is the whole point of "
             "it. Rather than spilling past the edge and over whatever else is on the panel, "
             "text() lays out as many lines as will fit, trims the last one to the width it "
             "has, and finishes it with an ellipsis so a reader can see that something was "
             "left unsaid. Everything from here on should be missing, and if any of it is "
             "legible on the panel then the box is larger than the words needed and this "
             "example is proving nothing at all. A sentence to make quite sure of it, then "
             "another, and one more after that for luck.")

ALIGNS = ((image.LEFT, "left"), (image.CENTER, "centre"), (image.RIGHT, "right"))
DOWNS = ((image.TOP, "top"), (image.MIDDLE, "middle"), (image.BOTTOM, "bottom"))

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a)

canvas = screen.canvas()
canvas.antialias = image.X4

face = getattr(font, BODY_FACE)
label_face = getattr(font, LABEL_FACE)

CELL = canvas.width / ACROSS, (canvas.height - SPILL_TALL) / DOWN


def framed(box):
    """A box drawn as its own ground inside a border, so its edges can be seen."""
    canvas.pen = EDGE
    canvas.rectangle(box.x - 1, box.y - 1, box.w + 2, box.h + 2)
    canvas.pen = BOX
    canvas.rectangle(box.x, box.y, box.w, box.h)


def inside(box):
    """The rect the lettering aligns in, held clear of the border it sits inside.

    Alignment goes to whatever rect it is given, and it works on the em box the face
    declares, so lettering aligned hard against an edge puts its ink on that edge or a
    pixel past it. A margin is a smaller rect, not a setting.
    """
    return rect(box.x + INSET, box.y + INSET, box.w - INSET * 2, box.h - INSET * 2)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    canvas.pen = GROUND
    canvas.clear()

    for down, (vertical, vname) in enumerate(DOWNS):
        for across, (horizontal, hname) in enumerate(ALIGNS):
            box = rect(round(across * CELL[0] + PAD + 1),
                       round(down * CELL[1] + PAD + 1),
                       round(CELL[0] - PAD * 2 - 2),
                       round(CELL[1] - PAD * 2 - LABEL_TALL))
            framed(box)

            canvas.font = face
            canvas.pen = INK
            canvas.text(MESSAGE, inside(box), align=(horizontal, vertical))

            canvas.font = label_face
            canvas.pen = LABEL
            canvas.text(f"{hname} {vname}", box.x, box.y + box.h + 1)

    # Far more than it can hold, trimmed rather than spilled. This one needs no name over it:
    # the missing end of the paragraph says what happened
    spill = rect(PAD + 1, canvas.height - SPILL_TALL + PAD,
                 canvas.width - PAD * 2 - 2, SPILL_TALL - PAD * 2 - 1)
    framed(spill)
    canvas.font = face
    canvas.pen = INK
    canvas.text(PARAGRAPH, inside(spill), overflow=image.ELLIPSES)

    screen.update(canvas)
    print(f"nine alignments in {CELL[0]:.0f}x{CELL[1]:.0f} boxes, and one overflow")

    # Nothing moves, so the panel holds its frame and this only waits
    while not mighty.boot_pressed():
        time.sleep(0.05)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
