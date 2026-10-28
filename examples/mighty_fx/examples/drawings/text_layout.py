from picovector import color, font, image, rect

"""
Drawing: Text layout
Text laid out inside boxes that wrap and align it, nine ways at once, and one that overflows.
Section: Drawing from code
"""

# Entry: screenA: graphics file=text_layout.py interval=60

# Constants for drawing
BACKGROUND = color.rgb(10, 12, 16)      # Behind everything
BOX = color.rgb(18, 22, 30)             # A box's own background
EDGE = color.rgb(70, 90, 110)           # Its border
TEXT_COLOUR = color.rgb(235, 230, 215)  # The lettering inside it
LABEL = color.rgb(150, 170, 190)        # And the name of the alignment
ACROSS = 3                              # Boxes across, one per horizontal alignment
DOWN = 3                                # And down, one per vertical
PAD = 3                                 # Between a box and its neighbour
INSET = 4                               # Between a box's border and the rect the lettering aligns in
LABEL_TALL = 9                          # Rows a name takes under its box
SPILL_TALL = 76                         # The overflow box at the foot of the panel
BODY_FACE = font.more                   # The tallest ROM pixel face, and it has the accents
LABEL_FACE = font.winds                 # The narrowest ROM pixel face, for the names

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

drawn = False


def framed(canvas, box):
    """Draw a box as its own background inside a border, so its edges can be seen."""
    canvas.pen = EDGE
    canvas.rectangle(box.x - 1, box.y - 1, box.w + 2, box.h + 2)
    canvas.pen = BOX
    canvas.rectangle(box.x, box.y, box.w, box.h)


def inside(box):
    """Inset the box clear of its border. A margin is a smaller rect, not a setting."""
    return rect(box.x + INSET, box.y + INSET, box.w - INSET * 2, box.h - INSET * 2)


def draw(canvas, _elapsed):
    global drawn
    # Nothing moves, so the boxes are drawn once and the canvas keeps them
    if drawn:
        return
    drawn = True

    canvas.antialias = image.X4
    cell = canvas.width / ACROSS, (canvas.height - SPILL_TALL) / DOWN

    canvas.pen = BACKGROUND
    canvas.clear()

    for down, (vertical, vname) in enumerate(DOWNS):
        for across, (horizontal, hname) in enumerate(ALIGNS):
            box = rect(round(across * cell[0] + PAD + 1),
                       round(down * cell[1] + PAD + 1),
                       round(cell[0] - PAD * 2 - 2),
                       round(cell[1] - PAD * 2 - LABEL_TALL))
            framed(canvas, box)

            canvas.font = BODY_FACE
            canvas.pen = TEXT_COLOUR
            canvas.text(MESSAGE, inside(box), align=(horizontal, vertical))

            canvas.font = LABEL_FACE
            canvas.pen = LABEL
            canvas.text(f"{hname} {vname}", box.x, box.y + box.h + 1)

    spill = rect(PAD + 1, canvas.height - SPILL_TALL + PAD,
                 canvas.width - PAD * 2 - 2, SPILL_TALL - PAD * 2 - 1)
    framed(canvas, spill)
    canvas.font = BODY_FACE
    canvas.pen = TEXT_COLOUR
    canvas.text(PARAGRAPH, inside(spill), overflow=image.ELLIPSES)
