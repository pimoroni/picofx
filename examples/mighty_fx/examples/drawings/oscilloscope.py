import math
from picovector import color, image, rect, shape

"""
Draw an oscilloscope tracing waves that slowly fade on the screen. A scrolling sine grows into a
square wave a harmonic at a time and melts back, and then the scope switches to XY mode for a
turning Lissajous figure.

The afterglow is the previous frame dimmed a little each time, so the beam is only ever drawn
where it is now.

Drawing: Oscilloscope
Defaults: Rotation = 90
Section: Retro displays
"""

# The demonstration
SINE_SECONDS = 6                                    # The sine alone, scrolling
GROW_SECONDS = 8                                    # Growing into a square wave, a harmonic at a time
MELT_SECONDS = 4                                    # And melting back to the sine
XY_SECONDS = 8                                      # A Lissajous figure in XY mode
HARMONICS = 8                                       # Odd harmonics in the square wave at its squarest
CYCLES = 2.5                                        # Cycles of the sine across a face DIVISIONS wide
SCROLL = 1.5                                        # How fast the wave scrolls, in radians a second
WAVE_HEIGHT = 0.3                                   # How far the wave reaches either side of the middle, of the face's height
FIGURE = (2, 3)                                     # The Lissajous figure's frequencies across and down
FIGURE_SIZE = 0.42                                  # How far it reaches from the middle, of the face's narrower side
TURN = 0.4                                          # How fast it turns, in radians a second

# The screens drive the panel at 12 bit, 16 levels a channel in steps of 17, so the colours sit on those levels
HALO = color.rgb(68, 255, 221)                      # The beam's cyan glow
CORE = color.rgb(204, 255, 255)                     # And its near-white core
GLASS = color.rgb(34, 102, 136)                     # The tube's face where nothing has lit it
GRID = color.rgb(17, 68, 102)                       # The graticule's lines, a shade darker
FRAME = color.rgb(17, 17, 17)                       # The dark edge the face sits in
CASE = color.rgb(221, 204, 187)                     # The case round the tube

# Sizes, in panel pixels
DIVISIONS = (10, 8)                                 # Graticule squares across and down on a panel on its side, swapped upright
DIVISION = 28                                       # Panel pixels a square
TICKS = 4                                           # Ticks a square along the middle lines, evenly spaced where they divide into DIVISION
CORE_W = 1.5                                        # Panel pixels across the beam's core
HALO_W = 5                                          # And across the glow round it
HALO_ALPHA = 70                                     # How strong that glow is, of 255
FRAME_W = 5                                         # Panel pixels across the frame
CORNER = 6                                          # How far the frame's corners are rounded
DIM = 70                                            # How much of the old trace dims away over DIM_MS, of 255, more giving a shorter afterglow
DIM_MS = 125                                        # The time DIM is taken over, an eighth of a second
DIM_LEAST = 17                                      # The faintest dim laid at once, one of the screens' 16 levels
SEGMENTS = 80                                       # Segments a sweep is drawn in, the figure taking twice as many
ANTIALIAS = image.X4                                # A beam is all edge, so it wants smoothing

# The canvas is the size of the screen, as the effects file turns it
WIDTH, HEIGHT = canvas.width, canvas.height
canvas.antialias = ANTIALIAS

# The sizes above are for a 2.8 inch panel, and scale with a canvas pixel doubled
SCALE = min(WIDTH, HEIGHT) / 240
DIVISION = round(DIVISION * SCALE)
CORE_W, HALO_W, CORNER = CORE_W * SCALE, HALO_W * SCALE, CORNER * SCALE
FRAME_W = max(1, round(FRAME_W * SCALE))
TICK_REACH = max(1, round(2 * SCALE))               # How far a tick reaches either side of its middle line

# As many of the DIVISIONS as fit inside the frame, an even number each way so the middle lines stay on the
# graticule. At a DIVISION of 28, 10 by 8 on a 2.8" panel on its side, 8 by 10 upright, and 8 by 8 on a 1.54"
WANTED = DIVISIONS if WIDTH >= HEIGHT else (DIVISIONS[1], DIVISIONS[0])
ACROSS, DOWN = (min(wanted, (room - FRAME_W * 2) // DIVISION // 2 * 2) for wanted, room in zip(WANTED, (WIDTH, HEIGHT)))

# The face is a pixel wider and taller than its squares, so the graticule's far lines land on it
FACE_W, FACE_H = ACROSS * DIVISION + 1, DOWN * DIVISION + 1
LEFT, TOP = (WIDTH - FACE_W) // 2, (HEIGHT - FACE_H) // 2
MIDDLE_X, MIDDLE_Y = ACROSS * DIVISION / 2, DOWN * DIVISION / 2
SPAN_X, SPAN_Y = ACROSS * DIVISION, DOWN * DIVISION
FIGURE_REACH = min(SPAN_X, SPAN_Y) * FIGURE_SIZE    # So the figure fits the face whichever way it stands

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
dim_pen = GLASS.with_alpha(0)       # The glass laid over the old trace, set for each frame from the time since the last
undimmed = 0                        # The ms the trace has gone without the glass laid over it


def graticule():
    """Draw the graticule over the face, a line every division and ticks along the middle lines."""
    tube.pen = GRID
    for across in range(ACROSS + 1):
        tube.vspan(across * DIVISION, 0, FACE_H)
    for down in range(DOWN + 1):
        tube.hspan(0, down * DIVISION, FACE_W)
    for tick in range(ACROSS * TICKS):
        tube.vspan(tick * DIVISION // TICKS, int(MIDDLE_Y) - TICK_REACH, TICK_REACH * 2 + 1)
    for tick in range(DOWN * TICKS):
        tube.hspan(int(MIDDLE_X) - TICK_REACH, tick * DIVISION // TICKS, TICK_REACH * 2 + 1)


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
        angle = 2 * math.pi * CYCLES * ACROSS / DIVISIONS[0] * i / SEGMENTS + phase
        total = sum(weight * math.sin(harmonic * angle) for harmonic, weight in weights)
        points.append((SPAN_X * i / SEGMENTS, MIDDLE_Y - SPAN_Y * WAVE_HEIGHT * total))
    return points


def lissajous(seconds):
    """Calculate the points of a Lissajous figure in XY mode, its across component's phase turning it about its upright axis."""
    across, down = FIGURE
    phase = seconds * TURN
    steps = SEGMENTS * 2
    return [(MIDDLE_X + FIGURE_REACH * math.sin(across * 2 * math.pi * i / steps + phase),
             MIDDLE_Y - FIGURE_REACH * math.sin(down * 2 * math.pi * i / steps))
            for i in range(steps + 1)]


WAVE_SECONDS = SINE_SECONDS + GROW_SECONDS + MELT_SECONDS
CYCLE_MS = round((WAVE_SECONDS + XY_SECONDS) * 1000)


def draw_scope(seconds):
    """Draw one frame this far into the demonstration, the old trace dimmed, the graticule, and the beam where it is now."""
    tube.pen = dim_pen
    tube.rectangle(whole_face)
    graticule()

    # Whether the demonstration is on the wave or the figure, cutting between them as a real scope switches to XY
    if seconds < WAVE_SECONDS:
        trace(wave(seconds))
    else:
        trace(lissajous(seconds - WAVE_SECONDS))


def draw():
    """Draw the scope for the time the drawing has played, the afterglow fading by time whatever the frame rate."""
    global dim_pen, undimmed
    undimmed += ticks_delta
    alpha = round(255 * (1 - (1 - DIM / 255) ** (undimmed / DIM_MS)))
    # Whether the glass owed takes a channel down a level. A fainter one leaves the trace short of
    # black, so at a fast frame rate it is saved up for a later frame
    if alpha < DIM_LEAST:
        alpha = 0
    else:
        undimmed = 0
    dim_pen = GLASS.with_alpha(alpha)
    # Kept in whole milliseconds until the fraction is wanted, as a float of hours of running loses it
    draw_scope(ticks % CYCLE_MS / 1000)
