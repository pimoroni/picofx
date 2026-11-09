import math
from picovector import color, image, rect, shape

"""
Draw a laser show of beams fanning and sweeping across a dark hall. Each scene runs a few
seconds, switching its projectors on and off as it goes. An upright panel, like a square 1.54" one,
has room for the outer two projectors only.

A beam is a line from its projector to the edge of the panel, a wide faint glow under a thin
bright core. Each frame dims the last a little before drawing, so a sweeping beam leaves a fading
sheet behind it, as a beam seen through haze seems to.

Drawing: Laser show
Defaults: Rotation = 90
Section: Animated scenes
"""

# Constants for drawing
SCENE_SECONDS = 6                           # How long each scene runs
SWITCH_SECONDS = 1.5                        # How long the projectors stay switched as they are, within a scene
DIM = 90                                    # How much of the last frame dims away over DIM_MS, of 255, more giving a shorter afterglow
DIM_MS = 125                                # The time DIM is taken over, an eighth of a second
DIM_LEAST = 17                              # The faintest dim laid at once, one of the screens' 16 levels
# The angles in degrees each projector fires across, left, middle and right, 0 being straight up and positive
# to the right. The outer two fire into the hall, leaning only a little towards their own wall
ARCS = ((-15, 70), (-70, 70), (-70, 15))
ANTIALIAS = image.X4                        # A beam is all edge

# The screens drive the panel at 12 bit, 16 levels a channel in steps of 17, so the colours sit on those levels
GREEN = (51, 255, 68)
RED = (255, 34, 34)
BLUE = (68, 102, 255)
CYAN = (34, 238, 255)
MAGENTA = (255, 51, 221)
CORE_LIFT = 136                             # How much paler than its colour a beam's core is, a whole number of levels
HALO_ALPHA = 60                             # How strong a beam's glow is, of 255
HALL = color.black                          # The dark the beams cross
HOUSING = color.rgb(68, 68, 68)             # A projector's housing
LENS_ON = color.white                       # The lens of a projector switched on
LENS_OFF = color.rgb(34, 34, 34)            # And switched off

# Sizes, in pixels of a 2.8 inch panel on its side
CORE_W = 1.5                                # Across a beam's core
HALO_W = 6                                  # And across the glow round it
LENS = 3                                    # A projector's lens radius
RAISED = 6                                  # How far above the panel's foot a beam starts, a projector's housing reaching down to it
HOUSING_W = 16                              # Across a projector's housing

# The canvas is the size of the screen, as the effects file turns it
WIDTH, HEIGHT = canvas.width, canvas.height
canvas.antialias = ANTIALIAS
NARROW = WIDTH <= HEIGHT            # Whether the hall is too narrow for the middle projector, being upright or square

# The sizes above scale with a shorter canvas or one pixel doubled
SCALE = min(WIDTH, HEIGHT) / 240
CORE_W, HALO_W, LENS, RAISED, HOUSING_W = (size * SCALE for size in (CORE_W, HALO_W, LENS, RAISED, HOUSING_W))

# The projectors along the foot of the stage, left, middle and right, the middle one only in a wide hall
PROJECTORS = ((WIDTH * 0.1, HEIGHT - RAISED), (WIDTH * 0.5, HEIGHT - RAISED), (WIDTH * 0.9, HEIGHT - RAISED))
FITTED = (0, 2) if NARROW else (0, 1, 2)
REACH = math.sqrt(WIDTH ** 2 + HEIGHT ** 2)         # Further than any beam can need, for an edge it never meets
hall = rect(0, 0, WIDTH, HEIGHT)
dim_pen = HALL.with_alpha(0)        # The dark laid over the last frame, set for each frame from the time since the last
undimmed = 0                        # The ms the hall has gone without its dark laid over it

# Every projector's housing and lens made once, a shape built per frame being an allocation
HOUSINGS = [shape.rounded_rectangle(rect(x - HOUSING_W / 2, y - 4 * SCALE, HOUSING_W, RAISED + 4 * SCALE),
                                    *([2 * SCALE] * 4)) for x, y in PROJECTORS]
LENSES = [shape.circle(x, y - 2 * SCALE, LENS) for x, y in PROJECTORS]


def pens(colour):
    """Make the pair of pens a beam is drawn with, a faint glow of its colour and a core paled towards white."""
    return (color.rgb(*colour).with_alpha(HALO_ALPHA),
            color.rgb(*(min(255, channel + CORE_LIFT) for channel in colour)))


def beam(projector, angle, glow_and_core):
    """
    Draw a beam from a projector at an angle in degrees, 0 being straight up and positive to the right,
    in a pair of pens from pens().

    It stops just past whichever edge of the panel it meets first, as drawing a beam further costs
    time for nothing.
    """
    x, y = PROJECTORS[projector]
    heading = math.radians(angle)
    across, up = math.sin(heading), math.cos(heading)
    # How far along the beam the side it leans towards is, if it leans at all
    if across > 0:
        to_side = (WIDTH + HALO_W - x) / across
    elif across < 0:
        to_side = (-HALO_W - x) / across
    else:
        to_side = REACH
    to_top = (y + HALO_W) / up if up > 0 else REACH
    reach = min(to_side, to_top)
    end_x, end_y = x + reach * across, y - reach * up
    # Only the core is smoothed, as the glow is too faint for a rough edge to show. That keeps most
    # of the antialiasing's cost off the frame
    glow, core = glow_and_core
    canvas.antialias = image.OFF
    canvas.pen = glow
    canvas.shape(shape.line(x, y, end_x, end_y, HALO_W))
    canvas.antialias = ANTIALIAS
    canvas.pen = core
    canvas.shape(shape.line(x, y, end_x, end_y, CORE_W))


def aimed(projector, aim):
    """Calculate the angle a projector fires at for an aim from -1 to 1 across its arc."""
    low, high = ARCS[projector]
    return low + (high - low) * (aim + 1) / 2


# Each scene's pens for its projectors, left to right, made once and not for every beam
FAN_PENS = tuple(pens(colour) for colour in (RED, GREEN, BLUE))
SCANNER_PENS = tuple(pens(colour) for colour in (CYAN, GREEN, MAGENTA))
TUNNEL_PENS = tuple(pens(colour) for colour in (GREEN, CYAN, GREEN))
STEP_PENS = tuple(pens(colour) for colour in (MAGENTA, RED, MAGENTA))


# The scenes, each given the seconds into the show and the projectors switched on, left 0 to right 2
def fans(seconds, on):
    """Spread a fan of beams from each projector across its arc, opening and closing."""
    spread = 0.12 + 0.1 * math.sin(seconds * 1.3)
    for projector in on:
        for ray in range(-3, 4):
            beam(projector, aimed(projector, ray * spread), FAN_PENS[projector])


def scanners(seconds, on):
    """Sweep one beam from each projector across its arc and back, each out of step with the others."""
    for projector in on:
        beam(projector, aimed(projector, math.sin(seconds * 1.8 + projector * 1.5)), SCANNER_PENS[projector])


def tunnel(seconds, on):
    """Aim each projector at one moving point, the beams meeting like the sides of a cone."""
    target_x = WIDTH / 2 + WIDTH * 0.3 * math.sin(seconds * 0.9)
    target_y = HEIGHT * 0.35 + HEIGHT * 0.2 * math.sin(seconds * 1.4)
    for projector in on:
        x, y = PROJECTORS[projector]
        angle = math.degrees(math.atan2(target_x - x, y - target_y))
        for ray in (-4, 0, 4):
            beam(projector, angle + ray, TUNNEL_PENS[projector])


def steps(seconds, on):
    """Jump a ring of beams across each projector's arc in steps, a new place every fifth of a second."""
    step = int(seconds * 5)
    for projector in on:
        for ray in range(4):
            aim = ((step + ray * 3 + projector * 2) % 12 - 5.5) / 5.5
            beam(projector, aimed(projector, aim), STEP_PENS[projector])


# Each scene with the projectors it switches on in turn, a set every SWITCH_SECONDS, in a wide hall and then a narrow one
RUNNING_ORDER = ((fans, ((1,), (0, 2), (0, 1, 2), (0, 1, 2)), ((0,), (2,), (0, 2), (0, 2))),
                 (scanners, ((0,), (2,), (0, 2), (0, 1, 2)), ((0,), (2,), (0, 2), (0, 2))),
                 (tunnel, ((0, 1, 2),), ((0, 2),)),
                 (steps, ((1,), (0, 2), (0, 1, 2), (1,)), ((0, 2), (2,), (0,), (0, 2))))
SCENES = tuple((scene, narrow if NARROW else wide) for scene, wide, narrow in RUNNING_ORDER)
CYCLE_MS = round(SCENE_SECONDS * len(SCENES) * 1000)


def draw_show(seconds):
    """Draw one frame, the last dimmed into the hall, then the beams of the scene running now."""
    canvas.pen = dim_pen
    canvas.rectangle(hall)

    scene, switching = SCENES[int(seconds / SCENE_SECONDS) % len(SCENES)]
    on = switching[int(seconds % SCENE_SECONDS / SWITCH_SECONDS) % len(switching)]
    scene(seconds, on)

    # Draw the projectors over their beams, each lens lit only while its projector is on
    for projector in FITTED:
        canvas.pen = HOUSING
        canvas.shape(HOUSINGS[projector])
        canvas.pen = LENS_ON if projector in on else LENS_OFF
        canvas.shape(LENSES[projector])


canvas.pen = HALL
canvas.clear()


def draw():
    """Draw the show for the time the drawing has played, the afterglow fading by time whatever the frame rate."""
    global dim_pen, undimmed
    undimmed += ticks_delta
    alpha = round(255 * (1 - (1 - DIM / 255) ** (undimmed / DIM_MS)))
    # Whether the dark owed takes a channel down a level. A fainter one leaves the beams' sheets short
    # of black, so at a fast frame rate it is saved up for a later frame
    if alpha < DIM_LEAST:
        alpha = 0
    else:
        undimmed = 0
    dim_pen = HALL.with_alpha(alpha)
    # Kept in whole milliseconds until the fraction is wanted, as a float of hours of running loses it
    draw_show(ticks % CYCLE_MS / 1000)
