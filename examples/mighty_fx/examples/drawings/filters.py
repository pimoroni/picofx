from picovector import color, font, image, rect

"""
Drawing: Filters
One picture under eleven filters side by side, to compare what each one does.
Section: Drawing from code
"""

# Entry: screenA: graphics file=filters.py interval=60

# Constants for drawing
BACKGROUND = color.rgb(10, 12, 16)      # Behind the grid
LABEL = color.white                     # The names under each cell
ACROSS = 3                              # Cells across the panel
DOWN = 4                                # And down it
LABEL_TALL = 10                         # Rows kept clear at the foot of a cell for its name
PICTURE = "/examples/assets/gold_macaw_card.png"
LABEL_FACE = font.winds                 # The narrowest ROM pixel face, drawn at its own size

FILTERS = (("none", None, ()),
           ("dither", "dither", ()),
           ("blur", "blur", (2,)),
           ("bloom", "bloom", ()),
           ("crt", "crt", (2, 0.6)),
           ("phosphor", "phosphor", (color.rgb(51, 255, 51),)),
           ("invert", "invert", ()),
           ("mono", "monochrome", ()),
           ("gameboy", "gameboy", ()),
           ("nightvision", "nightvision", ()),
           ("edgeglow", "edgeglow", ()),
           ("synthwave", "synthwave", ()))

try:
    picture = image.load(PICTURE)
except (ValueError, OSError):
    raise RuntimeError(f"'{PICTURE}' is missing or corrupt! Check it is on the drive") from None

drawn = False


def draw(canvas, _elapsed):
    global drawn
    # Nothing moves, so the grid is drawn once and the canvas keeps it
    if drawn:
        return
    drawn = True

    cell = round(canvas.width / ACROSS), round(canvas.height / DOWN)
    tall = cell[1] - LABEL_TALL
    scratch = image(cell[0], tall)
    fits = rect(0, 0, cell[0], tall)

    fit = picture.width, round(picture.width * tall / cell[0])
    whole = rect(0, (picture.height - fit[1]) // 2, fit[0], fit[1])

    canvas.font = LABEL_FACE
    canvas.pen = BACKGROUND
    canvas.clear()

    for index, (name, filtered, settings) in enumerate(FILTERS):
        scratch.blit(picture, whole, fits)
        if filtered is not None:
            getattr(scratch, filtered)(*settings)

        across = (index % ACROSS) * cell[0]
        down = (index // ACROSS) * cell[1]
        canvas.blit(scratch, fits, rect(across, down, cell[0], tall))

        canvas.pen = LABEL
        canvas.text(name, across + 2, down + tall - 2)
