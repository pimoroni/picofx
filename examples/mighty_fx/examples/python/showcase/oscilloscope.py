import math
import time
from mighty_fx import MightyFX, SPCE
from sensor import ANALOG
from timing import Pacer
from screens import Screen280
from picovector import color, image, rect, shape

"""
Draw an oscilloscope, a beam tracing waves across its graticule and leaving a fading afterglow on
the phosphor. A scrolling sine grows into a square wave a harmonic at a time and melts back, and
then the scope switches to XY mode for a turning Lissajous figure. SENSOR = True traces the
voltage on the sensor connector instead.

The afterglow is the previous frame dimmed a little each time, so the beam is only ever drawn
where it is now.

Press "Boot" to exit the program.

Section: Mechanical and glowing displays
"""

# Constants for drawing
SENSOR = False                                      # Whether to trace the sensor connector's voltage live
FRAME_RATE = 8                                      # Frames a second, which the board holds with the beam drawn

# The demonstration
SINE_SECONDS = 6                                    # The sine alone, scrolling
GROW_SECONDS = 8                                    # Growing into a square wave, a harmonic at a time
MELT_SECONDS = 4                                    # And melting back to the sine
XY_SECONDS = 8                                      # A Lissajous figure in XY mode
HARMONICS = 8                                       # Odd harmonics in the square wave at its squarest
CYCLES = 2.5                                        # Cycles of the sine across the face
SCROLL = 1.5                                        # How fast the wave scrolls, in radians a second
WAVE_HEIGHT = 0.3                                   # How far the wave reaches either side of the middle, of the face's height
FIGURE = (2, 3)                                     # The Lissajous figure's frequencies across and down
FIGURE_SIZE = 0.42                                  # How far it reaches from the middle, of the face's height
TURN = 0.4                                          # How fast it turns, in radians a second

# The screens drive the panel at 12 bit, 16 levels a channel in steps of 17, so the colours sit on those levels
HALO = color.rgb(68, 255, 221)                      # The beam's cyan glow
CORE = color.rgb(204, 255, 255)                     # And its near-white core
GLASS = color.rgb(34, 102, 136)                     # The tube's face where nothing has lit it
GRID = color.rgb(17, 68, 102)                       # The graticule's lines, a shade darker
FRAME = color.rgb(17, 17, 17)                       # The dark edge the face sits in
CASE = color.rgb(221, 204, 187)                     # The case round the tube

# Sizes, in panel pixels
DIVISIONS = (10, 8)                                 # Graticule squares across and down
DIVISION = 28                                       # Panel pixels a square
TICKS = 4                                           # Ticks a square along the middle lines, which DIVISION must divide into
CORE_W = 1.5                                        # Panel pixels across the beam's core
HALO_W = 5                                          # And across the glow round it
HALO_ALPHA = 70                                     # How strong that glow is, of 255
FRAME_W = 5                                         # Panel pixels across the frame
CORNER = 6                                          # How far the frame's corners are rounded
DIM = 70                                            # How much of the old trace each frame dims away, of 255, more giving a shorter afterglow
SEGMENTS = 80                                       # Segments a sweep is drawn in, the figure taking twice as many
ANTIALIAS = image.X4                                # A beam is all edge, so it wants smoothing

# The sensor's sweep
SAMPLE_US = 50                                      # Microseconds waited between readings, on top of a reading's own time
VOLTS_PER_DIVISION = 0.5
TRIGGER = 1.65                                      # The voltage a sweep starts on, rising through it, and the face's middle line
TRIGGER_WAIT_MS = 50                                # How long a sweep waits for it before starting anyway
MAX_VOLTAGE = 3.3                                   # The voltage a full reading stands for
FULL_READING = 65535                                # And that full reading

# Create a MightyFX object with SP/CE A set up for a screen, and with SENSOR the sensor connector read as a voltage
mighty = MightyFX(spce_a=SPCE.SCREEN, sensor=ANALOG if SENSOR else None)
screen = Screen280(mighty.spce_a)

# Drawn landscape and turned a quarter onto the panel at each update
canvas = screen.canvas(screen.height, screen.width)
WIDTH, HEIGHT = canvas.width, canvas.height
canvas.antialias = ANTIALIAS

# The face is a pixel wider and taller than its squares, so the graticule's far lines land on it
FACE_W, FACE_H = DIVISIONS[0] * DIVISION + 1, DIVISIONS[1] * DIVISION + 1
LEFT, TOP = (WIDTH - FACE_W) // 2, (HEIGHT - FACE_H) // 2
MIDDLE_X, MIDDLE_Y = DIVISIONS[0] * DIVISION / 2, DIVISIONS[1] * DIVISION / 2
SPAN_X, SPAN_Y = DIVISIONS[0] * DIVISION, DIVISIONS[1] * DIVISION

# The case round the tube is drawn once, as only the face changes from then on
canvas.pen = CASE
canvas.clear()
canvas.pen = FRAME
canvas.shape(shape.rounded_rectangle(rect(LEFT - FRAME_W, TOP - FRAME_W, FACE_W + FRAME_W * 2, FACE_H + FRAME_W * 2),
                                     CORNER, CORNER, CORNER, CORNER))

# A view of the canvas through the face, sharing its pixels. Everything on the face is drawn through it in
# the face's own coordinates, so a beam's glow at the edge cannot spill onto the frame, where nothing dims it
tube = canvas.window(rect(LEFT, TOP, FACE_W, FACE_H))
whole_face = rect(0, 0, FACE_W, FACE_H)
tube.antialias = ANTIALIAS
tube.pen = GLASS
tube.rectangle(whole_face)

HALO_PEN = HALO.with_alpha(HALO_ALPHA)
DIM_PEN = GLASS.with_alpha(DIM)


def graticule():
    """Draw the graticule over the face, a line every division and ticks along the middle lines."""
    tube.pen = GRID
    for across in range(DIVISIONS[0] + 1):
        tube.vspan(across * DIVISION, 0, FACE_H)
    for down in range(DIVISIONS[1] + 1):
        tube.hspan(0, down * DIVISION, FACE_W)
    for tick in range(DIVISIONS[0] * TICKS):
        tube.vspan(tick * DIVISION // TICKS, int(MIDDLE_Y) - 2, 5)
    for tick in range(DIVISIONS[1] * TICKS):
        tube.hspan(int(MIDDLE_X) - 2, tick * DIVISION // TICKS, 5)


def trace(points):
    """Draw the beam through these points on the face, its glow first and then its core."""
    for width, pen in ((HALO_W, HALO_PEN), (CORE_W, CORE)):
        tube.pen = pen
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            tube.shape(shape.line(x0, y0, x1, y1, width))


def harmonics_at(seconds):
    """Calculate how many odd harmonics the wave carries this far into the demonstration, with a fractional part."""
    if seconds < SINE_SECONDS:
        return 1
    seconds -= SINE_SECONDS
    if seconds < GROW_SECONDS:
        return 1 + (HARMONICS - 1) * seconds / GROW_SECONDS
    return HARMONICS - (HARMONICS - 1) * (seconds - GROW_SECONDS) / MELT_SECONDS


def wave(seconds):
    """
    Calculate the points of the wave across the face, this far into the demonstration.

    It is a sum of odd harmonics, which a square wave is made of. Each harmonic fades in or out as the
    count passes from one whole number to the next, so the sine grows into a square wave smoothly.
    """
    count = harmonics_at(seconds)
    phase = seconds * SCROLL
    weights = []
    for place, harmonic in enumerate(range(1, 2 * HARMONICS, 2)):
        weight = min(1, max(0, count - place)) / harmonic
        if weight:
            weights.append((harmonic, weight))

    points = []
    for i in range(SEGMENTS + 1):
        angle = 2 * math.pi * CYCLES * i / SEGMENTS + phase
        total = sum(weight * math.sin(harmonic * angle) for harmonic, weight in weights)
        points.append((SPAN_X * i / SEGMENTS, MIDDLE_Y - SPAN_Y * WAVE_HEIGHT * total))
    return points


def lissajous(seconds):
    """Calculate the points of a Lissajous figure in XY mode, its across component's phase turning it about its upright axis."""
    across, down = FIGURE
    phase = seconds * TURN
    steps = SEGMENTS * 2
    return [(MIDDLE_X + SPAN_Y * FIGURE_SIZE * math.sin(across * 2 * math.pi * i / steps + phase),
             MIDDLE_Y - SPAN_Y * FIGURE_SIZE * math.sin(down * 2 * math.pi * i / steps))
            for i in range(steps + 1)]


# The sensor's readings, filled in place, so nothing is allocated while a sweep is being timed
readings = [0] * (SEGMENTS + 1)


def sensed():
    """
    Read a sweep of the sensor connector's voltage, starting on a rising edge where there is one, and
    calculate its points across the face.

    The ADC is read directly, quicker than read_voltage(), so the readings sit close together.
    """
    adc = mighty.sensor.pin
    level = round(TRIGGER / MAX_VOLTAGE * FULL_READING)
    waited = time.ticks_add(time.ticks_ms(), TRIGGER_WAIT_MS)
    last = adc.read_u16()
    while time.ticks_diff(waited, time.ticks_ms()) > 0:
        now = adc.read_u16()
        if last < level <= now:
            break
        last = now

    for i in range(SEGMENTS + 1):
        readings[i] = adc.read_u16()
        time.sleep_us(SAMPLE_US)
    return [(SPAN_X * i / SEGMENTS,
             MIDDLE_Y - (reading * MAX_VOLTAGE / FULL_READING - TRIGGER) / VOLTS_PER_DIVISION * DIVISION)
            for i, reading in enumerate(readings)]


WAVE_SECONDS = SINE_SECONDS + GROW_SECONDS + MELT_SECONDS
CYCLE_MS = round((WAVE_SECONDS + XY_SECONDS) * 1000)


def draw(seconds):
    """Draw one frame this far into the demonstration, the old trace dimmed, the graticule, and the beam where it is now."""
    tube.pen = DIM_PEN
    tube.rectangle(whole_face)
    graticule()

    if SENSOR:
        trace(sensed())
    # Whether the demonstration is on the wave or the figure, cutting between them as a real scope switches to XY
    elif seconds < WAVE_SECONDS:
        trace(wave(seconds))
    else:
        trace(lissajous(seconds - WAVE_SECONDS))


pacer = Pacer(fps=FRAME_RATE)       # The scope's clock, holding each frame to the rate

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Kept in whole milliseconds until the fraction is wanted, as a float of hours of running loses it
        draw(pacer.elapsed % CYCLE_MS / 1000)
        screen.update(canvas, rotation=90)
        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
