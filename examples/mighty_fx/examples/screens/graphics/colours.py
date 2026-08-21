import sys
import time

from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import color, font

"""
Ask the colour module for a set of colours rather than picking them by hand.

The first two strips are the same eight hues twice, once through hsv and once through oklch.
hsv holds the numbers even and lets the lightness wander, so its yellow glares and its blue
sinks; oklch holds the lightness even instead, which is what makes a row of it read as one
family. That is the whole reason to reach for it.

Under those, three calls that hand back a set: harmony() for hues that belong together,
tones() for one hue from dark to light, and ramp() for the steps between colours you name.
Then readable_on(), which picks lettering that can be read against a given ground, with the
contrast it managed said beside it.

One thing to know before using any of them: an amount in this module runs 0 to 255, not 0 to
1, so mix(a, b, 0.5) hands back a unchanged where mix(a, b, 128) is the halfway blend. The
same goes for saturate, darken and lighten.

Press "Boot" to exit the program.
"""

# Constants for drawing
GROUND = color.rgb(10, 12, 16)          # Behind everything
INK = color.white                       # The headings
HUES = 8                                # Swatches in a hue sweep
LIGHTNESS = 165                         # The lightness oklch holds every hue at
CHROMA = 110
BASE_HUE = 25                           # The hue the harmony and tones rows start from
STEPS = 6                               # Swatches in the tones and ramp rows
STRIP = 26                              # How tall a strip of swatches is
GAP = 3                                 # Between a strip and the next heading
LABEL_FACE = "winds"                    # The narrowest ROM pixel face
MARGIN = 4

MIXES = (0, 51, 102, 153, 204, 255)      # Amounts to blend at, on the module's own 0 to 255
MIX_FROM, MIX_TO = color.rgb(230, 60, 40), color.rgb(40, 90, 220)

READ_ON = (color.rgb(240, 230, 60), color.rgb(30, 60, 140), color.rgb(120, 120, 120))
RAMP = ((0.0, color.rgb(255, 90, 40)), (0.5, color.rgb(250, 210, 90)),
        (1.0, color.rgb(60, 120, 230)))

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a)

canvas = screen.canvas()
label_face = getattr(font, LABEL_FACE)
canvas.font = label_face

base = color.oklch(LIGHTNESS, CHROMA, BASE_HUE)


def heading(text, down):
    """A line naming the strip under it, and where that strip starts."""
    canvas.pen = INK
    canvas.text(text, MARGIN, round(down))
    return down + label_face.height + 1


def strip(colours, down, tall=STRIP):
    """A row of swatches filling the panel's width, and where the next heading starts."""
    wide = (canvas.width - MARGIN * 2) / len(colours)
    for index, swatch in enumerate(colours):
        canvas.pen = swatch
        canvas.rectangle(round(MARGIN + index * wide), round(down), round(wide) + 1, tall)

    return down + tall + GAP


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    canvas.pen = GROUND
    canvas.clear()

    down = heading("hsv: even numbers, wandering lightness", MARGIN)
    down = strip([color.hsv(index * 256 // HUES, 255, 255) for index in range(HUES)], down)

    down = heading("oklch: even lightness, same hues", down)
    down = strip([color.oklch(LIGHTNESS, CHROMA, index * 360 / HUES) for index in range(HUES)],
                 down)

    down = heading("harmony: a base, then its triad and complement", down)
    down = strip((base,) + color.harmony(base, color.TRIAD)
                 + color.harmony(base, color.COMPLEMENT)[1:], down)

    down = heading(f"tones: one hue in {STEPS} steps", down)
    down = strip(color.tones(base, STEPS), down)

    down = heading(f"ramp: {STEPS} steps through colours you name", down)
    down = strip(color.ramp(RAMP, STEPS), down)

    down = heading("mix: an amount of 0 to 255, not 0 to 1", down)
    down = strip([color.mix(MIX_FROM, MIX_TO, amount) for amount in MIXES], down)

    down = heading("readable_on: lettering picked for its ground", down)
    wide = (canvas.width - MARGIN * 2) / len(READ_ON)
    for index, ground in enumerate(READ_ON):
        across = MARGIN + index * wide
        canvas.pen = ground
        canvas.rectangle(round(across), round(down), round(wide) + 1, STRIP + label_face.height)

        # Asked once and used twice: for the lettering, and for what it says about itself
        legible = color.readable_on(ground, ground)
        canvas.pen = legible
        canvas.text("readable", round(across + 3), round(down + 3))
        canvas.text(f"{color.contrast(ground, legible):.1f} to 1",
                    round(across + 3), round(down + STRIP - 4))

    screen.update(canvas)
    print("seven colour calls, each of them one line")

    # Nothing moves, so the panel holds its frame and this only waits
    while not mighty.boot_pressed():
        time.sleep(0.05)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
