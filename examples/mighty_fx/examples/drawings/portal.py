import math
import random
from picovector import color, image, rect, shape, vec2

"""
Drawing: Portal
A portal, glowing arms winding in towards a dark opening with motes of light falling in, set in a stone wall.
Section: Animation
"""

# Entry: screenA rotation=90: graphics file=portal.py fps=6   (a 2.8" screen)

# Constants for drawing
STONES = True                                       # Whether the portal is set into a stone wall
PORTRAIT = False                                    # Whether the panel stands upright, which turns the stones and the default shape with it
RIM_WIDTH = None                                    # Panel pixels across the rim, None for as large as fits
RIM_HEIGHT = None                                   # And down it
DIM = 60                                            # How much of the last frame each frame dims away, of 255, more giving shorter streaks
ANTIALIAS = image.X4

# The portal's movement
ARMS = 5                                            # Glowing arms winding in
TURNS = 0.8                                         # How far round an arm winds from the rim to the opening
SPIN = 0.9                                          # How fast the arms turn, in radians a second
MOTES = 40                                          # Motes of light falling in across the arms
FALL = 0.4                                          # How fast a mote falls, of an arm's winding a second
MOTE_CURL = 0.4                                     # How far round a mote winds as it falls, of an arm's winding, less falling in more directly
OPENING = 0.34                                      # The dark opening's size, of the rim's

# Sizes, in panel pixels
GLOW_W = 11                                         # Across an arm's glow at the rim, narrowing towards the opening
CORE_W = 2                                          # Across its bright core
RIM_W = 3                                           # Across the rim's bright line
MOTE_W = 2.5                                        # Across a mote's streak at the rim
BAND = 20                                           # How deep the ring of stones round the rim is
COURSE = 22                                         # How tall a course of stones in the wall is

# Detail
POINTS = 30                                         # Steps along an arm from the rim to the opening
LENGTHS = 5                                         # Lengths an arm is drawn in, a colour each, which POINTS must divide into
RIM_STEPS = 48                                      # Points round the rim
RIM_SHAKE = 0.04                                    # How far in a point on the rim strays each frame, of the rim's size
RING_STONES = 22                                    # Stones in the ring round the rim

# The screens drive the panel at 12 bit, 16 levels a channel in steps of 17, so the colours sit on those levels.
# From the rim in, an arm's colours dim towards black, and a mote's pale to white and go out at the opening
ARM_COLOURS = ((1.0, (102, 51, 255)), (0.65, (204, 68, 255)), (0.4, (255, 170, 238)),
               (0.2, (119, 34, 136)), (0.0, (0, 0, 0)))
MOTE_COLOURS = ((1.0, (102, 51, 255)), (0.6, (204, 68, 255)), (0.35, (255, 170, 238)),
                (0.18, (255, 255, 255)), (0.0, (0, 0, 0)))
GLOW_ALPHA = 70                                     # How strong an arm's glow is, of 255
RIM_LINE = color.rgb(204, 153, 255)
RIM_GLOW = color.rgb(153, 68, 255).with_alpha(90)
STONE_SHADES = ((102, 102, 102), (119, 119, 119), (136, 136, 136), (153, 153, 153))
MORTAR = color.rgb(34, 34, 34)
SPILL = (153, 68, 255)                              # The portal's light falling on the stones nearest it

# The canvas this drawing expects, a 2.8" screen upright or at rotation=90. The module body cannot see
# the canvas, and the layout below is built from it, so it is stated and checked on the first call
WIDTH, HEIGHT = (240, 320) if PORTRAIT else (320, 240)
canvas = None                       # The canvas draw() is given, kept for the functions below
MIDDLE_X, MIDDLE_Y = WIDTH / 2, HEIGHT / 2

# By default the rim is as large as fits inside the stones, or the panel's edge without them. Upright it
# takes the panel's shape, and on its side it is round
MARGIN = BAND + 2 if STONES else 2
DEFAULT_HEIGHT = HEIGHT - 2 * MARGIN
DEFAULT_WIDTH = DEFAULT_HEIGHT * WIDTH / HEIGHT if PORTRAIT else DEFAULT_HEIGHT
OUTER = (RIM_HEIGHT or DEFAULT_HEIGHT) / 2
INNER = OUTER * OPENING
SQUASH = (RIM_WIDTH or DEFAULT_WIDTH) / 2 / OUTER   # The rim's width against its height
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
ARM_OUTER = OUTER - GLOW_W / 2 - 2
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
DIM_PEN = color.black.with_alpha(DIM)


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
    for row, top in enumerate(range(-4, HEIGHT, COURSE)):
        x = -random.randint(0, 30) - (20 if row % 2 else 0)
        while x < WIDTH:
            width = random.randint(34, 58)
            base = random.choice(STONE_SHADES)
            left, right, upper, lower = x + 1, x + width - 1, top + 1, top + COURSE - 1
            # Lit along the top and left and shaded along the bottom and right, then a few flecks
            canvas.pen = shade(base, -34)
            canvas.rectangle(rect(left, upper, right - left, lower - upper))
            canvas.pen = shade(base, 34)
            canvas.rectangle(rect(left, upper, right - left - 1, lower - upper - 1))
            canvas.pen = color.rgb(*base)
            canvas.rectangle(rect(left + 1, upper + 1, right - left - 2, lower - upper - 2))
            for _ in range(4):
                canvas.pen = shade(base, random.choice((-17, -34, 17)))
                canvas.rectangle(rect(random.randint(left + 2, right - 3), random.randint(upper + 2, lower - 3), random.choice((1, 2)), 1))
            x += width

    canvas.pen = MORTAR
    canvas.shape(shape.ellipse(MIDDLE_X, MIDDLE_Y, (OUTER + BAND + 2) * SQUASH, OUTER + BAND + 2))
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
        canvas.shape(shape.custom(outer).stroke(1.5, OPEN_PATH))
        canvas.pen = shade(base, 34)
        canvas.shape(shape.custom(inner).stroke(1.5, OPEN_PATH))
        for _ in range(3):
            fleck = placed(random.uniform(first + 0.03, last - 0.03), OUTER + random.uniform(4, BAND - 4))
            canvas.pen = shade(base, random.choice((-17, -34, 17)))
            canvas.rectangle(rect(int(fleck.x), int(fleck.y), 2, 1))

    # The portal's light on the stones, fading with distance from the rim
    for reach, alpha in ((4, 70), (10, 40), (18, 22)):
        canvas.pen = color.rgb(*SPILL).with_alpha(alpha)
        canvas.shape(shape.ellipse(MIDDLE_X, MIDDLE_Y, (OUTER + reach / 2) * SQUASH, OUTER + reach / 2).stroke(reach, shape.ALIGN_CENTER))


motes = [Mote() for _ in range(MOTES)]
spun = 0.0                          # How far the arms have turned, wrapping at the angle between two arms


def draw_frame(seconds):
    """Draw one frame, the opening dimmed, the arms turned further by the seconds since the last, the motes, and the rim."""
    global spun
    spun = (spun + SPIN * seconds) % BETWEEN_ARMS
    canvas.pen = DIM_PEN
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


last = None                         # The elapsed seconds at the last frame


def draw(given, elapsed):
    global canvas, last
    if last is None:
        if (given.width, given.height) != (WIDTH, HEIGHT):
            raise ValueError(f'this drawing is laid out for {WIDTH}x{HEIGHT}, a 2.8" screen '
                             f"{'upright' if PORTRAIT else 'at rotation=90'}, and was given {given.width}x{given.height}")
        canvas = given
        canvas.antialias = ANTIALIAS

        # Only the opening is drawn to and dimmed from now on, so the wall or the black round it is drawn once
        if STONES:
            build_wall()
        else:
            canvas.pen = color.black
            canvas.clear()
        canvas.pen = color.black
        canvas.shape(OPENING_SHAPE)
        last = elapsed

    draw_frame(max(0.0, elapsed - last))
    last = elapsed
