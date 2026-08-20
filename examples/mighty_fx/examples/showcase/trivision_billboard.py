# A trivision billboard, its posters carried on three-sided slats that turn a third at a time.

import math
import time
from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import color, font, image, rect, shape

# Constants for drawing
SLATS = 20                          # How many prisms the board is split into across its width
TURN_MS = 1600                      # How long a slat takes to turn a third of the way round
# A turn crosses the board as a wave, which is both what a mechanical board does and what keeps the
# drawing cheap: only the slats moving at a given moment are redrawn, and the wider this is set the
# fewer of them there are at once. Roughly TURN_MS over this many are moving together
STAGGER_MS = 200                    # How much later each slat starts turning than the one left of it
HOLD = 3.0                          # How long a poster faces out before the board turns again
# The panel is 12 bit, so each channel has 16 levels and a shading ramp crossing one shows as a hard
# step between neighbouring slats. A slat barely off square on is not visibly turning, so a step
# there reads as a fault: shading holds off until SHADE_FROM and then runs to AMBIENT at edge on,
# which puts every step on a face that is plainly moving and narrowing as well
SHADE_FROM = 20                     # How far a face turns before it is shaded at all, in degrees
AMBIENT = 90                        # How lit it is by edge on, against 255 facing out
POSTER_FONT = "awesome"             # The lettering on the posters. dir(font) lists all 37
POSTER_SCALE = 3                    # Pixel fonts scale by whole numbers, so 3 is triple size

# Files to put on the faces instead of the drawn posters, as many as there are or none at all. Each
# is fitted to the whole board as it loads, so one shaped differently is stretched rather than
# cropped, and fewer than three faces' worth are used again in turn. A board without them says so
# and draws the posters, so the example runs whatever is or is not on this one
POSTER_FILES = ("/examples/assets/billboards/landscape/lambo.png",
                "/examples/assets/billboards/landscape/tufty.png",
                "/examples/assets/billboards/landscape/frum.png")

# One poster to a face, so a third of a turn brings the next one round and three turns come back to
# the first. Drawn here rather than loaded, which is what lets the board run with no files at all
POSTERS = (
    ("SUMMER", color.rgb(216, 72, 32), color.rgb(255, 236, 180), color.rgb(255, 176, 40)),
    ("SALE", color.rgb(24, 64, 148), color.rgb(240, 248, 255), color.rgb(96, 168, 232)),
    ("NOW ON", color.rgb(28, 28, 32), color.rgb(248, 232, 96), color.rgb(72, 72, 80)),
)
FACES = 3                           # Sides to a slat, and so how many posters the board carries

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# The board is wider than it is tall, so the canvas is drawn landscape and every update turns it a
# quarter turn onto the panel.
#
# It comes from the screen rather than from image(), which puts it in SRAM instead of on the GC
# heap. The heap is PSRAM, read over XIP, and every pixel of this board is written by a blit and
# read again by the update, so both halve. The posters stay on the heap: only one canvas of this
# size fits the region, and they are read far less than the canvas is written
canvas = screen.canvas(screen.height, screen.width)
SLAT = canvas.width // SLATS
APOTHEM = SLAT / (2 * math.sqrt(3))     # From a slat's axis out to the middle of one of its faces
poster_font = getattr(font, POSTER_FONT)


def poster(text, ground, ink, accent):
    """One poster, the size of the whole board, drawn rather than loaded."""
    face = image(canvas.width, canvas.height)
    face.pen = ground
    face.clear()

    # A band behind the lettering, and a rule under it, so a slat's strip still reads as part of
    # something when it is the only one turned
    face.pen = accent
    face.rectangle(rect(0, canvas.height // 3, canvas.width, canvas.height // 3))
    face.shape(shape.rectangle(0, canvas.height - 12, canvas.width, 6))

    face.font = poster_font
    face.pen = ink
    width = int(face.measure_text(text)[0]) * POSTER_SCALE
    height = poster_font.height * POSTER_SCALE
    face.text(text, rect((canvas.width - width) // 2, (canvas.height - height) // 2, width, height),
              font_size=POSTER_SCALE)
    return face


def fitted(path):
    """One file as a poster the size of the whole board.

    load() decodes straight to the size asked for, which is all most files need. A palettised one
    ignores that and arrives at its own size, one byte a pixel, so it is blitted into a board sized
    image instead, which fits it and gives it colour to be shaded with.
    """
    loaded = image.load(path, canvas.width, canvas.height)
    if loaded.width == canvas.width and loaded.height == canvas.height and not loaded.has_palette:
        return loaded

    board = image(canvas.width, canvas.height)
    board.blit(loaded, rect(0, 0, loaded.width, loaded.height),
               rect(0, 0, canvas.width, canvas.height), image.BILINEAR)
    return board


def from_files():
    """The files as posters, or None where any of them is not on this board."""
    faces = []
    for path in POSTER_FILES:
        try:
            faces.append(fitted(path))
        except OSError:
            print(f"{path} is not on this board, so the posters are drawn instead")
            return None

    return [faces[face % len(faces)] for face in range(FACES)]


posters = from_files() if POSTER_FILES else None
if posters is None:
    posters = [poster(*entry) for entry in POSTERS]


def showing(turn):
    """Which faces of a slat show at this rotation, and at what angle, left to right.

    A slat is an equilateral prism, so its faces sit 120 degrees apart and at most two ever face
    out. A face's width projects as the slat's own by the cosine of its angle, and its middle sits
    APOTHEM by the sine of it from the slat's axis, which is what slides a face across as it turns.

    The two together are why the wall shows through part way round: with a face square on the slat
    covers its whole pitch, and with a corner square on it covers only 0.866 of it.
    """
    faces = []
    for face in range(FACES):
        angle = (turn - face * 120 + 180) % 360 - 180
        if -90 < angle < 90:
            faces.append((angle, face))

    faces.sort()
    return faces


# One source rect a slat, which never changes, and one target reused for every blit. Building them
# each frame costs more than the blits do: forty of them is enough allocation to bring the collector
# in, and on a heap this size that is not cheap
sources = [rect(slat * SLAT, 0, SLAT, canvas.height) for slat in range(SLATS)]
target = rect(0, 0, SLAT, canvas.height)
drawn = [None] * SLATS      # What each slat was last drawn at, so a still one is left alone


def draw(turns):
    """Redraw the slats whose rotation changed, and hand back how many that was.

    The panel takes a whole frame however little of it changed, so narrowing the write buys
    nothing. Narrowing the draw does: a slat costs about 2.5ms, and with the turn crossing the
    board as a wave only a handful are moving at once.

    The neighbours of a changed slat are redrawn too. A turning slat overhangs its own pitch by up
    to a pixel, so blanking a pitch takes a slice of whatever is beside it, and the slat outside
    the wave is square on and overhangs nothing, which is what stops that spreading any further.
    """
    changed = [slat for slat in range(SLATS) if turns[slat] != drawn[slat]]
    if not changed:
        return 0

    touched = sorted({beside for slat in changed
                      for beside in (slat - 1, slat, slat + 1) if 0 <= beside < SLATS})

    # Every pitch blanked before any face is drawn, or a slat would blank its neighbour's overhang
    # after that neighbour had drawn it
    canvas.pen = color.black
    for slat in touched:
        canvas.rectangle(rect(slat * SLAT, 0, SLAT, canvas.height))

    for slat in touched:
        axis = slat * SLAT + SLAT / 2
        for angle, face in showing(turns[slat]):
            lit = math.cos(math.radians(angle))
            middle = axis + APOTHEM * math.sin(math.radians(angle))
            left, right = round(middle - SLAT / 2 * lit), round(middle + SLAT / 2 * lit)

            if right > left:
                # A face turned away catches less light, which the layer alpha gives for nothing
                past = max(0.0, abs(angle) - SHADE_FROM) / (90 - SHADE_FROM)
                canvas.alpha = int(255 - (255 - AMBIENT) * past)
                target.x, target.w = left, right - left
                canvas.blit(posters[face], sources[slat], target)

        drawn[slat] = turns[slat]

    canvas.alpha = 255
    return len(touched)


print(f"{SLATS} slats of {SLAT}px, {len(POSTERS)} posters, turning in {TURN_MS}ms")

# The board starts with the first poster facing out, and turns a third at a time from there
turns = [0] * SLATS
draw(turns)
screen.update(canvas, rotation=90)

turned = 0
started = None
settled_at = time.ticks_add(time.ticks_ms(), int(HOLD * 1000))

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        now = time.ticks_ms()

        # A turn runs until every slat has finished its own, each starting after the one before it
        if started is not None:
            done = True
            for slat in range(SLATS):
                elapsed = time.ticks_diff(now, time.ticks_add(started, slat * STAGGER_MS))
                if elapsed < 0:
                    part = 0.0
                    done = False
                elif elapsed < TURN_MS:
                    part = elapsed / TURN_MS
                    done = False
                else:
                    part = 1.0

                # Eased, since a slat is a mass on a shaft and does not start or stop dead
                turns[slat] = turned + 120 * (1 - math.cos(math.pi * part)) / 2

            if draw(turns):
                screen.update(canvas, rotation=90)

            if done:
                turned = (turned + 120) % 360
                turns = [turned] * SLATS
                started = None
                settled_at = time.ticks_add(now, int(HOLD * 1000))

        elif time.ticks_diff(now, settled_at) >= 0:
            started = now

        else:
            time.sleep_ms(10)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
