import math
from picovector import color, image, rect, shape

"""
Drawing: Laser show
Beams fanning and sweeping across a dark hall from projectors along the foot of the stage, each leaving a fading sheet.
Section: Animation
"""

# Entry: screenA rotation=90: graphics file=laser_show.py fps=8   (a 2.8" screen)

# Constants for drawing
PORTRAIT = False                                    # Whether the panel stands upright, room for two projectors and not three
SCENE_SECONDS = 6                                   # How long each scene runs
SWITCH_SECONDS = 1.5                                # How long the projectors stay switched as they are, within a scene
DIM = 90                                            # How much of the last frame each frame dims away, of 255, more giving a shorter afterglow
# The angles in degrees each projector fires across, left, middle and right, 0 being straight up and positive
# to the right. The outer two fire into the hall, leaning only a little towards their own wall
ARCS = ((-15, 70), (-70, 70), (-70, 15))
ANTIALIAS = image.X4                                # A beam is all edge

# The screens drive the panel at 12 bit, 16 levels a channel in steps of 17, so the colours sit on those levels
GREEN = (51, 255, 68)
RED = (255, 34, 34)
BLUE = (68, 102, 255)
CYAN = (34, 238, 255)
MAGENTA = (255, 51, 221)
CORE_LIFT = 136                                     # How much paler than its colour a beam's core is, a whole number of levels
HALO_ALPHA = 60                                     # How strong a beam's glow is, of 255
HALL = color.black                                  # The dark the beams cross
HOUSING = color.rgb(68, 68, 68)                     # A projector's housing
LENS_OFF = color.rgb(34, 34, 34)                    # The lens of a projector switched off

# Sizes, in panel pixels
CORE_W = 1.5                                        # Across a beam's core
HALO_W = 6                                          # And across the glow round it
LENS = 3                                            # A projector's lens radius
RAISED = 6                                          # How far above the panel's foot a beam starts, a projector's housing reaching down to it

# The canvas this drawing expects, a 2.8" screen at rotation=90, or at rotation=0 with PORTRAIT. The module
# body cannot see the canvas, and the layout below is built from it, so it is stated and checked on the first call
WIDTH, HEIGHT = (240, 320) if PORTRAIT else (320, 240)

# The projectors along the foot of the stage, left, middle and right, the middle one only in landscape
PROJECTORS = ((WIDTH * 0.1, HEIGHT - RAISED), (WIDTH * 0.5, HEIGHT - RAISED), (WIDTH * 0.9, HEIGHT - RAISED))
FITTED = (0, 2) if PORTRAIT else (0, 1, 2)
REACH = math.sqrt(WIDTH ** 2 + HEIGHT ** 2)         # Further than any beam can need, for an edge it never meets
hall = rect(0, 0, WIDTH, HEIGHT)
DIM_PEN = HALL.with_alpha(DIM)

# Every projector's housing and lens made once, a shape built per frame being an allocation
HOUSINGS = [shape.rounded_rectangle(rect(x - 8, y - 4, 16, RAISED + 4), 2, 2, 2, 2) for x, y in PROJECTORS]
LENSES = [shape.circle(x, y - 2, LENS) for x, y in PROJECTORS]


def pens(colour):
    """Make the pair of pens a beam is drawn with, a faint glow of its colour and a core paled towards white."""
    return (color.rgb(*colour).with_alpha(HALO_ALPHA),
            color.rgb(*(min(255, channel + CORE_LIFT) for channel in colour)))


def beam(canvas, projector, angle, glow_and_core):
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
def fans(canvas, seconds, on):
    """Spread a fan of beams from each projector across its arc, opening and closing."""
    spread = 0.12 + 0.1 * math.sin(seconds * 1.3)
    for projector in on:
        for ray in range(-3, 4):
            beam(canvas, projector, aimed(projector, ray * spread), FAN_PENS[projector])


def scanners(canvas, seconds, on):
    """Sweep one beam from each projector across its arc and back, each out of step with the others."""
    for projector in on:
        beam(canvas, projector, aimed(projector, math.sin(seconds * 1.8 + projector * 1.5)), SCANNER_PENS[projector])


def tunnel(canvas, seconds, on):
    """Aim each projector at one moving point, the beams meeting like the sides of a cone."""
    target_x = WIDTH / 2 + WIDTH * 0.3 * math.sin(seconds * 0.9)
    target_y = HEIGHT * 0.35 + HEIGHT * 0.2 * math.sin(seconds * 1.4)
    for projector in on:
        x, y = PROJECTORS[projector]
        angle = math.degrees(math.atan2(target_x - x, y - target_y))
        for ray in (-4, 0, 4):
            beam(canvas, projector, angle + ray, TUNNEL_PENS[projector])


def steps(canvas, seconds, on):
    """Jump a ring of beams across each projector's arc in steps, a new place every fifth of a second."""
    step = int(seconds * 5)
    for projector in on:
        for ray in range(4):
            aim = ((step + ray * 3 + projector * 2) % 12 - 5.5) / 5.5
            beam(canvas, projector, aimed(projector, aim), STEP_PENS[projector])


# Each scene with the projectors it switches on in turn, a set every SWITCH_SECONDS, in landscape and then in portrait
RUNNING_ORDER = ((fans, ((1,), (0, 2), (0, 1, 2), (0, 1, 2)), ((0,), (2,), (0, 2), (0, 2))),
                 (scanners, ((0,), (2,), (0, 2), (0, 1, 2)), ((0,), (2,), (0, 2), (0, 2))),
                 (tunnel, ((0, 1, 2),), ((0, 2),)),
                 (steps, ((1,), (0, 2), (0, 1, 2), (1,)), ((0, 2), (2,), (0,), (0, 2))))
SCENES = tuple((scene, portrait if PORTRAIT else landscape) for scene, landscape, portrait in RUNNING_ORDER)
CYCLE = SCENE_SECONDS * len(SCENES)            # Seconds before the show repeats


def draw_show(canvas, seconds):
    """Draw one frame, the last dimmed into the hall, then the beams of the scene running now."""
    canvas.pen = DIM_PEN
    canvas.rectangle(hall)

    scene, switching = SCENES[int(seconds / SCENE_SECONDS) % len(SCENES)]
    on = switching[int(seconds % SCENE_SECONDS / SWITCH_SECONDS) % len(switching)]
    scene(canvas, seconds, on)

    # Draw the projectors over their beams, each lens lit only while its projector is on
    for projector in FITTED:
        canvas.pen = HOUSING
        canvas.shape(HOUSINGS[projector])
        canvas.pen = color.white if projector in on else LENS_OFF
        canvas.shape(LENSES[projector])


started = False


def draw(canvas, elapsed):
    global started
    if not started:
        if (canvas.width, canvas.height) != (WIDTH, HEIGHT):
            raise ValueError(f'this drawing is laid out for {WIDTH}x{HEIGHT}, a 2.8" screen at '
                             f"rotation={0 if PORTRAIT else 90}, and was given {canvas.width}x{canvas.height}")
        canvas.antialias = ANTIALIAS
        canvas.pen = HALL
        canvas.clear()
        started = True

    draw_show(canvas, elapsed % CYCLE)
