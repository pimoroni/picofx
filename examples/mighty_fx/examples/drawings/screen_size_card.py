from picovector import color, font, image, shape

"""
Drawing: Screen size card
A card naming the screen it is drawn on, its diagonal and the canvas it was given.
Section: Screens
"""

# Entry: screenA: graphics file=screen_size_card.py interval=60

# Constants for drawing
BACKGROUND = color.navy                 # The panel behind everything
FOREGROUND = color.white                # The diagonal and every word of it
TITLE = 0.30                            # The size, as a fraction of the panel's width
DETAIL = 0.12                           # The line naming the canvas, the same way
PAD = 5                                 # Clearance the diagonal leaves around lettering
VECTOR_FACE = "/rom/fonts/AdventPro-Medium.af"
TEXT_MIDDLE = 0.805                     # Where this face centres its lettering below the given y, measured
                                        # for this face only

# A canvas the size of a whole panel, either way round, names the panel. Any other size is a
# canvas set by hand or halved by pixel_double, and is named by its pixels alone
SIZES = {(240, 320): '2.8"', (320, 240): '2.8"', (240, 240): '1.54"'}

face = font.load(VECTOR_FACE)
drawn = False


def label(canvas, text, size, down):
    """Draw lettering centred across the panel on a patch of background that stops the diagonal."""
    across = canvas.width / 2
    wide = canvas.measure_text(text, font_size=size)[0]

    canvas.pen = BACKGROUND
    canvas.rectangle(round(across - wide / 2 - PAD), round(down - size / 4 - PAD),
                     round(wide + PAD * 2), round(size / 2 + PAD * 2))

    canvas.pen = FOREGROUND
    canvas.text(text, across - wide / 2, down - TEXT_MIDDLE * size, font_size=size)


def draw(canvas, _elapsed):
    global drawn
    # Nothing changes, so the card is drawn once and the canvas keeps it
    if drawn:
        return
    drawn = True

    canvas.antialias = image.X4
    canvas.pen = BACKGROUND
    canvas.clear()

    # Corner to corner, which is what a screen's size measures
    canvas.pen = FOREGROUND
    canvas.shape(shape.line(0, canvas.height, canvas.width, 0, 1.4))

    canvas.font = face
    shape_of = (canvas.width, canvas.height)
    label(canvas, SIZES.get(shape_of, "?"), round(canvas.width * TITLE), canvas.height / 2)

    # What the canvas is, small and along the bottom
    detail = round(canvas.width * DETAIL)
    turned = "portrait" if canvas.height > canvas.width else "landscape" if canvas.width > canvas.height else "square"
    label(canvas, f"{canvas.width}x{canvas.height}   {turned}", detail, canvas.height - detail + detail // 2)
