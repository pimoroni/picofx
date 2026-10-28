import math
from picovector import color, font, image, mat3, shape

"""
Drawing: Flip-dot sign
A flip-dot sign, spelling its message in dots that turn over one column after the next.
Section: Mechanical and glowing displays
"""

# Entry: screenA rotation=90: graphics file=flip_dot_sign.py fps=100

# Constants for drawing
SIGN_FONT = font.match
CELL = 10
DOT_SIDES = 8
DOT_TWIST = 22.5
DOT_INSET = 1
FLIP_AXIS = 45
STOP_ANGLE = 135
PIN_SHARE = 0.25
FLIP_STEPS = 6
LIT = color.rgb(240, 230, 40)
UNLIT = color.rgb(48, 46, 44)
STOP = color.rgb(90, 88, 84)
FRAME = color.black
FLIP_MS = 420
SWEEP_MS = 70
HOLD_MS = 4000

MESSAGES = (
    ("CITY", "12:04"),
    ("CITY", "12:11"),
    ("DOCK", "12:26"),
    ("WEST", "12:40"),
)

DOT = CELL - DOT_INSET * 2
REACH = 1.0 / math.cos(math.pi / DOT_SIDES)
NUDGE = 0.5
PIN_PIXELS = max(2, round(DOT * PIN_SHARE))
PIN_AT = PIN_PIXELS // 2
PIN_REACH = 1.0 / math.cos(math.pi / 8)


def post(tile, angle):
    """Draw one of a cell's two posts, where it is seen."""
    seen = math.radians(angle)
    x = PIN_AT if math.cos(seen) < 0 else DOT - PIN_AT - PIN_PIXELS
    y = PIN_AT if math.sin(seen) < 0 else DOT - PIN_AT - PIN_PIXELS

    standing = shape.regular_polygon(0, 0, PIN_PIXELS / 2 * PIN_REACH, 8)
    standing.transform = mat3().translate(x + PIN_PIXELS / 2 + NUDGE, y + PIN_PIXELS / 2) \
                               .rotate(DOT_TWIST)
    tile.pen = STOP
    tile.shape(standing)


def faces(colour, stop_angle):
    """Bake a face at every step of its turn, from flat on to edge on."""
    middle = DOT / 2
    steps = []
    for step in range(FLIP_STEPS):
        squash = max(1.0 / DOT, math.cos(math.pi / 2 * step / (FLIP_STEPS - 1)))

        tile = image(DOT, DOT)
        tile.pen = FRAME
        tile.clear()

        radius = middle * REACH
        if squash == 1.0:
            placing = mat3().translate(middle + NUDGE, middle).rotate(DOT_TWIST)
        else:
            placing = mat3().translate(middle + NUDGE, middle).rotate(FLIP_AXIS) \
                            .scale(1, squash).rotate(DOT_TWIST - FLIP_AXIS)

        post(tile, stop_angle + 180)
        dot = shape.regular_polygon(0, 0, radius, DOT_SIDES)
        dot.transform = placing
        tile.pen = colour
        tile.shape(dot)
        post(tile, stop_angle)

        steps.append(tile)

    return steps


lit_steps = faces(LIT, STOP_ANGLE)
unlit_steps = faces(UNLIT, STOP_ANGLE + 180)

# The sign's size in dots and its lettering image, set on the first call from the canvas
columns = rows = 0
pattern = None
states = targets = None
flips = []
message = 0
sweep_from = 0          # When the sweep in progress began, in elapsed ms
due = None              # When the settled sign next changes, in elapsed ms


def dot_at(index):
    """Where the dot at this position in the grid starts on the canvas."""
    return (index % columns) * CELL + DOT_INSET, (index // columns) * CELL + DOT_INSET


def pattern_states(lines):
    """Draw the message at the sign's resolution and read it back as a state a dot."""
    pattern.pen = color.black
    pattern.clear()
    pattern.pen = color.white
    pattern.font = SIGN_FONT

    top = (rows - SIGN_FONT.height * len(lines)) // 2
    for line, text in enumerate(lines):
        width = int(pattern.measure_text(text)[0])
        pattern.text(text, (columns - width) // 2, top + line * SIGN_FONT.height)

    raw = pattern.raw
    stride = pattern.stride
    found = bytearray(columns * rows)
    for row in range(rows):
        for column in range(columns):
            pixel = row * stride + column * 4
            if raw[pixel] or raw[pixel + 1] or raw[pixel + 2]:
                found[row * columns + column] = 1

    return found


def show(canvas, index, lit):
    """Draw a dot at rest, showing one face or the other."""
    x, y = dot_at(index)
    canvas.blit(lit_steps[0] if lit else unlit_steps[0], x, y)


def turning(canvas, index, phase):
    """Draw a dot part way over. The face changes at halfway."""
    x, y = dot_at(index)
    if phase < 0.5:
        lit = states[index]
        step = round(phase * 2 * (FLIP_STEPS - 1))
    else:
        lit = targets[index]
        step = round((1 - phase) * 2 * (FLIP_STEPS - 1))

    canvas.blit(lit_steps[step] if lit else unlit_steps[step], x, y)


def schedule(wanted):
    """How far into the sweep each dot that has to change starts turning."""
    return [(index, (index % columns) * SWEEP_MS)
            for index in range(columns * rows) if wanted[index] != states[index]]


def advance(canvas, into_sweep):
    """Draw every dot mid-turn, and hand back the ones still turning."""
    turning_still = []
    for index, start in flips:
        into = into_sweep - start
        if into < 0:
            turning_still.append((index, start))
        elif into >= FLIP_MS:
            show(canvas, index, targets[index])
        else:
            turning(canvas, index, into / FLIP_MS)
            turning_still.append((index, start))

    return turning_still


def draw(canvas, elapsed):
    global columns, rows, pattern, states, targets, flips, message, sweep_from, due
    now = elapsed * 1000

    if pattern is None:
        # The board starts dark, as an unpowered one stands
        columns, rows = canvas.width // CELL, canvas.height // CELL
        pattern = image(columns, rows)
        canvas.pen = FRAME
        canvas.clear()
        states = bytearray(columns * rows)
        for position in range(columns * rows):
            show(canvas, position, False)
        targets = pattern_states(MESSAGES[0])
        flips = schedule(targets)
        sweep_from = now

    if flips:
        flips = advance(canvas, now - sweep_from)
        if not flips:
            states = targets
            due = now + HOLD_MS

    elif now >= due:
        message = (message + 1) % len(MESSAGES)
        targets = pattern_states(MESSAGES[message])
        flips = schedule(targets)
        sweep_from = now
