import sys

from mighty_fx import MightyFX, SPCE
from picovector import color, font, image, shape
from screens import SCREEN_TYPES, Reserve

"""
Show one mark in all eight ways a panel can carry it.

rotation= turns the picture in quarter steps and mirror= flips it, and together they give every
orientation. The cycle is the four turns, then the four turns of the mirrored mark.

rotation= suits a panel mounted on its side, and mirror= one seen in a mirror or through a
window. The mark is an F with a coloured band on each edge, so one look tells the edges apart.

Press "Boot" to exit the program.
"""

# Constants
HOLD = 44                   # Frames each orientation is held for, a little under two seconds
LETTER = "F"                # The mark, and the reason it is an F is that it has no symmetry
LETTER_FILL = 0.62          # How much of the square the drawn letter reaches across
CAPTION_FACE = font.winds   # The narrowest ROM pixel face, so the caption stays out of the way
CAPTION_GAP = 13            # Between the caption and the band along the foot of the square
FACE_PATH = "/rom/fonts/PoppinsBlack.af"    # A heavy vector face, the letter being the subject

BACKGROUND = color.rgb(18, 22, 32)          # The mark's own background
LETTER_COLOUR = color.rgb(236, 240, 248)
CAPTION = color.rgb(176, 192, 212)

# A coloured band along every edge, so a mirror visibly swaps two of them
BAND_TOP = color.rgb(216, 40, 48)
BAND_RIGHT = color.rgb(40, 176, 96)
BAND_FOOT = color.rgb(56, 96, 220)
BAND_LEFT = color.rgb(236, 176, 32)
BAND_REACH = 13          # How far a band reaches inside the uncropped square

# The turns, and then the same turns of the mirrored mark
ORDER = tuple((rotation, mirror) for mirror in (False, True)
              for rotation in (0, 90, 180, 270))

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens,
# and the screen on it with a reserve for a source this size
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES)

# The mark is a square of the panel's longest side to cover it at every turn, too big for the canvas
# region. SIDE is the square no turn crops, and END the strip beyond it that comes and goes
LONG = max(screen.width, screen.height)
mark = image(LONG, LONG)
mark.antialias = image.X4
SIDE = min(screen.width, screen.height)
END = (LONG - SIDE) // 2

letter_face = font.load(FACE_PATH)


def letter_box(size):
    """Measure where the drawn letter lies, as a capital neither fills nor centres in its em box."""
    probe = image(round(size * 2), round(size * 2))
    probe.antialias = image.X4
    probe.pen = color.white
    probe.font = letter_face
    probe.text(LETTER, 0, size, font_size=size)

    raw, stride = probe.raw, probe.stride
    rows = [y for y in range(probe.height)
            if any(raw[y * stride + x * 4] > 60 for x in range(probe.width))]
    columns = [x for x in range(probe.width)
               if any(raw[y * stride + x * 4] > 60 for y in rows)]
    return columns[0], rows[0], columns[-1] - columns[0] + 1, rows[-1] - rows[0] + 1


# Size and place the letter from one measurement, inside the square no turn crops
NOMINAL = SIDE / 2
box_x, box_y, box_w, box_h = letter_box(NOMINAL)
LETTER_SIZE = NOMINAL * SIDE * LETTER_FILL / max(box_w, box_h)
SCALED = LETTER_SIZE / NOMINAL
LETTER_X = (mark.width - box_w * SCALED) / 2 - box_x * SCALED
LETTER_Y = (mark.height - box_h * SCALED) / 2 - box_y * SCALED + LETTER_SIZE

print(f"eight orientations of a {mark.width}x{mark.height} mark on a"
      f" {screen.width}x{screen.height} panel, {END}px off its sides upright"
      f" and {END}px off its ends turned")


def draw_mark(rotation, mirror):
    """Draw the mark, captioned with the settings it is about to be shown under."""
    mark.pen = BACKGROUND
    mark.clear()

    # Every edge takes the same depth, and the sides go last to settle the corners
    deep = END + BAND_REACH
    for colour, x, y, wide, tall in ((BAND_TOP, 0, 0, mark.width, deep),
                                     (BAND_FOOT, 0, mark.height - deep, mark.width, deep),
                                     (BAND_LEFT, 0, 0, deep, mark.height),
                                     (BAND_RIGHT, mark.width - deep, 0, deep, mark.height)):
        mark.pen = colour
        mark.shape(shape.rectangle(x, y, wide, tall))

    mark.pen = LETTER_COLOUR
    mark.font = letter_face
    mark.text(LETTER, LETTER_X, LETTER_Y, font_size=LETTER_SIZE)

    # A pixel face draws down from the y it is given, so the caption is lifted by the face's
    # own height, and it sits inside the uncropped square so that it reads at every turn
    mark.pen = CAPTION
    mark.font = CAPTION_FACE
    caption = f"rotation={rotation} mirror={mirror}"
    wide = mark.measure_text(caption)[0]
    mark.text(caption, (mark.width - wide) / 2,
              END + SIDE - BAND_REACH - CAPTION_GAP - CAPTION_FACE.height)


step = -1
frames = 0

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Count frames, so every step is the same length on the panel
        reached = frames // HOLD % len(ORDER)
        if reached != step:
            step = reached
            rotation, mirror = ORDER[step]
            draw_mark(rotation, mirror)

        screen.update(mark, rotation=rotation, mirror=mirror)
        frames += 1

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
