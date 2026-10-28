from picovector import color, font, image

"""
Drawing: Vector fonts
Every vector face in ROM at three sizes, each writing its own name.
Section: Drawing from code
"""

# Entry: screenA: graphics file=vector_fonts.py interval=60

# Constants for drawing
BACKGROUND = color.navy
TEXT_COLOUR = color.white
RULE = color.rgb(70, 90, 130)
FACES = "/rom/fonts"
# The faces in ROM, in name order. A drawing cannot list a folder, so the names are written out
NAMES = ("AdventPro-Medium", "AlumniSansPinstripe", "Oswald", "PoppinsBlack")
LABEL_FACE = font.winds
SIZES = (15, 22, 29)
MARGIN = 6
GAP = 2
BAND_PAD = 2
SAID_AFTER = 6

faces = [(name, font.load(f"{FACES}/{name}.af")) for name in NAMES]

drawn = False


def draw(canvas, _elapsed):
    global drawn
    # Nothing moves, so the faces are drawn once and the canvas keeps them
    if drawn:
        return
    drawn = True

    canvas.antialias = image.X4
    band = canvas.height / len(faces)

    canvas.pen = BACKGROUND
    canvas.clear()

    for index, (name, face) in enumerate(faces):
        down = index * band + BAND_PAD

        if index:
            canvas.pen = RULE
            canvas.rectangle(0, round(index * band), canvas.width, 1)

        canvas.pen = TEXT_COLOUR
        for size in SIZES:
            canvas.font = face
            canvas.text(name, MARGIN, round(down), font_size=size)

            wide = canvas.measure_text(name, font_size=size)[0]
            canvas.font = LABEL_FACE
            canvas.text(f"{size}px", round(MARGIN + wide + SAID_AFTER),
                        round(down + size - LABEL_FACE.height))

            down += size + GAP
