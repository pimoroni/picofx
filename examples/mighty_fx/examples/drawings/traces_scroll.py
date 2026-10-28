import math
from picovector import image, tween

"""
Drawing: Traces scroll
An animation built from one tile, scrolling endlessly across the panel and turning between axes.
Section: Animation
"""

# Entry: screenA rotation=90: graphics file=traces_scroll.py

# Constants
FRAMES = "/examples/assets/traces"
# The animation's frames in order. A drawing cannot list a folder, so the names are written out
NAMES = ("traces1.png", "traces2.png", "traces3.png", "traces4.png",
         "traces5.png", "traces6.png", "traces7.png", "traces8.png")
FPS = 8                 # The rate the pattern itself animates at
STEP = 2                # Pixels the field travels each call
TURN = 50               # Calls a change of direction takes

tiles = []
for name in NAMES:
    path = f"{FRAMES}/{name}"
    try:
        tiles.append(image.load(path))
    except (ValueError, OSError):
        raise RuntimeError(f"'{path}' is missing or corrupt! Check it is on the drive") from None

WIDE = tiles[0].width        # The tile, and so how far the field travels across before it repeats
TALL = tiles[0].height       # And down

heading = tween(0.0, math.pi / 2, easing=tween.SINE_INOUT)
slowing = [STEP * math.cos(heading.at((frame + 0.5) / TURN)) for frame in range(TURN)]
TURNED = 2 * round(sum(slowing) / 2)
reached = [round(TURNED * sum(slowing[:frame + 1]) / sum(slowing)) for frame in range(TURN)]
leaving = [now - before for before, now in zip([0] + reached, reached)]
joining = leaving[::-1]


def moves():
    """Generate each call's step, a run, a turn, a run on the other axis and a turn back."""
    while True:
        for _ in range((WIDE - 2 * TURNED) // STEP):
            yield STEP, 0
        for left, joined in zip(leaving, joining):
            yield left, -joined
        for _ in range((TALL - 2 * TURNED) // STEP):
            yield 0, -STEP
        for left, joined in zip(leaving, joining):
            yield joined, -left


across, down = TURNED, 0
steps = moves()


def draw(canvas, elapsed):
    global across, down
    tile = tiles[int(elapsed * FPS) % len(tiles)]

    # The entry's offset is fixed, so the tile is laid by hand wherever the field has reached,
    # as many copies as cover the canvas from the wrapped start
    start_x = -(across % WIDE)
    start_y = -(down % TALL)
    y = start_y
    while y < canvas.height:
        x = start_x
        while x < canvas.width:
            canvas.blit(tile, x, y)
            x += WIDE
        y += TALL

    step_across, step_down = next(steps)
    across += step_across
    down += step_down
