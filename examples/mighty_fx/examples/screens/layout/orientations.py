import sys

from mighty_fx import MightyFX, SPCE
from picovector import color, font, image, shape, vec2
from screens import SCREEN_TYPES, Reserve

"""
Show one mark in all eight ways a panel can carry it.

rotation= turns the picture in quarter steps and mirror= flips it left to right. The two
together are every orientation there is, and the order they cycle in here is the lesson: the
four turns first, then the four turns of the mirrored mark. Nothing rotation= does on its own
reaches that second set, which is why mirror= is a setting of its own and not two more turns.

Both are there for how a panel ends up mounted. A screen fitted on its side wants rotation=,
and one seen in a mirror or from behind a window wants mirror=, so the drawing can be made
the right way round once and left alone.

The mark has to declare its own orientation or every step looks like a different picture. F
is the letter with no symmetry to hide behind, every edge carries a zigzag of its own colour
so one look says which edge is against which side of the panel, and the caption is drawn into
the mark, so it turns and flips with everything else: upside down at 180, back to front when
mirrored. That is the plainest sight of what the settings did.

The mark is square and as long as the panel's longest side, so it reaches past the panel
whichever way round it is turned: upright it loses part of its sides, and turned a quarter it
loses part of its top and foot instead. Every turn therefore keeps a different part of it and
none of them is ever letterboxed, the colour running to the panel's edge throughout. Nothing
is wrong with that: a source is not obliged to be the panel's shape or the panel's size. The
four zigzags all reach far enough in to survive every turn, as do the letter and the caption.

Nothing is drawn per frame; the mark is redrawn only when the settings change.

Press "Boot" to exit the program.
"""

# Constants
HOLD = 44                # Frames each orientation is held for, a little under two seconds
LETTER = "F"             # The mark, and the reason it is an F is that it has no symmetry
LETTER_FILL = 0.62       # How much of the square the letter's ink reaches across
CAPTION_FACE = "winds"   # The narrowest ROM pixel face, so the caption stays out of the way
CAPTION_GAP = 8          # Between the caption and the zigzag along the foot of the square
FACE_PATH = "/rom/fonts/PoppinsBlack.af"   # A heavy vector face, the letter being the subject

GROUND = color.rgb(18, 22, 32)        # The mark's own ground
INK = color.rgb(236, 240, 248)
CAPTION = color.rgb(176, 192, 212)

# A zigzag along every edge, a colour to each, which is how the edges are told apart: one
# look says which of them is against which side of the panel, and mirroring swaps two
# colours over. The zigzag itself is what a straight edge cannot do, being caught at a glance
ZIG_TOP = color.rgb(216, 40, 48)
ZIG_RIGHT = color.rgb(40, 176, 96)
ZIG_FOOT = color.rgb(56, 96, 220)
ZIG_LEFT = color.rgb(236, 176, 32)
ZIG_REACH = 18           # How far a zigzag reaches inside the uncropped square
ZIG_DEEP = 10            # Of which this much is tooth, the rest a solid band
ZIG_WIDE = 24            # And how wide a tooth is, near enough: the edge divides it

# The turns, and then the same turns of the mirrored mark
ORDER = tuple((rotation, mirror) for mirror in (False, True)
              for rotation in (0, 90, 180, 270))

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it. The
# reserve is what keeps a source this size ahead of the wire out of the heap, the conversion
# moving into prepare() rather than racing the scan
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES)

# The mark is a square of the panel's longest side, so it reaches past the panel every way
# round. It lives in the heap: at this size it is larger than a full-size image and the SRAM
# canvas has no room for it, and nothing draws to it per frame in any case.
#
# SIDE is the square inside it that no turn can crop, which is where anything that has to
# stay readable belongs, and END is the strip beyond it that comes and goes
LONG = max(screen.width, screen.height)
mark = image(LONG, LONG)
mark.antialias = image.X4
SIDE = min(screen.width, screen.height)
END = (LONG - SIDE) // 2

letter_face = font.load(FACE_PATH)
caption_face = getattr(font, CAPTION_FACE)


def ink_box(size):
    """Which pixels the letter's ink actually occupies, drawn at this size from the origin.

    Read from a drawing, since a face takes font_size as its em height and a capital fills
    neither all of that nor the middle of it. Centring on the box a face declares puts the
    letter visibly off centre, which on a mark about orientation would read as a fault.
    """
    probe = image(round(size * 2), round(size * 2))
    probe.antialias = image.X4
    probe.pen = color.black
    probe.clear()
    probe.pen = color.white
    probe.font = letter_face
    probe.text(LETTER, 0, size, font_size=size)

    raw, stride = probe.raw, probe.stride
    rows = [y for y in range(probe.height)
            if any(raw[y * stride + x * 4] > 60 for x in range(probe.width))]
    columns = [x for x in range(probe.width)
               if any(raw[y * stride + x * 4] > 60 for y in rows)]
    return columns[0], rows[0], columns[-1] - columns[0] + 1, rows[-1] - rows[0] + 1


# One measurement of the ink at a nominal size gives the size the letter wants and where to
# put it, both scaling with the panel. It is placed in the square that no turn crops, so the
# letter is whole at every one of the eight
NOMINAL = SIDE / 2
box_x, box_y, box_w, box_h = ink_box(NOMINAL)
LETTER_SIZE = NOMINAL * SIDE * LETTER_FILL / max(box_w, box_h)
SCALED = LETTER_SIZE / NOMINAL
LETTER_X = (mark.width - box_w * SCALED) / 2 - box_x * SCALED
LETTER_Y = (mark.height - box_h * SCALED) / 2 - box_y * SCALED + LETTER_SIZE

print(f"eight orientations of a {mark.width}x{mark.height} mark on a"
      f" {screen.width}x{screen.height} panel, {END}px off its sides upright"
      f" and {END}px off its ends turned")


def teeth_along(edge):
    """Where one edge's teeth start, as a run of positions along it."""
    count = max(2, round(edge / ZIG_WIDE))
    wide = edge / count
    return [tooth * wide for tooth in range(count)], wide


def zig_across(ink, edge, inward, depth):
    """The zigzag on the top or the foot, inward being 1 from the top and -1 from the foot.

    A solid band from the edge of the mark, then a row of teeth off the inside of it. The
    teeth are drawn in the block's own colour rather than cut out of it in the ground's,
    since the four blocks meet at the corners and a cut-out would bite into its neighbour.
    """
    inner = edge + (depth - ZIG_DEEP) * inward
    mark.pen = ink
    mark.shape(shape.rectangle(0, min(edge, inner), mark.width, depth - ZIG_DEEP))

    point = edge + depth * inward
    starts, wide = teeth_along(mark.width)
    for start in starts:
        mark.shape(shape.custom([vec2(start, inner), vec2(start + wide, inner),
                                 vec2(start + wide / 2, point)]))


def zig_down(ink, edge, inward, depth):
    """The zigzag on the left or the right, inward being 1 from the left and -1 from the right."""
    inner = edge + (depth - ZIG_DEEP) * inward
    mark.pen = ink
    mark.shape(shape.rectangle(min(edge, inner), 0, depth - ZIG_DEEP, mark.height))

    point = edge + depth * inward
    starts, wide = teeth_along(mark.height)
    for start in starts:
        mark.shape(shape.custom([vec2(inner, start), vec2(inner, start + wide),
                                 vec2(point, start + wide / 2)]))


def draw_mark(rotation, mirror):
    """The mark, captioned with the settings it is about to be shown under."""
    mark.pen = GROUND
    mark.clear()

    # Every edge has a cropped strip beyond the square, so all four are given the same depth:
    # the strip, and the reach inside the square that no turn takes. The sides are drawn last,
    # which is what settles the corners
    zig_across(ZIG_TOP, 0, 1, END + ZIG_REACH)
    zig_across(ZIG_FOOT, mark.height, -1, END + ZIG_REACH)
    zig_down(ZIG_LEFT, 0, 1, END + ZIG_REACH)
    zig_down(ZIG_RIGHT, mark.width, -1, END + ZIG_REACH)

    mark.pen = INK
    mark.font = letter_face
    mark.text(LETTER, LETTER_X, LETTER_Y, font_size=LETTER_SIZE)

    # A pixel face draws down from the y it is given, so the caption is lifted by the face's
    # own height, and it sits inside the uncropped square so that it reads at every turn
    mark.pen = CAPTION
    mark.font = caption_face
    caption = f"rotation={rotation} mirror={mirror}"
    wide = mark.measure_text(caption)[0]
    mark.text(caption, (mark.width - wide) / 2,
              END + SIDE - ZIG_REACH - CAPTION_GAP - caption_face.height)


step = -1
frames = 0
rotation, mirror = ORDER[0]

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Counting frames rather than reading the clock keeps every step the same length,
        # the frame wait already being the only clock the panel answers to
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
