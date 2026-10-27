import math
from mighty_fx import MightyFX, SPCE
from timing import Pacer, Roller
from screens import Screen280
from picovector import color, font, image, mat3, shape

"""
Draw a flip-dot sign, spelling its message in dots that turn over one column after the next.

Press "Boot" to exit the program.

Section: Mechanical and glowing displays
"""

# Constants for drawing
SIGN_FONT = font.match              # The boldest face that fits five characters a line, a pixel to a dot
CELL = 10                           # The dot pitch in pixels, which sets how much the sign holds
DOT_SIDES = 8                       # Octagonal dots, as one type has. 16 gives the round type, which shows from a CELL of about 14
DOT_TWIST = 22.5                    # Turns the octagon so its flats face up and along, as a real one sits
DOT_INSET = 1                       # How much of the frame shows between one dot and the next
FLIP_AXIS = 45                      # The angle of the diagonal a dot turns about, corner to corner
# Two posts a cell across the turning axis, the dark face resting on the one opposite the lit face's
STOP_ANGLE = 135                    # The post the lit face rests against, bottom left as seen
PIN_SHARE = 0.25                    # A post's size against the dot's, so detail grows with the pitch
FLIP_STEPS = 6                      # How many faces a turn is drawn with, one to a frame
LIT = color.rgb(240, 230, 40)       # A dot showing its yellow face
UNLIT = color.rgb(48, 46, 44)       # And its dark one, which a real dot still shows plainly
STOP = color.rgb(90, 88, 84)        # The posts, lighter than either face so they read as parts
FRAME = color.black                 # What the dots are set into
# Set in whole frames, as a turn spanning fewer arrives in two or three steps
FLIP_MS = 420                       # How long one dot takes to turn over
SWEEP_MS = 70                       # How much later each column starts turning than the one before
HOLD = 4.0                          # How long a message stays up once the board has settled

# What the sign shows, a line to a row of lettering. A board this wide holds four or five characters
# a line. The first two share a destination, so that change turns over only the time
MESSAGES = (
    ("CITY", "12:04"),
    ("CITY", "12:11"),
    ("DOCK", "12:26"),
    ("WEST", "12:40"),
)

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# Drawn landscape and turned a quarter onto the panel at each update
canvas = screen.canvas(screen.height, screen.width)
columns = canvas.width // CELL
rows = canvas.height // CELL

# One pixel to a dot, the sign's own resolution, for the lettering
pattern = image(columns, rows)

DOT = CELL - DOT_INSET * 2

# A radius reaching the flats to the tile's edge, and a half-pixel nudge that keeps every corner
# chamfered. CELL and DOT_INSET give the eight pixels that chamfer evenly
REACH = 1.0 / math.cos(math.pi / DOT_SIDES)
NUDGE = 0.5

# A post in whole pixels grows with the pitch. Its octagon comes out a square with cut corners
PIN_PIXELS = max(2, round(DOT * PIN_SHARE))
PIN_AT = PIN_PIXELS // 2
PIN_REACH = 1.0 / math.cos(math.pi / 8)


def post(tile, angle):
    """Draw one of a cell's two posts, where it is seen. The carrier holds them, so they never move."""
    seen = math.radians(angle)
    x = PIN_AT if math.cos(seen) < 0 else DOT - PIN_AT - PIN_PIXELS
    y = PIN_AT if math.sin(seen) < 0 else DOT - PIN_AT - PIN_PIXELS

    standing = shape.regular_polygon(0, 0, PIN_PIXELS / 2 * PIN_REACH, 8)
    standing.transform = mat3().translate(x + PIN_PIXELS / 2 + NUDGE, y + PIN_PIXELS / 2) \
                               .rotate(DOT_TWIST)
    tile.pen = STOP
    tile.shape(standing)


def faces(colour, stop_angle):
    """
    Bake a face at every step of its turn, from flat on to edge on.

    A dot turns about one diagonal, so it narrows across that line. stop_angle is the post it
    rests on at the other's end. Each tile carries its frame, so a turning dot costs one blit.
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

        # A face at rest takes the single turn it needs, as composing three shifts
        # the rasteriser a pixel and costs a row of chamfer
        if squash == 1.0:
            placing = mat3().translate(middle + NUDGE, middle).rotate(DOT_TWIST)
        else:
            placing = mat3().translate(middle + NUDGE, middle).rotate(FLIP_AXIS) \
                            .scale(1, squash).rotate(DOT_TWIST - FLIP_AXIS)

        # The far post first so a wide face covers it, and the near one last so it always shows
        post(tile, stop_angle + 180)

        # A polygon, as the circle primitive comes out a row short at one end
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
    """
    Draw the message at the sign's resolution and read it back as a state a dot.

    Anything drawn here reaches the sign.
    """
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
    states = bytearray(columns * rows)
    for row in range(rows):
        for column in range(columns):
            pixel = row * stride + column * 4
            if raw[pixel] or raw[pixel + 1] or raw[pixel + 2]:
                states[row * columns + column] = 1

    return states


def show(index, lit):
    """Draw a dot at rest, showing one face or the other."""
    x, y = dot_at(index)
    canvas.blit(lit_steps[0] if lit else unlit_steps[0], x, y)


def turning(index, phase):
    """Draw a dot part way over. The face changes at halfway, when a real dot passes edge-on."""
    x, y = dot_at(index)
    if phase < 0.5:
        lit = states[index]
        step = round(phase * 2 * (FLIP_STEPS - 1))
    else:
        lit = targets[index]
        step = round((1 - phase) * 2 * (FLIP_STEPS - 1))

    canvas.blit(lit_steps[step] if lit else unlit_steps[step], x, y)


def schedule(wanted):
    """
    How far into the sweep each dot that has to change starts turning, each column later than the last.

    Only what the message changed turns.
    """
    flips = []
    for index in range(columns * rows):
        if wanted[index] != states[index]:
            flips.append((index, (index % columns) * SWEEP_MS))

    return flips


def advance(flips, elapsed):
    """Draw every dot mid-turn, and hand back the ones still turning."""
    turning_still = []
    for index, start in flips:
        into = elapsed - start
        if into < 0:
            turning_still.append((index, start))       # Its column has not come round yet
        elif into >= FLIP_MS:
            show(index, targets[index])
        else:
            turning(index, into / FLIP_MS)
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
flips = schedule(targets)

# The pacer's elapsed time counts from the start of the sweep in progress
pacer = Pacer(0.01)
settled = Roller(HOLD)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Write the panel only while something turns, as a settled sign holds its frame
        if flips:
            flips = advance(flips, pacer.elapsed)
            screen.update(canvas, rotation=90)

            if not flips:
                # The sweep is done, so the sign stands at the new message
                states = targets
                settled.restart()

        elif settled.is_due():
            message = (message + 1) % len(MESSAGES)
            targets = pattern_states(MESSAGES[message])
            flips = schedule(targets)
            pacer.restart()

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
