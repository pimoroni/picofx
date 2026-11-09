import math
import random
from picovector import color, image, rect, shape, vec2

"""
Draw a glowing portal with arms spiralling into a dark opening and specks of light
falling in. Each arm dims to black before the opening, so it seems to fall away without
end. SCHEME chooses its colours, violet, ember, ice or emerald, and STONES = True sets it
into a stone wall.

RIM_WIDTH and RIM_HEIGHT size the portal to a cutout in front of the panel, and by default it is as
large as fits. Each frame dims the opening a little before drawing, so the motes leave fading streaks.

Drawing: Portal
Defaults: Rotation = 90
Styles: violet, ember, ice, emerald
Styles: walled, bare
Styles: round, oval
Section: Animated scenes
"""

# Constants for drawing
SCHEME = "violet"                   # The portal's colours, a name from SCHEMES, unless the entry's style names one
STONES = True                       # Whether the portal is set into a stone wall, unless the entry's style says bare
RIM_WIDTH = None                    # Panel pixels across the rim, None for as large as fits
RIM_HEIGHT = None                   # And down it
OVAL = False                        # Whether the rim stretches to fill a panel wider than it is tall, unless the entry's style says round
DIM = 60                            # How much of the last frame dims away over DIM_MS, of 255, more giving shorter streaks
DIM_MS = 167                        # The time DIM is taken over, a sixth of a second
DIM_LEAST = 17                      # The faintest dim laid at once, one of the screens' 16 levels
ANTIALIAS = image.X4

# The portal's movement
ARMS = 5                            # Glowing arms winding in
TURNS = 0.8                         # How far round an arm winds from the rim to the opening
SPIN = 0.9                          # How fast the arms turn, in radians a second
MOTES = 40                          # Motes of light falling in across the arms
FALL = 0.4                          # How fast a mote falls, of an arm's winding a second
MOTE_CURL = 0.4                     # How far round a mote winds as it falls, of an arm's winding, less falling in more directly
OPENING = 0.34                      # The dark opening's size, of the rim's

# Sizes, in panel pixels
GLOW_W = 11                         # Across an arm's glow at the rim, narrowing towards the opening
CORE_W = 2                          # Across its bright core
RIM_W = 3                           # Across the rim's bright line
MOTE_W = 2.5                        # Across a mote's streak at the rim
BAND = 20                           # How deep the ring of stones round the rim is
COURSE = 22                         # How tall a course of stones in the wall is

# Detail
POINTS = 30                         # Steps along an arm from the rim to the opening
LENGTHS = 5                         # Lengths an arm is drawn in, a colour each, which must divide into POINTS
RIM_STEPS = 48                      # Points round the rim
RIM_SHAKE = 0.04                    # How far in a point on the rim strays each frame, of the rim's size
RING_STONES = 22                    # Stones in the ring round the rim

# The screens drive the panel at 12 bit, 16 levels a channel in steps of 17, so the colours sit on those levels.
# Each scheme is an arm's colours at the rim, part way in, at its brightest and deep in, then the rim's line
# and its glow, which also falls on the stones nearest it
SCHEMES = {
    "violet": ((102, 51, 255), (204, 68, 255), (255, 170, 238), (119, 34, 136), (204, 153, 255), (153, 68, 255)),
    "ember": ((238, 68, 34), (255, 136, 51), (255, 221, 136), (119, 17, 17), (255, 187, 85), (238, 85, 17)),
    "ice": ((68, 119, 204), (136, 204, 255), (238, 238, 255), (51, 34, 136), (204, 238, 255), (85, 153, 238)),
    "emerald": ((0, 153, 85), (0, 204, 119), (238, 255, 221), (17, 85, 17), (170, 255, 34), (0, 204, 119)),
}

# The entry's style, its choices joined by a dash, such as ember-bare, each a scheme, walled or bare, or round or oval
for choice in style.split("-") if style else ():
    if choice in SCHEMES:
        SCHEME = choice
    elif choice in ("walled", "bare"):
        STONES = choice == "walled"
    elif choice in ("round", "oval"):
        OVAL = choice == "oval"
    else:
        raise ValueError(f"'{choice}' is not one of the styles! Use {', '.join(SCHEMES)}, walled or bare, round or oval")

# Is SCHEME one of them?
if SCHEME not in SCHEMES:
    raise ValueError(f"'{SCHEME}' is not one of the schemes! Set SCHEME to {', '.join(SCHEMES)}")
EDGE, PART_WAY, BRIGHTEST, DEEP, RIM_RGB, GLOW_RGB = SCHEMES[SCHEME]

# From the rim in, an arm's colours dim towards the opening's dark, and a mote's pale to white and go out there
VOID = (0, 0, 0)                    # The opening's dark, which the arms fall into and each frame dims back to
ARM_COLOURS = ((1.0, EDGE), (0.65, PART_WAY), (0.4, BRIGHTEST), (0.2, DEEP), (0.0, VOID))
MOTE_COLOURS = ((1.0, EDGE), (0.6, PART_WAY), (0.35, BRIGHTEST), (0.18, (255, 255, 255)), (0.0, VOID))
GLOW_ALPHA = 70                     # How strong an arm's glow is, of 255
RIM_LINE = color.rgb(*RIM_RGB)
RIM_GLOW = color.rgb(*GLOW_RGB).with_alpha(90)
STONE_SHADES = ((102, 102, 102), (119, 119, 119), (136, 136, 136), (153, 153, 153))
MORTAR = color.rgb(34, 34, 34)
BACKGROUND = color.black            # Behind the portal where there is no stone wall
SPILL = GLOW_RGB                    # The portal's light falling on the stones nearest it

# The canvas is the size of the screen, as the effects file turns it
WIDTH, HEIGHT = canvas.width, canvas.height
canvas.antialias = ANTIALIAS
MIDDLE_X, MIDDLE_Y = WIDTH / 2, HEIGHT / 2

# The sizes above are for a 2.8 inch panel, and scale with a shorter canvas or one pixel doubled
SCALE = min(WIDTH, HEIGHT) / 240
GLOW_W, CORE_W, RIM_W, MOTE_W, BAND = (size * SCALE for size in (GLOW_W, CORE_W, RIM_W, MOTE_W, BAND))
RIM_WIDTH = RIM_WIDTH and RIM_WIDTH * SCALE
RIM_HEIGHT = RIM_HEIGHT and RIM_HEIGHT * SCALE

# By default the rim is round and as large as fits the panel's shorter side, inside the stones or the
# panel's edge without them, so it is the same size whichever way the panel is turned
MARGIN = (BAND if STONES else 0) + 2 * SCALE
DEFAULT_SIZE = min(WIDTH, HEIGHT) - 2 * MARGIN
if OVAL:
    RIM_WIDTH, RIM_HEIGHT = WIDTH - 2 * MARGIN, HEIGHT - 2 * MARGIN
OUTER = (RIM_HEIGHT or DEFAULT_SIZE) / 2
INNER = OUTER * OPENING
SQUASH = (RIM_WIDTH or DEFAULT_SIZE) / 2 / OUTER    # The rim's width against its height
BETWEEN_ARMS = 2 * math.pi / ARMS


def colour_at(stops, reach):
    """Calculate the colour this far out from the opening, from 1 at the rim to 0 at the opening."""
    for (high, high_rgb), (low, low_rgb) in zip(stops, stops[1:]):
        if reach >= low:
            part = (reach - low) / (high - low)
            return tuple(round(b + (a - b) * part) for a, b in zip(high_rgb, low_rgb))
    return stops[-1][1]


def placed(angle, distance):
    """Find the point on the panel at an angle and a distance out from the middle, narrowed to the rim's shape."""
    return vec2(MIDDLE_X + distance * math.cos(angle) * SQUASH, MIDDLE_Y + distance * math.sin(angle))


# An arm is a logarithmic spiral, its distance out shrinking by the same share for every step round, so
# it winds evenly from just inside the rim to the opening, its glow staying inside the rim
WINDING = TURNS * 2 * math.pi
ARM_OUTER = OUTER - GLOW_W / 2 - 2 * SCALE
SHRINK = math.log(ARM_OUTER / INNER) / WINDING

# Each step along the first arm, from the rim in, as it sits before turning. Every arm is this one turned
SPIRAL = [(ARM_OUTER * math.exp(-SHRINK * angle) * math.cos(angle), ARM_OUTER * math.exp(-SHRINK * angle) * math.sin(angle))
          for angle in (WINDING * step / POINTS for step in range(POINTS + 1))]

# Each length of an arm, its glow's pen and width and its core's, the colour taken at its middle
PER_LENGTH = POINTS // LENGTHS
LENGTH_PENS = []
for length in range(LENGTHS):
    rgb = colour_at(ARM_COLOURS, 1 - (length + 0.5) / LENGTHS)
    narrowing = length / LENGTHS
    LENGTH_PENS.append((color.rgb(*rgb).with_alpha(GLOW_ALPHA), GLOW_W * (1 - 0.7 * narrowing),
                        color.rgb(*rgb), CORE_W * (1 - 0.6 * narrowing)))

# A mote's pen at each of 51 steps out from the opening, made once and not for every streak. A mote at the
# rim starts four fifths along its colours, already lit pink, so it shows against the arms' violet
MOTE_PENS = [color.rgb(*colour_at(MOTE_COLOURS, 0.8 * step / 50)) for step in range(51)]

# The direction of each point round the rim, calculated once
RIM_DIRECTIONS = [(math.cos(2 * math.pi * step / RIM_STEPS), math.sin(2 * math.pi * step / RIM_STEPS))
                  for step in range(RIM_STEPS)]
RIM_LINE_OUTER = OUTER - RIM_W * 1.5                # Where the rim's line sits at its widest, its glow reaching the edge
OPEN_PATH = shape.ALIGN_CENTER | shape.PATH_OPEN
OPENING_SHAPE = shape.ellipse(MIDDLE_X, MIDDLE_Y, OUTER * SQUASH, OUTER)
dim_pen = color.rgb(*VOID).with_alpha(0)    # The dark laid over the opening, set for each frame from the time since the last
undimmed = 0                                # The ms the opening has gone without its dark laid over it


def draw_arm(spun):
    """Draw an arm turned this far round, each length a glow under a smoothed core."""
    cosine, sine = math.cos(spun), math.sin(spun)
    points = [vec2(MIDDLE_X + (x * cosine - y * sine) * SQUASH, MIDDLE_Y + x * sine + y * cosine) for x, y in SPIRAL]
    for length, (glow, glow_w, core, core_w) in enumerate(LENGTH_PENS):
        piece = points[length * PER_LENGTH:(length + 1) * PER_LENGTH + 1]
        # The glow is wide and faint, so a rough edge to it never shows and only the core is smoothed
        canvas.antialias = image.OFF
        canvas.pen = glow
        canvas.shape(shape.custom(piece).stroke(glow_w, OPEN_PATH))
        canvas.antialias = ANTIALIAS
        canvas.pen = core
        canvas.shape(shape.custom(piece).stroke(core_w, OPEN_PATH))


def rim_points():
    """Calculate the rim's points for this frame, each strayed inward at random and smoothed with its neighbours."""
    strays = [random.uniform(0, 1) for _ in range(RIM_STEPS)]
    points = []
    for step, (across, down) in enumerate(RIM_DIRECTIONS):
        stray = (strays[step - 1] + strays[step] + strays[(step + 1) % RIM_STEPS]) / 3
        distance = RIM_LINE_OUTER * (1 - RIM_SHAKE * stray)
        points.append(vec2(MIDDLE_X + distance * across * SQUASH, MIDDLE_Y + distance * down))
    return points


class Mote:
    """A mote of light, falling in from the rim along a looser spiral than the arms'."""

    def __init__(self):
        self.restart(anywhere=True)

    def restart(self, anywhere):
        """Start the mote at the rim, or anywhere along its fall when the portal first opens."""
        self.home = random.uniform(0, 2 * math.pi)
        # How far it has fallen, in radians of an arm's winding, starting short of the opening
        self.fallen = random.uniform(0, WINDING * 0.9) if anywhere else random.uniform(0, 0.3)
        self.at = None

    def fall_and_draw(self, seconds):
        """Carry the mote in by the seconds since the last frame, and draw its streak from where it was."""
        self.fallen += FALL * WINDING * seconds
        if self.fallen > WINDING:
            self.restart(anywhere=False)
            return

        distance = ARM_OUTER * math.exp(-SHRINK * self.fallen)
        was = self.at
        self.at = placed(self.home + MOTE_CURL * self.fallen, distance)
        if was is None:
            return
        reach = max(0, (distance - INNER) / (ARM_OUTER - INNER))
        canvas.pen = MOTE_PENS[round(reach * 50)]
        # A streak narrows as it falls, to a floor that still shows
        canvas.shape(shape.line(was.x, was.y, self.at.x, self.at.y, MOTE_W * max(0.4, distance / OUTER)))


def shade(rgb, by):
    """Make a pen from a colour lightened or darkened by a step."""
    return color.rgb(*(max(0, min(255, channel + by)) for channel in rgb))


def build_wall():
    """Draw the stone wall once, its courses offset from each other, and the ring of stones round the rim."""
    canvas.antialias = image.OFF
    canvas.pen = MORTAR
    canvas.clear()
    # The wall is laid out in a 2.8 inch panel's pixels and scaled as each stone is drawn, so its
    # random draws are the same at any size and so is the pattern they make
    def scaled(left, upper, right, lower):
        """Make a rectangle from its edges in a 2.8 inch panel's pixels, scaled to the canvas, at least a pixel each way."""
        return rect(round(left * SCALE), round(upper * SCALE), max(1, round(right * SCALE) - round(left * SCALE)),
                    max(1, round(lower * SCALE) - round(upper * SCALE)))

    for row, top in enumerate(range(-4, math.ceil(HEIGHT / SCALE), COURSE)):
        x = -random.randint(0, 30) - (20 if row % 2 else 0)
        while x * SCALE < WIDTH:
            width = random.randint(34, 58)
            base = random.choice(STONE_SHADES)
            left, right, upper, lower = x + 1, x + width - 1, top + 1, top + COURSE - 1
            # Lit along the top and left and shaded along the bottom and right, then a few flecks
            canvas.pen = shade(base, -34)
            canvas.rectangle(scaled(left, upper, right, lower))
            canvas.pen = shade(base, 34)
            canvas.rectangle(scaled(left, upper, right - 1, lower - 1))
            canvas.pen = color.rgb(*base)
            canvas.rectangle(scaled(left + 1, upper + 1, right - 1, lower - 1))
            for _ in range(4):
                canvas.pen = shade(base, random.choice((-17, -34, 17)))
                fleck_x, fleck_y = random.randint(left + 2, right - 3), random.randint(upper + 2, lower - 3)
                canvas.rectangle(scaled(fleck_x, fleck_y, fleck_x + random.choice((1, 2)), fleck_y + 1))
            x += width

    canvas.pen = MORTAR
    canvas.shape(shape.ellipse(MIDDLE_X, MIDDLE_Y, (OUTER + BAND + 2 * SCALE) * SQUASH, OUTER + BAND + 2 * SCALE))
    canvas.antialias = ANTIALIAS
    for stone in range(RING_STONES):
        # A small gap either side of each stone for the mortar to show through
        first = 2 * math.pi * (stone - 0.5) / RING_STONES - math.pi / 2 + 0.014
        last = 2 * math.pi * (stone + 0.5) / RING_STONES - math.pi / 2 - 0.014
        inner = [placed(first + (last - first) * k / 4, OUTER) for k in range(5)]
        outer = [placed(last - (last - first) * k / 4, OUTER + BAND) for k in range(5)]
        base = random.choice(STONE_SHADES)
        canvas.pen = color.rgb(*base)
        canvas.shape(shape.custom(inner + outer))
        canvas.pen = shade(base, -34)
        canvas.shape(shape.custom(outer).stroke(1.5 * SCALE, OPEN_PATH))
        canvas.pen = shade(base, 34)
        canvas.shape(shape.custom(inner).stroke(1.5 * SCALE, OPEN_PATH))
        for _ in range(3):
            fleck = placed(random.uniform(first + 0.03, last - 0.03),
                           OUTER + random.uniform(4, BAND / SCALE - 4) * SCALE)
            canvas.pen = shade(base, random.choice((-17, -34, 17)))
            canvas.rectangle(rect(int(fleck.x), int(fleck.y), 2, 1))

    # The portal's light on the stones, fading with distance from the rim
    for reach, alpha in ((4 * SCALE, 70), (10 * SCALE, 40), (18 * SCALE, 22)):
        canvas.pen = color.rgb(*SPILL).with_alpha(alpha)
        canvas.shape(shape.ellipse(MIDDLE_X, MIDDLE_Y, (OUTER + reach / 2) * SQUASH, OUTER + reach / 2).stroke(reach, shape.ALIGN_CENTER))


motes = [Mote() for _ in range(MOTES)]
spun = 0.0                          # How far the arms have turned, wrapping at the angle between two arms


def draw_portal(seconds):
    """Draw one frame, the opening dimmed, the arms turned further by the seconds since the last, the motes, and the rim."""
    global spun
    spun = (spun + SPIN * seconds) % BETWEEN_ARMS
    canvas.pen = dim_pen
    canvas.shape(OPENING_SHAPE)

    for arm in range(ARMS):
        draw_arm(spun + arm * BETWEEN_ARMS)

    for mote in motes:
        mote.fall_and_draw(seconds)

    rim = rim_points()
    canvas.antialias = image.OFF
    canvas.pen = RIM_GLOW
    canvas.shape(shape.custom(rim).stroke(RIM_W * 3, shape.ALIGN_CENTER))
    canvas.antialias = ANTIALIAS
    canvas.pen = RIM_LINE
    canvas.shape(shape.custom(rim).stroke(RIM_W, shape.ALIGN_CENTER))


# Only the opening is drawn to and dimmed from now on, so the wall or the black round it is drawn once
if STONES:
    build_wall()
else:
    canvas.pen = BACKGROUND
    canvas.clear()
canvas.pen = color.rgb(*VOID)
canvas.shape(OPENING_SHAPE)


def draw():
    """Draw the portal moved on by the time since the last frame, the streaks fading by time whatever the frame rate."""
    global dim_pen, undimmed
    undimmed += ticks_delta
    alpha = round(255 * (1 - (1 - DIM / 255) ** (undimmed / DIM_MS)))
    # Whether the dark owed takes a channel down a level. A fainter one leaves the streaks short of
    # black, so at a fast frame rate it is saved up for a later frame
    if alpha < DIM_LEAST:
        alpha = 0
    else:
        undimmed = 0
    dim_pen = color.rgb(*VOID).with_alpha(alpha)
    draw_portal(ticks_delta / 1000)
