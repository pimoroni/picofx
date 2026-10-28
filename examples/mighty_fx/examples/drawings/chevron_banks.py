from picovector import color, image, shape, vec2

"""
Drawing: Chevron bank
Runway chevrons flashing on one panel, lit and dark in turn, one bank of a pair.
Section: Across several screens
"""

# Entry: screenA: graphics file=chevron_banks.py fps=10

# Constants for drawing
BANK = 0                            # Which bank this panel is, 0 or 1, the two lit in turn
FLASH_MS = 500                      # How long each bank stays lit before the other takes over
CHEVRONS = 3
LIT = color.rgb(255, 204, 0)
UNLIT = color.rgb(51, 51, 34)
BACKGROUND = color.black

# Both states, drawn on the first call from the canvas's size
lit = unlit = None
showing = None


def chevrons(width, height, pen):
    """Draw a panel's chevrons in one pen, each a thick upward point."""
    picture = image(width, height)
    picture.antialias = image.X4
    picture.pen = BACKGROUND
    picture.clear()

    picture.pen = pen
    reach = width * 0.35
    thick = height / (CHEVRONS * 4)
    pitch = height / CHEVRONS
    middle = width / 2
    for index in range(CHEVRONS):
        top = index * pitch + (pitch - reach - thick) / 2
        picture.shape(shape.custom([vec2(middle, top), vec2(middle + reach, top + reach),
                                    vec2(middle + reach, top + reach + thick), vec2(middle, top + thick),
                                    vec2(middle - reach, top + reach + thick), vec2(middle - reach, top + reach)]))
    return picture


def draw(canvas, elapsed):
    global lit, unlit, showing
    if lit is None:
        lit = chevrons(canvas.width, canvas.height, LIT)
        unlit = chevrons(canvas.width, canvas.height, UNLIT)

    # A bank is lit in its own half of each pair of flashes
    on = int(elapsed * 1000) // FLASH_MS % 2 == BANK
    if on != showing:
        canvas.blit(lit if on else unlit, 0, 0)
        showing = on
