from picovector import brush, color, image, shape, vec2

"""
Drawing: Billboard cased
A folder of posters shown as if each stood in a case behind glass.
Section: Billboards and panels
"""

# Entry: screenA: graphics file=billboard_cased.py fps=2   (a 2.8" screen)

# Constants
POSTERS = "/examples/assets/billboards/portrait"
# The loop, in name order. A drawing cannot list a folder, so the names are written out
NAMES = ("amityville.png", "comedy.png", "crunchweet.png", "falconmouse.png", "jk7.png",
         "radical.png", "scooshers.png", "travel.png", "vitaminy.png", "weevil.png",
         "zeropoint.png")
DWELL_MS = 3000                  # How long a poster is up for
LEVEL = 17
CASE_WIDE = 4
CASE_ROUND = 10
GLASS = color.rgb(28, 44, 66)
SKY = color.rgb(225, 242, 255)
CASE = color.rgb(150, 150, 150)
CASE_LIT = color.rgb(215, 220, 230)
LEAN = 150

BANDS = ((30, 26, 10, 2.0, True), (96, 9, 6, 3.5, True), (150, 34, 14, 1.6, False),
         (206, 14, 8, 2.2, True), (232, 30, 12, 1.4, False))

# The canvas this drawing expects, a 2.8" screen at rotation 0, stated as the pane is built
# before the first call
WIDE, TALL = 240, 320

# Every poster held, palettised as they load, as the sequence player would hold them
posters = []
for name in NAMES:
    path = f"{POSTERS}/{name}"
    try:
        posters.append(image.load(path))
    except (ValueError, OSError):
        raise RuntimeError(f"'{path}' is missing or corrupt! Check it is on the drive") from None

pane = image(WIDE, TALL)
pane.antialias = image.X4


def band(across, half, feather, levels, tone):
    """A diagonal band whose edges fade, as a stack of narrower bands over one another."""
    passes = max(1, feather // 2)
    unit = max(4, round(levels * LEVEL / passes))
    pane.pen = tone.with_alpha(unit)
    for step in range(passes):
        reach = half - step * (feather / passes) / 2
        pane.shape(shape.custom([vec2(across - reach, 0), vec2(across + reach, 0),
                                 vec2(across + reach - LEAN, TALL), vec2(across - reach - LEAN, TALL)]))


def case():
    """Cut the case's window away from the pane so its light survives, then lay the case on it."""
    frame = image(WIDE, TALL)
    frame.antialias = image.X4
    frame.pen = CASE
    frame.clear()

    frame.pen = brush.erase()
    frame.shape(shape.rounded_rectangle(CASE_WIDE, CASE_WIDE, WIDE - CASE_WIDE * 2,
                                        TALL - CASE_WIDE * 2, CASE_ROUND))
    pane.blit(frame, 0, 0)

    pane.pen = CASE_LIT
    pane.shape(shape.rounded_rectangle(CASE_WIDE, CASE_WIDE, WIDE - CASE_WIDE * 2,
                                       TALL - CASE_WIDE * 2, CASE_ROUND).stroke(1))


for across, half, feather, levels, lit in BANDS:
    band(across, half, feather, levels, SKY if lit else GLASS)
case()

shown = None


def draw(canvas, elapsed):
    global shown
    if shown is None and (canvas.width, canvas.height) != (WIDE, TALL):
        raise ValueError(f'this drawing is laid out for {WIDE}x{TALL}, a 2.8" screen at '
                         f"rotation 0, and was given {canvas.width}x{canvas.height}")

    # A poster and the pane over it, laid only when the poster changes
    poster = int(elapsed * 1000) // DWELL_MS % len(posters)
    if poster != shown:
        canvas.blit(posters[poster], 0, 0)
        canvas.blit(pane, 0, 0)
        shown = poster
