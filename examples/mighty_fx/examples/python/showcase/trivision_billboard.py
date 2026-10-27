import math
from mighty_fx import MightyFX, SPCE
from timing import Pacer, Roller
from screens import Screen280
from picovector import color, image, rect

"""
Draw a trivision billboard, its posters carried on three-sided slats that turn a third at a time.

Press "Boot" to exit the program.

Section: Billboards and panels
"""

# Constants for drawing
SLATS = 20                          # How many prisms the board is split into across its width
TURN_MS = 1600                      # How long a slat takes to turn a third of the way round
# A turn crosses the board as a wave as on a real board, so only a few slats are redrawn at once
STAGGER_MS = 200                    # How much later each slat starts turning than the one left of it
HOLD = 3.0                          # How long a poster faces out before the board turns again
# Shading waits for SHADE_FROM, so the steps between a channel's 16 levels
# fall only on faces plainly turning
SHADE_FROM = 20                     # How far a face turns before it is shaded at all, in degrees
AMBIENT = 90                        # How lit it is by edge on, against 255 facing out

# One poster to each of a slat's three faces, stretched to the board as it loads
POSTER_FILES = ("/examples/assets/billboards/landscape/lambo.png",
                "/examples/assets/billboards/landscape/tufty.png",
                "/examples/assets/billboards/landscape/frum.png")

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# Drawn landscape and turned a quarter onto the panel at each update
canvas = screen.canvas(screen.height, screen.width)
SLAT = canvas.width // SLATS
APOTHEM = SLAT / (2 * math.sqrt(3))     # From a slat's axis out to the middle of one of its faces


def fitted(path):
    """
    One file as a board-sized poster.

    A file smaller than the board arrives at its own size, so it is blitted up to fit.
    """
    try:
        loaded = image.load(path, canvas.width, canvas.height)
    except (ValueError, OSError):
        mighty.shutdown()
        raise RuntimeError(f"'{path}' is missing or corrupt! Check it is on the board") from None

    board = image(canvas.width, canvas.height)
    board.blit(loaded, rect(0, 0, loaded.width, loaded.height),
               rect(0, 0, canvas.width, canvas.height), image.BILINEAR)
    return board


posters = [fitted(path) for path in POSTER_FILES]


def showing(turn):
    """
    Which faces of a slat show at this rotation, and at what angle, left to right.

    A slat is a three-sided prism, so at most two faces show. A face narrows by the cosine of its
    angle and slides by the sine, which is why the wall shows through part way round.
    """
    faces = []
    for face in range(3):
        angle = (turn - face * 120 + 180) % 360 - 180   # This face's angle from facing out, folded into -180 to 180
        if -90 < angle < 90:
            faces.append((angle, face))

    faces.sort()
    return faces


# One source rect a slat and one target reused, so a frame allocates nothing
sources = [rect(slat * SLAT, 0, SLAT, canvas.height) for slat in range(SLATS)]
target = rect(0, 0, SLAT, canvas.height)
drawn = [None] * SLATS      # What each slat was last drawn at, so a still one is left alone


def draw(turns):
    """
    Redraw the slats whose rotation changed and their neighbours, and return how many.

    A turning slat overhangs its pitch by up to a pixel, so blanking it clips whatever is beside it.
    """
    changed = [slat for slat in range(SLATS) if turns[slat] != drawn[slat]]
    if not changed:
        return 0

    touched = sorted({beside for slat in changed
                      for beside in (slat - 1, slat, slat + 1) if 0 <= beside < SLATS})

    # Every pitch blanked before any face is drawn, or a slat would blank
    # its neighbour's overhang after that neighbour had drawn it
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


print(f"{SLATS} slats of {SLAT}px, {len(POSTER_FILES)} posters, turning in {TURN_MS}ms")

# The board starts with the first poster facing out, and turns a third at a time from there
turns = [0] * SLATS
draw(turns)
screen.update(canvas, rotation=90)

turned = 0
turning = False
pacer = Pacer(0.01)                 # Its elapsed time counts from the start of the turn in progress

# When the board is next due to turn. The hold runs from the end of the last turn
settled = Roller(HOLD)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # A turn runs until every slat has finished its own, each starting after the one before it
        if turning:
            wave = pacer.elapsed
            done = True
            for slat in range(SLATS):
                elapsed = wave - slat * STAGGER_MS
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
                turning = False
                settled.restart()

        elif settled.is_due():
            turning = True
            pacer.restart()

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
