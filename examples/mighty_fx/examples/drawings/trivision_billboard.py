import math
from picovector import color, image, rect

"""
Drawing: Trivision billboard
A trivision billboard, its posters carried on three-sided slats that turn a third at a time.
Section: Billboards and panels
"""

# Entry: screenA rotation=90: graphics file=trivision_billboard.py fps=100   (a 2.8" screen)

# Constants for drawing
SLATS = 20
TURN_MS = 1600
STAGGER_MS = 200
HOLD_MS = 3000
SHADE_FROM = 20
AMBIENT = 90

POSTER_FILES = ("/examples/assets/billboards/landscape/lambo.png",
                "/examples/assets/billboards/landscape/tufty.png",
                "/examples/assets/billboards/landscape/frum.png")

# The canvas this drawing expects, a 2.8" screen at rotation=90, stated as the posters are
# fitted to it before the first call
WIDTH, HEIGHT = 320, 240

SLAT = WIDTH // SLATS
APOTHEM = SLAT / (2 * math.sqrt(3))


def fitted(path):
    """One file as a board-sized poster."""
    try:
        loaded = image.load(path, WIDTH, HEIGHT)
    except (ValueError, OSError):
        raise RuntimeError(f"'{path}' is missing or corrupt! Check it is on the drive") from None

    board = image(WIDTH, HEIGHT)
    board.blit(loaded, rect(0, 0, loaded.width, loaded.height),
               rect(0, 0, WIDTH, HEIGHT), image.BILINEAR)
    return board


posters = [fitted(path) for path in POSTER_FILES]


def showing(turn):
    """Which faces of a slat show at this rotation, and at what angle, left to right."""
    faces = []
    for face in range(3):
        angle = (turn - face * 120 + 180) % 360 - 180
        if -90 < angle < 90:
            faces.append((angle, face))
    faces.sort()
    return faces


sources = [rect(slat * SLAT, 0, SLAT, HEIGHT) for slat in range(SLATS)]
target = rect(0, 0, SLAT, HEIGHT)
drawn = [None] * SLATS


def redraw(canvas, turns):
    """Redraw the slats whose rotation changed and their neighbours."""
    changed = [slat for slat in range(SLATS) if turns[slat] != drawn[slat]]
    if not changed:
        return

    touched = sorted({beside for slat in changed
                      for beside in (slat - 1, slat, slat + 1) if 0 <= beside < SLATS})

    canvas.pen = color.black
    for slat in touched:
        canvas.rectangle(rect(slat * SLAT, 0, SLAT, HEIGHT))

    for slat in touched:
        axis = slat * SLAT + SLAT / 2
        for angle, face in showing(turns[slat]):
            lit = math.cos(math.radians(angle))
            middle = axis + APOTHEM * math.sin(math.radians(angle))
            left, right = round(middle - SLAT / 2 * lit), round(middle + SLAT / 2 * lit)
            if right > left:
                past = max(0.0, abs(angle) - SHADE_FROM) / (90 - SHADE_FROM)
                canvas.alpha = int(255 - (255 - AMBIENT) * past)
                target.x, target.w = left, right - left
                canvas.blit(posters[face], sources[slat], target)

        drawn[slat] = turns[slat]

    canvas.alpha = 255


turns = [0] * SLATS
turned = 0
turning = False
turn_from = 0           # When the turn in progress began, in elapsed ms
due = None              # When the board next turns, in elapsed ms


def draw(canvas, elapsed):
    global turns, turned, turning, turn_from, due
    now = elapsed * 1000
    if due is None:
        if (canvas.width, canvas.height) != (WIDTH, HEIGHT):
            raise ValueError(f'this drawing is laid out for {WIDTH}x{HEIGHT}, a 2.8" screen at '
                             f"rotation=90, and was given {canvas.width}x{canvas.height}")
        redraw(canvas, turns)
        due = now + HOLD_MS

    if turning:
        wave = now - turn_from
        done = True
        for slat in range(SLATS):
            into = wave - slat * STAGGER_MS
            if into < 0:
                part = 0.0
                done = False
            elif into < TURN_MS:
                part = into / TURN_MS
                done = False
            else:
                part = 1.0
            turns[slat] = turned + 120 * (1 - math.cos(math.pi * part)) / 2

        redraw(canvas, turns)

        if done:
            turned = (turned + 120) % 360
            turns = [turned] * SLATS
            turning = False
            due = now + HOLD_MS

    elif now >= due:
        turning = True
        turn_from = now
