# A flip-dot sign, spelling its message in dots that turn over one column after the next.

import math
import time
from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import color, font, image, mat3, shape

# Constants for drawing
# match is the bolder face that still fits, a wider one running a five character line off a board
# this size. dir(font) lists all 37
SIGN_FONT = "match"                 # The lettering, drawn one pixel to a dot
CELL = 10                           # The dot pitch in pixels, which is what sets how much the sign holds
DOT_SIDES = 8                       # Octagonal dots, as one type has. Set it to 16 for the round type
DOT_TWIST = 22.5                    # Turns the octagon so its flats face up and along, as a real one sits
DOT_INSET = 1                       # How much of the frame shows between one dot and the next
FLIP_AXIS = 45                      # The angle of the diagonal a dot turns about, corner to corner
# Two posts to a cell, one at either end of the diagonal across the turning axis, and the dark face
# rests against the one opposite the lit face's
STOP_ANGLE = 135                    # The post the lit face rests against, bottom left as seen
PIN_SHARE = 0.25                    # A post's size against the dot's, so detail grows with the pitch
FLIP_STEPS = 6                      # How many faces a turn is drawn with, one to a frame
LIT = color.rgb(240, 230, 40)       # A dot showing its yellow face
UNLIT = color.rgb(48, 46, 44)       # And its dark one, which a real dot still shows plainly
STOP = color.rgb(90, 88, 84)        # The posts, lighter than either face so they read as parts
FRAME = color.black                 # What the dots are set into
# A frame takes about 65ms, nearly all of it reaching the panel, so these are set in whole frames
# rather than finer: a turn spanning fewer of them arrives in two or three steps however smooth the
# sum is, and a sweep shorter than one starts whole blocks of columns together
FLIP_MS = 420                       # How long one dot takes to turn over
SWEEP_MS = 70                       # How much later each column starts turning than the one before
HOLD = 4.0                          # How long a message stays up once the board has settled

# What the sign shows, a line to a row of lettering. A board this wide holds four or five
# characters a line, as terse as a real sign of the same pitch. The first two share a destination,
# so that change turns over only the time and leaves the rest of the board standing
MESSAGES = (
    ("CITY", "12:04"),
    ("CITY", "12:11"),
    ("DOCK", "12:26"),
    ("WEST", "12:40"),
)

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# The sign is wider than it is tall, so the canvas is drawn landscape and every update turns it a
# quarter turn onto the panel. It comes from the screen rather than from image(), which puts it in
# SRAM instead of on the GC heap: the heap is PSRAM and read over XIP, so the update pays about
# twice per pixel to convert from one
canvas = screen.canvas(screen.height, screen.width)
columns = canvas.width // CELL
rows = canvas.height // CELL

# One pixel to a dot, which is what the lettering is drawn at: the sign's own resolution
sign_font = getattr(font, SIGN_FONT)
pattern = image(columns, rows)

DOT = CELL - DOT_INSET * 2

# A radius that reaches the dot's flats to the edge of its tile rather than its corners, and a
# half pixel across to sit the shape on the pixel grid. Without the offset the right and bottom of
# the dot fall outside the tile and one corner comes out square instead of chamfered. Eight pixels
# of dot is the smallest that chamfers evenly, which is what CELL and DOT_INSET are set for
REACH = 1.0 / math.cos(math.pi / DOT_SIDES)
NUDGE = 0.5

# The post in whole pixels, so a wider pitch carries a larger one rather than the same two pixels
# sitting in a bigger dot. It is drawn as an octagon like the dot, which at two pixels comes out a
# square and at four has its corners off, both of which is what a post looks like at that size
PIN_PIXELS = max(2, round(DOT * PIN_SHARE))
PIN_AT = PIN_PIXELS // 2
PIN_REACH = 1.0 / math.cos(math.pi / 8)


def post(tile, angle):
    """One of a cell's two posts, where it is seen. The carrier holds them, so they never move."""
    seen = math.radians(angle)
    x = PIN_AT if math.cos(seen) < 0 else DOT - PIN_AT - PIN_PIXELS
    y = PIN_AT if math.sin(seen) < 0 else DOT - PIN_AT - PIN_PIXELS

    standing = shape.regular_polygon(0, 0, PIN_PIXELS / 2 * PIN_REACH, 8)
    standing.transform = mat3().translate(x + PIN_PIXELS / 2 + NUDGE, y + PIN_PIXELS / 2) \
                               .rotate(DOT_TWIST)
    tile.pen = STOP
    tile.shape(standing)


def faces(colour, stop_angle):
    """A face at every step of its turn, from flat on to edge on.

    A dot turns about the diagonal between two of its corners, so the face narrows across that
    line and not down the panel. The axis itself has nothing to see.

    Each cell holds two posts, one at either end of the other diagonal, and the dot's travel runs
    between them. Whichever it is resting against shows on top of the face, while the far one is
    covered by it, until the face turns far enough to be narrower than the gap and both come into
    view. Turning over swaps which is which, so each face has its own and stop_angle is that one.

    Baking the steps means a turning dot costs the same single blit a still one does, and each
    tile carries the frame around the dot so nothing underneath has to be redrawn first.
    """
    middle = DOT / 2
    steps = []
    for step in range(FLIP_STEPS):
        # The last step keeps a pixel of width, an edge-on dot being a line rather than nothing
        squash = max(1.0 / DOT, math.cos(math.pi / 2 * step / (FLIP_STEPS - 1)))

        tile = image(DOT, DOT)
        tile.pen = FRAME
        tile.clear()

        radius = middle * REACH

        # At rest the squash does nothing, and composing three turns rather than one moves the
        # rasterising by a pixel, which costs the dot a row of its chamfer. So a face at rest is
        # placed with the single turn its shape actually needs
        if squash == 1.0:
            placing = mat3().translate(middle + NUDGE, middle).rotate(DOT_TWIST)
        else:
            placing = mat3().translate(middle + NUDGE, middle).rotate(FLIP_AXIS) \
                            .scale(1, squash).rotate(DOT_TWIST - FLIP_AXIS)

        # Both posts are drawn, the far one first so the face covers it while the face is wide, and
        # the near one last so it always shows. Part way over the face is narrow and covers neither,
        # which is when both are in view
        post(tile, stop_angle + 180)

        # A polygon at any roundness, since the circle primitive picks its own side count and comes
        # out a row short at one end
        dot = shape.regular_polygon(0, 0, radius, DOT_SIDES)
        dot.transform = placing
        tile.pen = colour
        tile.shape(dot)

        post(tile, stop_angle)

        steps.append(tile)

    return steps


lit_steps = faces(LIT, STOP_ANGLE)
unlit_steps = faces(UNLIT, STOP_ANGLE + 180)


def dot_at(index):
    """Where the dot at this position in the grid starts on the canvas."""
    return (index % columns) * CELL + DOT_INSET, (index // columns) * CELL + DOT_INSET


def pattern_states(lines):
    """The message drawn at the sign's own resolution, read back as one state a dot.

    Anything can be drawn into the pattern, not only lettering, since what reaches the sign is
    whichever pixels came out lit.
    """
    pattern.pen = color.black
    pattern.clear()
    pattern.pen = color.white
    pattern.font = sign_font

    top = (rows - sign_font.height * len(lines)) // 2
    for line, text in enumerate(lines):
        width = int(pattern.measure_text(text)[0])
        pattern.text(text, (columns - width) // 2, top + line * sign_font.height)

    raw = pattern.raw
    stride = pattern.stride
    states = bytearray(columns * rows)
    for row in range(rows):
        for column in range(columns):
            pixel = row * stride + column * 4
            if raw[pixel] or raw[pixel + 1] or raw[pixel + 2]:
                states[row * columns + column] = 1

    return states


def show(index, lit):
    """A dot at rest, showing one face or the other."""
    x, y = dot_at(index)
    canvas.blit(lit_steps[0] if lit else unlit_steps[0], x, y)


def turning(index, phase):
    """A dot part way over, at whichever step of its turn it has reached.

    The face changes at halfway, which is the moment a real dot passes edge-on and the other side
    comes into view, so each half runs the steps in its own direction.
    """
    x, y = dot_at(index)
    if phase < 0.5:
        lit = states[index]
        step = round(phase * 2 * (FLIP_STEPS - 1))
    else:
        lit = targets[index]
        step = round((1 - phase) * 2 * (FLIP_STEPS - 1))

    canvas.blit(lit_steps[step] if lit else unlit_steps[step], x, y)


def schedule(wanted, now):
    """A start time for every dot that has to change, each column later than the one before.

    Only the dots that differ are given one, so the sign turns over what the message changed and
    leaves the rest standing, which is what makes a real board rattle in patches.
    """
    flips = []
    for index in range(columns * rows):
        if wanted[index] != states[index]:
            flips.append((index, time.ticks_add(now, (index % columns) * SWEEP_MS)))

    return flips


def advance(flips, now):
    """Draw every dot mid-turn, and hand back the ones still turning."""
    turning_still = []
    for index, start in flips:
        elapsed = time.ticks_diff(now, start)
        if elapsed < 0:
            turning_still.append((index, start))       # Its column has not come round yet
        elif elapsed >= FLIP_MS:
            show(index, targets[index])
        else:
            turning(index, elapsed / FLIP_MS)
            turning_still.append((index, start))

    return turning_still


# The board starts dark, as an unpowered one stands, so the first message turns up like any other
canvas.pen = FRAME
canvas.clear()
states = bytearray(columns * rows)
for position in range(columns * rows):
    show(position, False)

print(f"{columns} by {rows} dots at a {CELL}px pitch, {len(MESSAGES)} messages")

message = 0
targets = pattern_states(MESSAGES[0])
flips = schedule(targets, time.ticks_ms())
settled_at = time.ticks_ms()

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        now = time.ticks_ms()

        # The panel is only written while something is turning. A settled sign holds its frame, as
        # a real one holds its dots with nothing driving them
        if flips:
            flips = advance(flips, now)
            screen.update(canvas, rotation=90)

            if not flips:
                states = targets
                settled_at = time.ticks_add(now, int(HOLD * 1000))

        elif time.ticks_diff(now, settled_at) >= 0:
            message = (message + 1) % len(MESSAGES)
            targets = pattern_states(MESSAGES[message])
            flips = schedule(targets, now)

        else:
            time.sleep_ms(10)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
