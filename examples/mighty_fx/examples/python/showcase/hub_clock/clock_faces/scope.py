import math
import random
from array import array
from picovector import color, image, rect, shape

"""
A scope's digit for the hub clock, the beam tracing it on an upright screen as a figure from a pair of
signals, one driving it across and one driving it down. Each signal is a sum of waves, so the digit is a
smooth curve the beam follows without lifting, and the signals carry a little noise, so no digit is
quite true. When the digit changes, the beam traces the new figure as the old one fades on the phosphor.
A colon is a pair of beam dots beside the digit. showcase/oscilloscope.py draws the beam the same way.
"""

CHANGE_STEPS = 4                    # Frames through a change, the old figure fading over them
PACED = False                       # Kept to its own frames when the clock is overclocked, as each takes long to draw
COLON_BLINKS = False                # The colon's dots are held lit
WRITE_BUDGET = 16                   # Writes a change may take across the panels, so a carry's fades are cut short
TRACE_SHARE = 0.35                  # How much of a change the beam takes to trace the new figure
NOISE = 0.06                        # How far the signals stray, of the digit's size

# Each digit's signals, a wave to a row. A row is its frequency, in turns a trace, then the cosine and
# sine amplitudes across and the cosine and sine amplitudes down, of the digit's box. Frequency 0 is where
# the figure sits. Most digits have cosines alone, so the beam runs out along the stroke and back over it.
# The 0 is a circle, and the 8 the 1:2 Lissajous figure
DIGITS = {
    "0": ((0, 0.500, 0.000, 0.500, 0.000), (1, 0.000, 0.500, -0.500, 0.000)),
    "1": ((0, 0.510, 0.000, 0.394, 0.000), (1, -0.076, 0.000, -0.412, 0.000), (2, -0.062, 0.000, 0.118, 0.000),
          (3, -0.046, 0.000, 0.024, 0.000), (4, -0.028, 0.000, 0.054, 0.000)),
    "2": ((0, 0.509, 0.000, 0.565, 0.000), (1, 0.028, 0.000, -0.546, 0.000), (2, -0.040, 0.000, -0.052, 0.000),
          (3, -0.406, 0.000, 0.078, 0.000), (4, 0.030, 0.000, 0.032, 0.000), (5, -0.034, 0.000, 0.040, 0.000),
          (6, 0.004, 0.000, 0.028, 0.000), (9, -0.030, 0.000, 0.008, 0.000)),
    "3": ((0, 0.617, 0.000, 0.511, 0.000), (1, 0.008, 0.000, -0.500, 0.000), (2, -0.272, 0.000, -0.010, 0.000),
          (3, 0.026, 0.000, 0.012, 0.000), (4, -0.236, 0.000, -0.008, 0.000), (5, -0.026, 0.000, 0.090, 0.000),
          (6, 0.050, 0.000, 0.010, 0.000), (8, -0.040, 0.000, -0.002, 0.000)),
    "4": ((0, 0.541, 0.000, 0.506, 0.000), (1, 0.152, 0.000, -0.110, 0.000), (2, 0.228, 0.000, 0.228, 0.000),
          (3, -0.236, 0.000, 0.226, 0.000), (4, 0.058, 0.000, 0.058, 0.000), (9, -0.026, 0.000, 0.026, 0.000)),
    "5": ((0, 0.499, 0.000, 0.467, 0.000), (1, -0.082, 0.000, -0.496, 0.000), (2, -0.048, 0.000, 0.020, 0.000),
          (3, 0.394, 0.000, -0.028, 0.000), (4, 0.014, 0.000, -0.052, 0.000), (5, 0.030, 0.000, 0.100, 0.000),
          (6, 0.014, 0.000, 0.018, 0.000), (8, 0.002, 0.000, -0.028, 0.000)),
    "6": ((0, 0.439, 0.000, 0.571, 0.000), (1, -0.120, 0.000, -0.364, 0.000), (2, -0.130, 0.000, 0.002, 0.000),
          (3, 0.370, 0.000, -0.080, 0.000), (4, 0.022, 0.000, -0.170, 0.000), (5, 0.018, 0.000, 0.036, 0.000),
          (6, 0.018, 0.000, 0.014, 0.000), (7, 0.014, 0.000, 0.032, 0.000), (9, 0.022, 0.000, -0.002, 0.000),
          (10, 0.006, 0.000, -0.028, 0.000)),
    "7": ((0, 0.595, 0.000, 0.272, 0.000), (1, -0.108, 0.000, -0.424, 0.000), (2, -0.336, 0.000, 0.182, 0.000),
          (3, -0.054, 0.000, -0.024, 0.000), (5, 0.010, 0.000, -0.024, 0.000), (6, -0.032, 0.000, 0.018, 0.000)),
    "8": ((0, 0.500, 0.000, 0.500, 0.000), (1, 0.000, 0.000, -0.500, 0.000), (2, 0.000, 0.380, 0.000, 0.000)),
    "9": ((0, 0.561, 0.000, 0.429, 0.000), (1, 0.120, 0.000, 0.364, 0.000), (2, 0.130, 0.000, -0.002, 0.000),
          (3, -0.370, 0.000, 0.080, 0.000), (4, -0.022, 0.000, 0.170, 0.000), (5, -0.018, 0.000, -0.036, 0.000),
          (6, -0.018, 0.000, -0.014, 0.000), (7, -0.014, 0.000, -0.032, 0.000), (9, -0.022, 0.000, 0.002, 0.000),
          (10, -0.006, 0.000, 0.028, 0.000)),
}
SAMPLES = 120                       # Points along a trace

# The screen, upright in a dark case as a vector console's is. The screens drive the panel at 12 bit, 16
# levels a channel in steps of 17, so the colours sit on those levels
CASE = color.rgb(17, 17, 17)
RIM = color.rgb(51, 51, 51)         # The screen's edge in the case
GLASS = color.rgb(0, 17, 0)         # The tube's face where nothing has lit it
SCREEN_INSET = 12                   # Panel pixels of case round the screen
SCREEN_CORNER = 20
HALO = color.rgb(68, 255, 119)      # The beam's green glow
CORE = color.rgb(204, 255, 204)     # And its near-white core
CORE_W = 2.5                        # Panel pixels across the beam's core
HALO_W = 8                          # And across the glow round it
HALO_ALPHA = 100                    # How strong that glow is, of 255
DIGIT_W = 120                       # The digit's box, in panel pixels
DIGIT_H = 200
DIGIT_SHIFT = -10                   # The digit sits left of the screen's middle, the colon taking the right
COLON_X = 82                        # The colon's dots, right of the screen's middle
COLON_Y = 40                        # And above and below it
ANTIALIAS = image.X4                # A beam is all edge, so it wants smoothing

# Made by prepare() for the panel's size, and kept
background = None
waves = []                          # Each frequency's cosine and sine at every point along a trace
beam_area = rect(0, 0, 0, 0)        # Everywhere the beam reaches, the digit with its noise and the colon
drawn_frames = set()                # The frames already holding the screen, by id
figures = {}                        # Each digit's figure once calculated, its noise the same each time
left = top = middle_x = middle_y = 0


def prepare(width, height):
    """Draw the screen in its case and calculate the waves every trace is made of, for a panel this size."""
    global background, left, top, middle_x, middle_y
    middle_x, middle_y = width / 2, height / 2
    left, top = middle_x + DIGIT_SHIFT - DIGIT_W / 2, middle_y - DIGIT_H / 2
    # A figure strays a little past its box, as a series cut short overshoots and the noise moves it
    # A figure strays a little past its box, as a series cut short overshoots and the noise moves it. Kept
    # to the screen, so the case round it is never cleared
    reach = round(DIGIT_H * 0.08 + DIGIT_H * NOISE + HALO_W)
    inner = SCREEN_INSET + SCREEN_CORNER // 2
    beam_area.x, beam_area.y = max(inner, round(left) - reach), max(inner, round(top) - reach)
    beam_area.w = min(width - inner, round(middle_x + COLON_X + HALO_W) + 2) - beam_area.x
    beam_area.h = min(height - inner, round(top) + DIGIT_H + reach) - beam_area.y

    background = image(width, height)
    background.antialias = ANTIALIAS
    background.pen = CASE
    background.clear()
    screen = rect(SCREEN_INSET, SCREEN_INSET, width - SCREEN_INSET * 2, height - SCREEN_INSET * 2)
    background.pen = RIM
    background.shape(shape.rounded_rectangle(rect(screen.x - 2, screen.y - 2, screen.w + 4, screen.h + 4),
                                             SCREEN_CORNER + 2, SCREEN_CORNER + 2, SCREEN_CORNER + 2, SCREEN_CORNER + 2))
    background.pen = GLASS
    background.shape(shape.rounded_rectangle(screen, SCREEN_CORNER, SCREEN_CORNER, SCREEN_CORNER, SCREEN_CORNER))

    highest = max(row[0] for rows in DIGITS.values() for row in rows)
    for frequency in range(highest + 1):
        angles = [2 * math.pi * frequency * sample / SAMPLES for sample in range(SAMPLES)]
        waves.append(([math.cos(angle) for angle in angles], [math.sin(angle) for angle in angles]))


def figure(digit):
    """
    Find the points of a digit's figure as flat x, y pairs, calculated the first time it is asked for.

    A digit of cosines alone comes back over the same line, so only the way out is calculated, and the
    beam's glow is not drawn twice over it. A digit with sines is a loop, calculated the whole way round.
    """
    if digit in figures:
        return figures[digit]
    # Seeded by the digit, so the same noise comes out whichever run draws it
    random.seed(ord(digit))
    rows = DIGITS[digit]
    count = SAMPLES if any(row[2] or row[4] for row in rows) else SAMPLES // 2 + 1
    points = array("f", [0.0] * (count * 2))
    for frequency, x_cos, x_sin, y_cos, y_sin in rows:
        # Each wave's amplitude wanders a little, the way a signal from an analogue source does
        wander = 1 + (random.random() - 0.5) * NOISE * 4 if frequency else 1
        cosines, sines = waves[frequency]
        x_cos, x_sin = x_cos * wander * DIGIT_W, x_sin * wander * DIGIT_W
        y_cos, y_sin = y_cos * wander * DIGIT_H, y_sin * wander * DIGIT_H
        for sample in range(count):
            points[sample * 2] += x_cos * cosines[sample] + x_sin * sines[sample]
            points[sample * 2 + 1] += y_cos * cosines[sample] + y_sin * sines[sample]
    # And the whole figure drifts a little with the source's level
    drift_x = left + (random.random() - 0.5) * NOISE * DIGIT_W
    drift_y = top + (random.random() - 0.5) * NOISE * DIGIT_H
    for sample in range(count):
        points[sample * 2] += drift_x
        points[sample * 2 + 1] += drift_y
    figures[digit] = points
    return points


def trace(frame, points, share, strength):
    """
    Draw the beam along a share of a figure, from 0 to 1, its glow first and then its core, at a strength.

    A segment at a time, as a figure stroked whole cancels itself wherever its outline overlaps.
    """
    count = len(points) // 2
    # A loop closes on its first point
    ends = list(range(count)) + ([0] if count == SAMPLES else [])
    ends = ends[:max(2, round(len(ends) * share))]
    for width, pen, alpha in ((HALO_W, HALO, HALO_ALPHA), (CORE_W, CORE, 255)):
        frame.pen = pen.with_alpha(round(alpha * strength))
        for start, end in zip(ends, ends[1:]):
            frame.shape(shape.line(points[start * 2], points[start * 2 + 1], points[end * 2], points[end * 2 + 1], width))


def dot(frame, x, y):
    """Draw the beam held still on a point, its glow round it."""
    frame.pen = HALO.with_alpha(HALO_ALPHA)
    frame.shape(shape.circle(x, y, HALO_W / 2 + 1))
    frame.pen = CORE
    frame.shape(shape.circle(x, y, CORE_W + 0.5))


def draw(frame, digit, colon_lit, previous=None, progress=1.0):
    """
    Draw a whole panel into the frame, the digit's figure on the screen.

    colon_lit is None on a panel without a colon. On the way from a previous digit, by progress from 0 to
    1, the beam traces the new figure over the first TRACE_SHARE of it while the old one fades throughout.

    A frame takes the whole screen the first time, and after that only where the beam reaches is cleared.
    """
    if id(frame) in drawn_frames:
        frame.blit(background, beam_area, beam_area)
    else:
        frame.raw[:] = background.raw
        drawn_frames.add(id(frame))
    frame.antialias = ANTIALIAS
    if previous in DIGITS and progress < 1:
        trace(frame, figure(previous), 1, 1 - progress)
        if digit in DIGITS:
            trace(frame, figure(digit), min(1, progress / TRACE_SHARE), 1)
    elif digit in DIGITS:
        trace(frame, figure(digit), 1, 1)
    if colon_lit:
        for offset in (-COLON_Y, COLON_Y):
            dot(frame, middle_x + COLON_X, middle_y + offset)
