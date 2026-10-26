import math
import random
import sys
import time
from collections import OrderedDict
from mighty_fx import MightyFX, SPCE
from timing import Pacer
from screens import SCREEN_TYPES, ScreenPair
from picovector import color, image, shape, vec2

"""
Draw a creature's eyes looking about, an eye on each SP/CE port's screen, darting from spot to spot,
holding there a while and blinking now and then. CREATURE chooses the cat, owl, goat, alien, robot or
zombie, each with its own eyes and its own way of looking about.

Both panels show the one frame. Eyes facing forward show it as drawn, a goat's eyes either side of its
head mirror the second panel, and the alien's eyes slanting outwards mirror the first, so its outer
corners are at the outside of the pair with SP/CE A on the left. One screen shows a single eye.

TURNED mounts one of a pair on their sides turned round from the other, so the narrow bezels meet.

Nothing is drawn while the eyes hold still, so the board idles between darts.

Press "Boot" for the next creature, and hold it to exit the program.
"""

# Constants
CREATURE = "cat"            # The creature to start on, a name from CREATURES
# One panel of a pair on their sides is mounted turned round, so their narrowest bezels meet. 0 for SP/CE A,
# 1 for B, or None. Upright panels meet along their long edges, which are equally narrow, so neither is turned
TURNED = 0
QUIT_MS = 1500              # Held at least this long, the button ends the example
FRAME_RATE = 50             # Passes a second at most, each drawing only where the eyes have moved
SQUARE = 240                # The square an eye is sized for, a wider panel widening the eye by its "widen"
LID_STEPS = 32              # Points along a lid's edge
STREAKS = 28                # Streaks across an iris
SHADOW_DROP = 9             # How far the upper lid's shadow falls on the eye
BLINK_MS = (70, 40, 120)    # How long a blink takes to close, stays closed and takes to open
GLINT = color.rgb(255, 255, 255, 221)       # The highlights, which stay put while the iris moves under them
SHEEN = color.rgb(255, 255, 255, 51)        # A wet gleam along the top of a dark eye

# What a creature takes unless its entry says otherwise. Sizes are in pixels for the SQUARE, and the
# front corner is on the canvas's left. The screens drive the panel at 12 bit, 16 levels a channel in
# steps of 17, so the colours sit on those levels
DEFAULTS = {
    "layout": "front",          # "front" for one frame as drawn, "side" mirroring the second panel and "face" the first
    "draw": None,               # A drawing of its own in DRAWINGS, None for an eye drawn from the sizes here
    "surround": color.black,    # Round the eye, and the lids
    "shadow": None,             # The upper lid's shadow on the eye, None for none
    "front": 100,               # How far the eye reaches to its front corner
    "back": 100,                # And to its back corner
    "top": 56,                  # How far the upper lid arches above the middle
    "bottom": 42,               # And the lower lid below it
    "top_power": 0.75,          # How full the upper lid's curve is, below 1 rounder
    "bottom_power": 0.95,       # And the lower lid's
    "tilt": 0,                  # Degrees the eye is turned, negative raising the back corner
    "widen": 0,                 # How much of a wider panel's extra width the eye takes
    "iris_radius": 46,          # 0 for an eye with no iris or pupil showing
    "pupil_shape": "round",     # "round", a "slit" upright or a "bar" across
    "pupil_radius": 17,         # A round pupil's size
    "glint": (-22, -22, 9),     # The highlight's place from the eye's middle and its radius
    "sheen": False,             # Whether a gleam runs along the top of the eye
    "reach": (46, 20),          # How far the iris moves across and down at the edge of a look
    "whole": (0, 0),            # How far the whole eye moves, for a creature that turns its head to look
    "lid_follow": 0.3,          # How far the upper lid lifts and lowers with a look, as a share of its height
    "blink_from": "above",      # Which lid closes, "above" or "below"
    "hold": (0.8, 2.5),         # Seconds the eyes rest on one spot, at random between these
    "blinks": (3, 6),           # Seconds between blinks, the same way
    "dart": (0.05, 0.05),       # Seconds a dart takes, and more for each half of the width it crosses
    "home": 0.3,                # The chance a dart goes back to the middle
}

# Each creature, what differs from DEFAULTS, in the order Boot steps through them. An OrderedDict, as
# MicroPython's dict keeps no order. A colour with an alpha is laid over what is under it
CREATURES = OrderedDict({
    # A black cat, almost all iris round a slit pupil
    "cat": {
        "white": color.rgb(136, 153, 51), "iris_edge": color.rgb(102, 136, 34), "iris": color.rgb(170, 187, 51),
        "streaks": color.rgb(221, 221, 119, 90), "inner_ring": color.rgb(204, 153, 34, 110),
        "pupil": color.black,
        "front": 92, "back": 92, "top": 58, "bottom": 54, "top_power": 0.6, "bottom_power": 0.7,
        "iris_radius": 64, "pupil_shape": "slit", "reach": (30, 14), "glint": (-24, -26, 9), "widen": 0.3,
    },
    # An owl's eyes barely move in its head, so the whole eye moves slowly as the head turns
    "owl": {
        "surround": color.rgb(119, 102, 68), "shadow": color.rgb(34, 17, 0, 90),
        "white": color.rgb(221, 153, 17), "iris_edge": color.rgb(204, 136, 17), "iris": color.rgb(255, 187, 34),
        "streaks": color.rgb(255, 221, 119, 80), "inner_ring": color.rgb(238, 153, 17, 80),
        "pupil": color.black,
        "front": 86, "back": 86, "top": 82, "bottom": 82, "top_power": 0.5, "bottom_power": 0.5,
        "iris_radius": 78, "pupil_radius": 40, "glint": (-26, -32, 11),
        "reach": (6, 4), "whole": (24, 14), "lid_follow": 0,
        "hold": (1, 3), "blinks": (2.5, 5), "dart": (0.15, 0.1),
    },
    # A goat's eyes are either side of its head, its bar pupil level whichever way it looks
    "goat": {
        "layout": "side", "surround": color.rgb(153, 136, 102), "shadow": color.rgb(34, 17, 0, 90),
        "white": color.rgb(221, 204, 187), "iris_edge": color.rgb(153, 102, 17), "iris": color.rgb(221, 153, 34),
        "streaks": color.rgb(255, 204, 102, 90), "inner_ring": color.rgb(153, 102, 17, 90),
        "pupil": color.black,
        "front": 104, "back": 92, "top": 74, "bottom": 66, "top_power": 0.55, "bottom_power": 0.6,
        "iris_radius": 78, "pupil_shape": "bar", "reach": (22, 8), "glint": (-34, -42, 11),
        "hold": (1.2, 3.5), "dart": (0.08, 0.06), "home": 0.2,
    },
    # A glossy dark almond with no pupil that slants up to its outer corner. Its front is the inner corner
    "alien": {
        "layout": "face", "surround": color.rgb(153, 153, 153), "shadow": color.rgb(34, 51, 51, 80),
        "white": color.rgb(17, 17, 17),
        "front": 66, "back": 100, "top": 58, "bottom": 44, "top_power": 0.7, "bottom_power": 0.9,
        "tilt": -18, "widen": 0.5, "iris_radius": 0, "glint": (-6, -22, 10), "sheen": True,
        "whole": (8, 10), "lid_follow": 0.15, "hold": (1, 3), "blinks": (5, 9), "dart": (0.06, 0.05),
    },
    # A glowing block that narrows as it looks aside and squashes flat to blink
    "robot": {
        "draw": "block", "surround": color.rgb(0, 0, 17), "glow": color.rgb(0, 221, 204),
        "size": (110, 130), "corner": 30, "reach": (50, 30),
        "hold": (0.6, 2), "dart": (0.08, 0.06), "home": 0.4,
    },
    # A human eye gone grey and milky, drifting slowly from one look to the next
    "zombie": {
        "surround": color.rgb(153, 153, 119), "shadow": color.rgb(17, 34, 0, 100),
        "white": color.rgb(221, 204, 170), "iris_edge": color.rgb(153, 170, 153), "iris": color.rgb(204, 204, 204),
        "streaks": color.rgb(238, 238, 238, 80), "inner_ring": color.rgb(170, 170, 153, 80),
        "pupil": color.rgb(119, 119, 119),
        "pupil_radius": 15, "glint": (-22, -22, 7), "widen": 0.6,
        "hold": (1.5, 3.5), "blinks": (4, 8), "dart": (0.25, 0.2), "home": 0.2,
    },
})

# Which panels each layout mirrors, the first and the second
MIRRORS = {"front": (False, False), "side": (False, True), "face": (True, False)}

# Is CREATURE one of them? Checked before the pair takes its few seconds to set up
if CREATURE not in CREATURES:
    raise ValueError(f"'{CREATURE}' is not one of the creatures! Set CREATURE to {', '.join(CREATURES)}")

# Which screen is on both ports, "2.8" or "1.54", and how far they are turned, 0, 90, 180 or 270,
# or what the effects file passes in args, the size first. A pair needs both panels the same size
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ROTATION = 90 if not sys.argv[2:] else int(sys.argv[2])
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with both SP/CE ports set up for screens
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# A screen refuses to be created where no panel answers, so one panel shows a single eye. The TURNED
# panel takes half a turn more where the panels are on their sides
sideways = ROTATION % 180 == 90
screens = []
numbers = []                # Which port each screen is on, 0 for SP/CE A and 1 for B
for number, port in enumerate((mighty.spce_a, mighty.spce_b)):
    try:
        screens.append(ScreenType(port, rotation=(ROTATION + 180 * (sideways and number == TURNED)) % 360))
        numbers.append(number)
    except ValueError as e:
        print(e)

if not screens:
    mighty.shutdown()
    raise RuntimeError("No panels answered! Plug a screen into SP/CE A, and a second into SP/CE B for a pair of eyes")

# A pair shows both eyes on one frame. Working out how takes a few seconds
pair = ScreenPair(*screens) if len(screens) == 2 else None

# One canvas in fast SRAM that both panels show, sized as they are turned
canvas = screens[0].canvas()
canvas.antialias = image.X4


# Each layout's rotations and mirrors, a screen each. The driver mirrors along a panel's own width, up and
# down on a panel on its side, so a mirrored one there takes half a turn more to flip left to right as seen
placements = {}
for layout, flips in MIRRORS.items():
    placements[layout] = (tuple((screen.rotation + 180 * (sideways and flips[number])) % 360
                                for number, screen in zip(numbers, screens)),
                          tuple(flips[number] for number in numbers))


def between(span):
    """Pick a number at random between the two in span."""
    return random.uniform(span[0], span[1])


def lid_edge(cx, cy, creature, height, power, sign):
    """List the points along a lid's edge from the front corner to the back, arching up for a sign of -1."""
    front, back = creature["front"], creature["back"]
    points = []
    for step in range(LID_STEPS + 1):
        x = -front + (front + back) * step / LID_STEPS
        across = x / front if x < 0 else x / back
        points.append((cx + x, cy + sign * height * max(0.0, 1 - across * across) ** power))
    return points


def outline(points, cx, cy, turn):
    """Make a shape of the points, turned about (cx, cy) by a turn given as its cosine and sine."""
    cos_t, sin_t = turn
    return shape.custom([vec2(cx + (x - cx) * cos_t - (y - cy) * sin_t, cy + (x - cx) * sin_t + (y - cy) * cos_t)
                         for x, y in points])


def draw_iris(creature, x, y):
    """Draw the iris with its edge, streaks and inner ring, and the pupil in it."""
    radius = creature["iris_radius"]
    canvas.pen = creature["iris_edge"]
    canvas.shape(shape.circle(x, y, radius))
    canvas.pen = creature["iris"]
    canvas.shape(shape.circle(x, y, radius * 0.88))
    canvas.pen = creature["streaks"]
    for streak in range(STREAKS):
        angle = streak * 2 * math.pi / STREAKS
        across, down = math.cos(angle) * radius, math.sin(angle) * radius
        canvas.shape(shape.line(x + across * 0.4, y + down * 0.4, x + across * 0.82, y + down * 0.82, 1.5))
    canvas.pen = creature["inner_ring"]
    canvas.shape(shape.circle(x, y, radius * 0.52).stroke(3))

    canvas.pen = creature["pupil"]
    if creature["pupil_shape"] == "slit":
        canvas.shape(shape.ellipse(x, y, radius * 0.13, radius * 0.8))
    elif creature["pupil_shape"] == "bar":
        bar_w, bar_h = radius * 1.25, radius * 0.34
        canvas.shape(shape.rounded_rectangle(x - bar_w / 2, y - bar_h / 2, bar_w, bar_h, bar_h / 2))
    else:
        canvas.shape(shape.circle(x, y, creature["pupil_radius"]))


def draw_eye(creature, gaze, openness):
    """Draw an eye from the creature's sizes, looking that way and that far open."""
    look_x, look_y = gaze
    cx = canvas.width / 2 + look_x * creature["whole"][0]
    cy = canvas.height / 2 + look_y * creature["whole"][1]
    tilt = math.radians(creature["tilt"])
    turn = (math.cos(tilt), math.sin(tilt))

    canvas.pen = creature["surround"]
    canvas.clear()

    # The eyeball, larger than any opening as the lids cover the rest, turned by the tilt as the lids are
    ball_x = max(creature["front"], creature["back"]) + 4
    ball_y = max(creature["top"] * (1 + creature["lid_follow"]), creature["bottom"]) + 6
    canvas.pen = creature["white"]
    canvas.shape(outline([(cx + math.cos(step * math.pi / 24) * ball_x, cy + math.sin(step * math.pi / 24) * ball_y)
                          for step in range(48)], cx, cy, turn))

    if creature["iris_radius"]:
        draw_iris(creature, cx + look_x * creature["reach"][0], cy + look_y * creature["reach"][1])
    if creature["sheen"]:
        outer = lid_edge(cx, cy, creature, creature["top"] * 0.78, creature["top_power"], -1)
        inner = lid_edge(cx, cy, creature, creature["top"] * 0.6, creature["top_power"], -1)
        canvas.pen = SHEEN
        canvas.shape(outline(outer[6:-10] + inner[6:-10][::-1], cx, cy, turn))

    glint_x, glint_y, glint_r = creature["glint"]
    canvas.pen = GLINT
    canvas.shape(shape.circle(cx + glint_x, cy + glint_y, glint_r))
    canvas.pen = GLINT.with_alpha(119)
    canvas.shape(shape.circle(cx - glint_x * 0.6, cy - glint_y * 0.5, glint_r * 0.45))

    # A blink slides one lid's arch across the eye until it passes the other. A look lifts or lowers
    # the lids' middles while their corners stay put
    upper_height = creature["top"] * (1 - look_y * creature["lid_follow"])
    lower_height = creature["bottom"] * (1 + look_y * 0.1)
    closing = (1 - openness) * (upper_height + lower_height + 2)    # Two pixels over, so no seam shows when shut
    upper_y = lower_y = cy
    if creature["blink_from"] == "below":
        lower_y -= closing
    else:
        upper_y += closing
    upper = lid_edge(cx, upper_y, creature, upper_height, creature["top_power"], -1)
    lower = lid_edge(cx, lower_y, creature, lower_height, creature["bottom_power"], 1)

    # Each lid runs level from its corners out past the panel's edges, far enough to cover them once
    # turned, and a pixel past the other lid's so no seam shows between them
    front_x, back_x = upper[0][0], upper[-1][0]
    far = canvas.width + canvas.height
    upper_meet = max(upper_y, lower_y) + 1
    upper_lid = ([(cx - far, cy - far), (cx + far, cy - far), (cx + far, upper_meet), (back_x, upper_meet)]
                 + upper[::-1] + [(front_x, upper_meet), (cx - far, upper_meet)])
    lower_meet = min(upper_y, lower_y) - 1
    lower_lid = ([(cx - far, cy + far), (cx + far, cy + far), (cx + far, lower_meet), (back_x, lower_meet)]
                 + lower[::-1] + [(front_x, lower_meet), (cx - far, lower_meet)])

    if creature["shadow"] is not None:
        canvas.pen = creature["shadow"]
        canvas.shape(outline([(x, y + SHADOW_DROP) for x, y in upper_lid], cx, cy, turn))

    # The closing lid goes on top
    canvas.pen = creature["surround"]
    lids = (upper_lid, lower_lid) if creature["blink_from"] == "below" else (lower_lid, upper_lid)
    for lid in lids:
        canvas.shape(outline(lid, cx, cy, turn))


def draw_block(creature, gaze, openness):
    """Draw a glowing block, narrower looking aside, shorter looking up or down and squashed flat to blink."""
    look_x, look_y = gaze
    cx = canvas.width / 2 + look_x * creature["reach"][0]
    cy = canvas.height / 2 + look_y * creature["reach"][1]
    w = creature["size"][0] * (1 - 0.15 * abs(look_x))
    h = max(10, creature["size"][1] * (1 - 0.1 * abs(look_y)) * openness)
    corner = min(creature["corner"], h / 2)

    canvas.pen = creature["surround"]
    canvas.clear()
    for grow, alpha in ((24, 20), (14, 40), (6, 80)):
        canvas.pen = creature["glow"].with_alpha(alpha)
        canvas.shape(shape.rounded_rectangle(cx - w / 2 - grow, cy - h / 2 - grow, w + grow * 2, h + grow * 2,
                                             corner + grow))
    canvas.pen = creature["glow"]
    canvas.shape(shape.rounded_rectangle(cx - w / 2, cy - h / 2, w, h, corner))


# The drawings an entry can name with "draw"
DRAWINGS = {"block": draw_block}


class Eyes:
    """Where a creature's eyes look and how open they are, darting, holding and blinking as time passes."""

    def __init__(self, creature, now):
        """Construct the eyes looking ahead and wide open, the first dart and blink coming sooner than the rest."""
        self.creature = creature
        self.start = self.target = (0.0, 0.0)
        self.dart_at = now
        self.dart_ms = 0
        self.next_dart = now + between(creature["hold"]) * 500
        self.blink_at = None
        self.next_blink = now + between(creature["blinks"]) * 500

    def looking(self, now):
        """Calculate where the eyes look, easing out of each dart as eyes do."""
        if self.dart_ms == 0:
            return self.target
        progress = min(1.0, (now - self.dart_at) / self.dart_ms)
        eased = 1 - (1 - progress) ** 3
        return (self.start[0] + (self.target[0] - self.start[0]) * eased,
                self.start[1] + (self.target[1] - self.start[1]) * eased)

    def openness(self, now):
        """Calculate how open the eyes are, from 1 open to 0 shut."""
        if self.blink_at is None:
            return 1.0
        since = now - self.blink_at
        closing, closed, opening = BLINK_MS
        if since < closing:
            return 1 - since / closing
        if since < closing + closed:
            return 0.0
        return min(1.0, (since - closing - closed) / opening)

    def at(self, now):
        """Move on to now, starting a dart or a blink where one is due, and return the look and the openness."""
        creature = self.creature
        if now >= self.next_dart:
            current = self.looking(now)
            if random.random() < creature["home"]:
                target = (random.uniform(-0.15, 0.15), random.uniform(-0.1, 0.1))
            elif random.random() < 0.25:
                # A small correction near where the eyes already are
                target = (current[0] + random.uniform(-0.12, 0.12), current[1] + random.uniform(-0.08, 0.08))
            else:
                target = (random.uniform(-1, 1), random.uniform(-0.8, 0.8))
            # Kept to the edge of a look, which a run of corrections could walk past
            target = (max(-1.0, min(1.0, target[0])), max(-0.8, min(0.8, target[1])))
            distance = math.sqrt((target[0] - current[0]) ** 2 + (target[1] - current[1]) ** 2)
            self.start, self.target = current, target
            self.dart_at = now
            self.dart_ms = (creature["dart"][0] + creature["dart"][1] * distance) * 1000
            self.next_dart = now + self.dart_ms + between(creature["hold"]) * 1000

            # Does a long dart bring a blink with it, where none is running?
            blinking = self.blink_at is not None and now - self.blink_at < sum(BLINK_MS)
            if distance > 0.8 and random.random() < 0.3 and not blinking:
                self.next_blink = now

        if now >= self.next_blink:
            self.blink_at = now
            self.next_blink = now + between(creature["blinks"]) * 1000

        return self.looking(now), self.openness(now)


def choose(name, now):
    """Build a creature from DEFAULTS and its entry, widened to suit the panel, and the Eyes that move it."""
    creature = dict(DEFAULTS)
    creature.update(CREATURES[name])
    extra = max(0, canvas.width - SQUARE) * creature["widen"] / 2
    creature["front"] += extra
    creature["back"] += extra
    creature["reach"] = (creature["reach"][0] + extra / 2, creature["reach"][1])
    return creature, Eyes(creature, now)


names = list(CREATURES)
index = names.index(CREATURE)
creature, eyes = choose(names[index], 0)
pacer = Pacer(fps=FRAME_RATE)       # The eyes' clock, holding each pass to the rate
now = 0                             # Milliseconds the eyes have been moving, added up from each pass
print(f"{len(screens)} panel(s): press for the next creature, hold {QUIT_MS}ms to finish")

shown = None
pressed_since = None
leaving = False

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not leaving:
        now += pacer.delta
        gaze, openness = eyes.at(now)

        # Is this any different from what the panels show?
        moment = (index, round(gaze[0], 3), round(gaze[1], 3), round(openness, 2))
        if moment != shown:
            DRAWINGS.get(creature["draw"], draw_eye)(creature, gaze, openness)
            rotations, mirrors = placements[creature["layout"]]
            if pair is not None:
                pair.update(canvas, rotation=rotations, mirror=mirrors)
            else:
                screens[0].update(canvas, rotation=rotations[0], mirror=mirrors[0])
            shown = moment

        # Judged on release, a press being impossible to tell from a hold until it ends
        if mighty.boot_pressed():
            if pressed_since is None:
                pressed_since = time.ticks_ms()

        elif pressed_since is not None:
            held = time.ticks_diff(time.ticks_ms(), pressed_since)
            pressed_since = None
            if held >= QUIT_MS:
                leaving = True
            else:
                index = (index + 1) % len(names)
                creature, eyes = choose(names[index], now)
                print(f"> {names[index]}")

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
