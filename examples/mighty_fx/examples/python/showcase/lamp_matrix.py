import math
import random
import time
import micropython
from mighty_fx import MightyFX, SPCE
from timing import Pacer
from screens import Screen280
from picovector import brush, color, image, mat3, rect, shape

"""
Draw a stage lighting lamp matrix, a panel of lamps in deep reflector cups running through cues.
Tungsten lamps glow up quickly and fade slowly, white hot through orange to a dull red as each
filament cools. LAMPS = "led" switches each instantly to one of a handful of colours, or off, instead.

Every stage of a lamp's glow is drawn once when the program starts, before anything is shown, and
from then on a frame only copies those drawings into place.

Press "Boot" to exit the program.
"""

# Constants for drawing
LAMPS = "tungsten"                                  # "tungsten" for filament lamps, or "led" to switch instantly in colour
LED_COLOURS = ((255, 34, 17), (255, 136, 0), (51, 255, 68),
               (34, 85, 255), (204, 68, 255))       # The colours an LED lamp can show, any lamp any of them
CUE_SECONDS = 6                                     # How long each lighting cue runs
STEP_SECONDS = 0.2                                  # How long a cue holds each step
FRAME_RATE = 10                                     # Frames a second the cues run at

COLUMNS = 7
ROWS = 5
PITCH = 44                                          # Panel pixels from one lamp to the next
RADIUS = 21                                         # A reflector cup's radius
EMITTER = 0.32                                      # How far an outermost lamp's emitter shows off its cup's middle, of the radius
PANEL = color.black
RIM = color.rgb(34, 34, 34)                         # The cup's rim, a hard edge drawn over its light
RIM_W = 2                                           # Panel pixels across the rim
BULB_RING = color.rgb(34, 34, 34)                   # An unlit emitter, a dark ring
BULB_GLASS = color.rgb(85, 85, 85)                  # Round its dull glass
ANTIALIAS = image.X4

# A tungsten lamp warms in a moment and cools slowly, its filament's colour falling with its heat
RISE_MS = 40                                        # How quickly a lamp warms, quicker than a frame so it is full on the next
FALL_MS = 450                                       # And how slowly it cools, over enough frames to pass every stage
STAGES = 5                                          # How many steps of its glow are drawn, from just lit to full
FILAMENT = ((0.0, (0, 0, 0)), (0.12, (136, 17, 0)), (0.35, (238, 68, 0)),
            (0.65, (255, 153, 34)), (1.0, (255, 238, 187)))  # Colour at each brightness, from cold to white hot
CORE_LIFT = 0.3                                     # How much hotter an emitter's middle runs than the rest of its glow

# The light a cup fills with, a ring at a time from the rim in towards the emitter, each ring's alpha
# layering over the rings before it
RINGS = (90, 70, 62, 60, 60, 62, 66, 72, 82, 96)

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# Drawn landscape and turned a quarter onto the panel at each update
canvas = screen.canvas(screen.height, screen.width)
WIDTH, HEIGHT = canvas.width, canvas.height
canvas.antialias = ANTIALIAS

LEFT = (WIDTH - COLUMNS * PITCH) // 2 + PITCH // 2
TOP = (HEIGHT - ROWS * PITCH) // 2 + PITCH // 2
SIDE = PITCH                        # A lamp's square patch, cups being a pitch apart so patches never overlap


def middle(column, row):
    """
    Find where a lamp's cup and its emitter sit on the panel.

    The panel is seen from in front of its middle, so the emitter at the back of a deep cup shows
    shifted towards the middle, by more the further out the lamp is.
    """
    x, y = LEFT + column * PITCH, TOP + row * PITCH
    # From -1 at one edge to 1 at the other, a single column or row being its own middle
    across = (column - (COLUMNS - 1) / 2) / ((COLUMNS - 1) / 2 or 1)
    down = (row - (ROWS - 1) / 2) / ((ROWS - 1) / 2 or 1)
    return x, y, x - RADIUS * EMITTER * across, y - RADIUS * EMITTER * down


def filament(level):
    """Calculate a tungsten filament's colour at a brightness from 0 to 1, between the FILAMENT stops."""
    for (low, cold), (high, hot) in zip(FILAMENT, FILAMENT[1:]):
        if level <= high:
            part = (level - low) / (high - low)
            return tuple(round(a + (b - a) * part) for a, b in zip(cold, hot))
    return FILAMENT[-1][1]


# The screens drive the panel at 12 bit, 16 levels a channel in steps of 17, so a smooth fade shows as bands.
# Each drawing is set onto those levels a pixel at a time, rounding up or down by a fixed 4x4 pattern, an
# ordered dither, which breaks the bands up and stays put as a lamp moves between stages
BAYER = bytes((0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5))


@micropython.viper
def dither(pixels: ptr8, width: int, height: int, stride: int, pattern: ptr8):
    """
    Set every pixel of an image onto the panel's levels, in place, by an ordered dither.

    A channel's part of the way to the next level rounds it up where it passes the pattern's
    threshold for that pixel, the middle of one of sixteen steps. A channel already on a level has no
    part, so it never moves. Every pixel is made opaque too. An antialiased edge can leave one just
    short, and a colour rounded up past its pixel's alpha would wrap when blitted. Compiled by viper,
    as this runs for every pixel of every drawing.
    """
    for y in range(height):
        for x in range(width):
            threshold = pattern[(y & 3) * 4 + (x & 3)]
            at = y * stride + x * 4
            for channel in range(3):
                value = pixels[at + channel]
                level = value // 17
                # Whether the part, of 17, passes the threshold's middle, (threshold + 0.5) of 16
                if (value - level * 17) * 32 > threshold * 34 + 17:
                    level += 1
                pixels[at + channel] = level * 17
            pixels[at + 3] = 255


# The rim, laid over the light so a lit cup still reads as a cup
rim_line = image(SIDE, SIDE)
rim_line.raw[:] = bytes(len(rim_line.raw))
rim_line.antialias = ANTIALIAS
rim_line.pen = RIM
rim_line.shape(shape.circle(SIDE / 2, SIDE / 2, RADIUS - RIM_W / 2).stroke(RIM_W))

# The background every lamp starts from, the black panel and every cup unlit, paler deep in around
# the emitter
background = image(WIDTH, HEIGHT)
background.antialias = ANTIALIAS
background.pen = PANEL
background.clear()
for row in range(ROWS):
    for column in range(COLUMNS):
        x, y, emitter_x, emitter_y = middle(column, row)
        for ring in range(12):
            part = ring / 11
            grey = round(26 + 26 * part)
            background.pen = color.rgb(grey, grey, grey)
            background.shape(shape.circle(x + (emitter_x - x) * part, y + (emitter_y - y) * part,
                                          RADIUS * (1 - 0.8 * part)))
        # The unlit bulb, a dark ring round dull glass
        background.pen = BULB_RING
        background.shape(shape.circle(emitter_x, emitter_y, 5))
        background.pen = BULB_GLASS
        background.shape(shape.circle(emitter_x, emitter_y, 3))
        background.blit(rim_line, x - SIDE // 2, y - SIDE // 2)
dither(background.raw, WIDTH, HEIGHT, background.stride, BAYER)

# The rects a lamp's drawing is copied through, made once, a rect built per lamp being an allocation
source = rect(0, 0, SIDE, SIDE)
target = rect(0, 0, SIDE, SIDE)
whole_patch = rect(0, 0, SIDE, SIDE)


def lit(column, row, colour, strength, core):
    """
    Draw a lamp lit, on a patch of its own over its piece of the background.

    The cup fills with the colour in rings from the rim in towards the emitter, the emitter itself a
    ring of that colour round a middle in the core colour. Strength from 0 to 1 sets how far it shows.
    """
    x, y, emitter_x, emitter_y = middle(column, row)
    left, top = x - SIDE // 2, y - SIDE // 2
    patch = image(SIDE, SIDE)
    patch.antialias = ANTIALIAS
    source.x, source.y = left, top
    patch.blit(background, source, whole_patch)

    x, y, emitter_x, emitter_y = x - left, y - top, emitter_x - left, emitter_y - top
    tint = color.rgb(*colour)
    for ring, alpha in enumerate(RINGS):
        part = ring / (len(RINGS) - 1)
        patch.pen = tint.with_alpha(round(alpha * strength))
        patch.shape(shape.circle(x + (emitter_x - x) * part, y + (emitter_y - y) * part,
                                 RADIUS * (1 - 0.7 * part)))
    patch.pen = tint.with_alpha(round(255 * strength))
    patch.shape(shape.circle(emitter_x, emitter_y, 5))
    patch.pen = color.rgb(*core).with_alpha(round(255 * strength))
    patch.shape(shape.circle(emitter_x, emitter_y, 3))

    patch.blit(rim_line, 0, 0)
    dither(patch.raw, SIDE, SIDE, patch.stride, BAYER)
    return patch


def mirrored(patch, flip_across, flip_down):
    """
    Copy a lamp's drawing flipped across the panel, down it, or both, for the lamp opposite it.

    The image pen lands a flip down one row low, and a flip down alone one column out as well, so
    those are shifted back a pixel. Found by comparing every pixel of each flip on the board.
    """
    if flip_across and flip_down:
        flip = mat3().translate(SIDE, SIDE - 1).scale(-1, -1)
    elif flip_across:
        flip = mat3().translate(SIDE, 0).scale(-1, 1)
    else:
        flip = mat3().translate(1, SIDE - 1).scale(1, -1)
    flipped = image(SIDE, SIDE)
    flipped.pen = brush.image(patch, flip)
    flipped.shape(shape.rectangle(0, 0, SIDE, SIDE))
    return flipped


def place(column, row, patch):
    """Copy a lamp's drawing into place on the canvas, or its piece of the background where it is out."""
    x, y, _, _ = middle(column, row)
    target.x, target.y = x - SIDE // 2, y - SIDE // 2
    if patch is None:
        source.x, source.y = target.x, target.y
        canvas.blit(background, source, target)
    else:
        canvas.blit(patch, target.x, target.y)


def chase(step):
    """Choose a column at a time, across the panel, in a new colour each time across."""
    colour = step // COLUMNS % len(LED_COLOURS) + 1
    return {row * COLUMNS + step % COLUMNS: colour for row in range(ROWS)}


def sweep(step):
    """Choose a row at a time, down the panel, in a new colour each time down."""
    colour = step // ROWS % len(LED_COLOURS) + 1
    return {step % ROWS * COLUMNS + column: colour for column in range(COLUMNS)}


def wave(step):
    """Choose a diagonal at a time, from the top left corner out, each diagonal in the next colour."""
    diagonals = COLUMNS + ROWS - 1
    colour = step % len(LED_COLOURS) + 1
    return {row * COLUMNS + column: colour for row in range(ROWS) for column in range(COLUMNS)
            if column + row == step % diagonals}


def sparkle(_step):
    """Choose a handful of lamps at random, each in a colour at random."""
    return {random.randrange(COLUMNS * ROWS): random.randrange(len(LED_COLOURS)) + 1 for _ in range(6)}


def checker(step):
    """Choose alternate lamps, swapping every third step so a lamp has cooled before it lights again."""
    colour = step // 3 % len(LED_COLOURS) + 1
    return {row * COLUMNS + column: colour for row in range(ROWS) for column in range(COLUMNS)
            if (column + row + step // 3) % 2 == 0}


# The lighting cues in the order they run. Each chooses the lamps lit at a step of it, as indexes
# counting along each row in turn, and the colour each shows, from 1 for the first of LED_COLOURS.
# A tungsten lamp is simply lit, whatever colour it is given
CUES = (chase, sweep, wave, sparkle, checker)

if LAMPS not in ("tungsten", "led"):
    raise ValueError(f'LAMPS is {LAMPS!r}. Set it to "tungsten" or "led"')
TUNGSTEN = LAMPS == "tungsten"

# The screen stays dark until its first frame, so every stage of each lamp is drawn first
marked = time.ticks_ms()
stages = []
for row in range(ROWS):
    for column in range(COLUMNS):
        opposite_column, opposite_row = min(column, COLUMNS - 1 - column), min(row, ROWS - 1 - row)
        # Whether this lamp is past the panel's middle, the mirror image of the one opposite it
        if (opposite_column, opposite_row) != (column, row):
            opposite = stages[opposite_row * COLUMNS + opposite_column]
            stages.append([None] + [mirrored(patch, column != opposite_column, row != opposite_row)
                                    for patch in opposite[1:]])
            continue

        if TUNGSTEN:
            # A stage's strength rises quicker than its colour, so a dim filament still shows, and the
            # emitter's middle runs hotter than the rest
            drawn = [lit(column, row, filament(stage / STAGES), min(1, stage / STAGES * 1.4),
                         filament(min(1, stage / STAGES + CORE_LIFT)))
                     for stage in range(1, STAGES + 1)]
        else:
            # An LED lamp in each of its colours, its emitter's middle paler
            drawn = [lit(column, row, colour, 1, tuple(min(255, channel + 140) for channel in colour))
                     for colour in LED_COLOURS]
        stages.append([None] + drawn)
print(f"{len(stages)} lamps drawn in {time.ticks_diff(time.ticks_ms(), marked)}ms, {len(stages[0]) - 1} each")

# The panel starts with every lamp out, and each is copied into place on the first frame
canvas.blit(background, 0, 0)
levels = [0.0] * (COLUMNS * ROWS)   # How lit each lamp is, from 0 to 1
shown = [None] * (COLUMNS * ROWS)
STEP_FRAMES = max(1, round(STEP_SECONDS * FRAME_RATE))
CUE_FRAMES = max(1, round(CUE_SECONDS * FRAME_RATE))
frame = 0
pacer = Pacer(fps=FRAME_RATE)       # The matrix's clock, holding each frame to the rate

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        if frame % STEP_FRAMES == 0:
            # Each cue counts its steps from its own start, so a pattern begins at its beginning
            cue = CUES[frame // CUE_FRAMES % len(CUES)]
            lit_now = cue(frame % CUE_FRAMES // STEP_FRAMES)

        changed = False
        for index in range(COLUMNS * ROWS):
            if TUNGSTEN:
                # A filament heats and cools towards where it is driven, quickly up and slowly down
                wanted = 1.0 if index in lit_now else 0.0
                settle = RISE_MS if wanted > levels[index] else FALL_MS
                levels[index] += (wanted - levels[index]) * (1 - math.exp(-pacer.delta / settle))
                stage = round(levels[index] * STAGES)
            else:
                # An LED lamp shows its colour at once, 0 being off
                stage = lit_now.get(index, 0)

            if stage != shown[index]:
                place(index % COLUMNS, index // COLUMNS, stages[index][stage])
                shown[index] = stage
                changed = True

        if changed:
            screen.update(canvas, rotation=90)

        frame += 1
        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
