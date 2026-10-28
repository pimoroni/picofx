from picovector import color, font

"""
Drawing: Colours
Colours built from the colour module, from even hues to readable text on any background.
Section: Drawing from code
"""

# Entry: screenA: graphics file=colours.py interval=60

# Constants for drawing
BACKGROUND = color.rgb(10, 12, 16)      # Behind everything
TEXT_COLOUR = color.white               # The headings
HUES = 8                                # Swatches in a hue sweep
LIGHTNESS = 165                         # The lightness oklch holds every hue at
CHROMA = 110
BASE_HUE = 25                           # The hue the harmony and tones rows start from
STEPS = 6                               # Swatches in the tones and ramp rows
STRIP = 26                              # How tall a strip of swatches is
GAP = 3                                 # Between a strip and the next heading
LABEL_FACE = font.winds                 # The narrowest ROM pixel face
MARGIN = 4

MIXES = (0, 51, 102, 153, 204, 255)      # Amounts to blend at, on the module's own 0 to 255
MIX_FROM, MIX_TO = color.rgb(230, 60, 40), color.rgb(40, 90, 220)

READ_ON = (color.rgb(240, 230, 60), color.rgb(30, 60, 140), color.rgb(120, 120, 120))
RAMP = ((0.0, color.rgb(255, 90, 40)), (0.5, color.rgb(250, 210, 90)),
        (1.0, color.rgb(60, 120, 230)))

base = color.oklch(LIGHTNESS, CHROMA, BASE_HUE)
drawn = False


def heading(canvas, text, down):
    """Draw a line naming the strip under it, returning where that strip starts."""
    canvas.pen = TEXT_COLOUR
    canvas.text(text, MARGIN, round(down))
    return down + LABEL_FACE.height + 1


def strip(canvas, colours, down):
    """Draw a row of swatches filling the canvas's width, returning where the next heading starts."""
    wide = (canvas.width - MARGIN * 2) / len(colours)
    for index, swatch in enumerate(colours):
        canvas.pen = swatch
        canvas.rectangle(round(MARGIN + index * wide), round(down), round(wide) + 1, STRIP)

    return down + STRIP + GAP


def draw(canvas, _elapsed):
    global drawn
    # Nothing moves, so the page is drawn once and the canvas keeps it
    if drawn:
        return
    drawn = True

    canvas.font = LABEL_FACE
    canvas.pen = BACKGROUND
    canvas.clear()

    down = heading(canvas, "hsv: even numbers, wandering lightness", MARGIN)
    down = strip(canvas, [color.hsv(index * 256 // HUES, 255, 255) for index in range(HUES)], down)

    down = heading(canvas, "oklch: even lightness, same hues", down)
    down = strip(canvas, [color.oklch(LIGHTNESS, CHROMA, index * 360 / HUES) for index in range(HUES)],
                 down)

    down = heading(canvas, "harmony: a base, then its triad and complement", down)
    down = strip(canvas, color.harmony(base, color.TRIAD) + color.harmony(base, color.COMPLEMENT)[1:],
                 down)

    down = heading(canvas, f"tones: one hue in {STEPS} steps", down)
    down = strip(canvas, color.tones(base, STEPS), down)

    down = heading(canvas, f"ramp: {STEPS} steps through colours you name", down)
    down = strip(canvas, color.ramp(RAMP, STEPS), down)

    down = heading(canvas, "mix: an amount of 0 to 255, not 0 to 1", down)
    down = strip(canvas, [color.mix(MIX_FROM, MIX_TO, amount) for amount in MIXES], down)

    down = heading(canvas, "readable_on: text picked for its background", down)
    wide = (canvas.width - MARGIN * 2) / len(READ_ON)
    for index, background in enumerate(READ_ON):
        across = MARGIN + index * wide
        canvas.pen = background
        canvas.rectangle(round(across), round(down), round(wide) + 1, STRIP + LABEL_FACE.height)

        legible = color.readable_on(background, background)
        canvas.pen = legible
        canvas.text("readable", round(across + 3), round(down + 3))
        canvas.text(f"{color.contrast(background, legible):.1f} to 1",
                    round(across + 3), round(down + STRIP - 4))
