from picovector import color, image, rect, shape, vec2

"""
A seven-segment LED digit for the hub clock, its unlit segments showing faintly through a coloured
filter, with a colon on the right where the clock asks for one. showcase/segment_clock.py is the
fuller version.
"""

# The colour a lit segment glows, which the filter and the unlit segments take theirs from.
# (255, 153, 0) is an amber display and (51, 255, 68) a green one
LED = (255, 34, 17)

# A segment is set out in a digit one unit wide between its outer bars' centres, and this many tall
DIGIT_TALL = 1.8
STROKE = 0.2                        # How thick a bar is
SEGMENT_GAP = 0.035                 # Between one bar and the next, along the line they meet on
SLANT = 0.1                         # How far the top of a digit leans over its foot, per unit of height
MARGIN = 12                         # Panel pixels around the window, and between it and the digit
CORNER = 6                          # How far the window's corners are rounded

# Which bars each character lights, named a to g as a display's datasheet names them
#
#    aaaaaaa
#   f       b
#   f       b
#    ggggggg
#   e       c
#   e       c
#    ddddddd
LIGHTS = {
    " ": (),
    "0": ("a", "b", "c", "d", "e", "f"),
    "1": ("b", "c"),
    "2": ("a", "b", "g", "e", "d"),
    "3": ("a", "b", "g", "c", "d"),
    "4": ("f", "g", "b", "c"),
    "5": ("a", "f", "g", "c", "d"),
    "6": ("a", "f", "g", "e", "d", "c"),
    "7": ("a", "b", "c"),
    "8": ("a", "b", "c", "d", "e", "f", "g"),
    "9": ("a", "b", "c", "d", "f", "g"),
}


def dimmed(fraction):
    """
    Calculate the LED's colour at a fraction of its brightness.

    The screens drive the panel at 12 bit, 16 levels a channel in steps of 17, so each channel is
    rounded to a level.
    """
    return color.rgb(*(round(channel * fraction / 17) * 17 for channel in LED))


LIT = color.rgb(*LED)               # A segment carrying current
GHOST = dimmed(0.267)               # One that is not, seen through the filter
FILTER = dimmed(0.067)              # The filter itself, filling the window
KEYLINE = dimmed(0.267)             # The window's edge, which finds it against the black
CASE = color.black
ANTIALIAS = image.X4                # Every bar is slanted, so its edges want smoothing

HALF = STROKE / 2
MIDDLE = DIGIT_TALL / 2


def bar(x0, y0, x1, y1):
    """Outline a bar between two points on a row or a column, pointed at both ends so neighbours meet on a mitre."""
    if y0 == y1:
        x0, x1 = x0 + SEGMENT_GAP, x1 - SEGMENT_GAP
        return ((x0, y0), (x0 + HALF, y0 - HALF), (x1 - HALF, y0 - HALF),
                (x1, y0), (x1 - HALF, y0 + HALF), (x0 + HALF, y0 + HALF))

    y0, y1 = y0 + SEGMENT_GAP, y1 - SEGMENT_GAP
    return ((x0, y0), (x0 + HALF, y0 + HALF), (x0 + HALF, y1 - HALF),
            (x0, y1), (x0 - HALF, y1 - HALF), (x0 - HALF, y0 + HALF))


OUTLINES = {
    "a": bar(0, 0, 1, 0),
    "b": bar(1, 0, 1, MIDDLE),
    "c": bar(1, MIDDLE, 1, DIGIT_TALL),
    "d": bar(0, DIGIT_TALL, 1, DIGIT_TALL),
    "e": bar(0, MIDDLE, 0, DIGIT_TALL),
    "f": bar(0, 0, 0, MIDDLE),
    "g": bar(0, MIDDLE, 1, MIDDLE),
}

# Made by prepare() for the panel's size, and kept, a shape built per frame being an allocation
segments = {}
colon = []                          # The colon's two dots
ground = None                       # The window with every segment unlit, which every frame starts from


def prepare(width, height):
    """Build the digit's segments and the ground under them, sized to fill a panel this size."""
    global ground

    # A digit's outer edges reach half a bar past the unit square, its top leans the slant further over,
    # and room for a colon is kept on the right of every digit, so they all sit alike
    digit_w = 1 + STROKE + SLANT * DIGIT_TALL + STROKE * 2
    digit_h = DIGIT_TALL + STROKE
    scale = min((width - MARGIN * 4) / digit_w, (height - MARGIN * 4) / digit_h)
    left = (width - digit_w * scale) / 2
    top = (height - digit_h * scale) / 2

    for name, outline in OUTLINES.items():
        segments[name] = shape.custom([vec2(left + (HALF + x + SLANT * (DIGIT_TALL - y)) * scale,
                                            top + (HALF + y) * scale) for x, y in outline])
    # The colon's dots sit out by the window's edge, nearer the next panel than their own digit, and lean
    # with the digit at the height of the gaps between its bars
    radius = STROKE * 0.6 * scale
    for y in (MIDDLE * 0.5, MIDDLE * 1.5):
        colon.append(shape.circle(width - MARGIN * 2 - radius + SLANT * (MIDDLE - y) * scale,
                                  top + (HALF + y) * scale, radius))

    ground = image(width, height)
    ground.antialias = ANTIALIAS
    ground.pen = CASE
    ground.clear()
    window = rect(MARGIN, MARGIN, width - MARGIN * 2, height - MARGIN * 2)
    ground.pen = KEYLINE
    ground.shape(shape.rounded_rectangle(rect(window.x - 1, window.y - 1, window.w + 2, window.h + 2),
                                         CORNER, CORNER, CORNER, CORNER))
    ground.pen = FILTER
    ground.shape(shape.rounded_rectangle(window, CORNER, CORNER, CORNER, CORNER))
    ground.pen = GHOST
    for segment in segments.values():
        ground.shape(segment)


def draw(frame, digit, colon_lit):
    """
    Draw a whole panel into the frame, the ground with the segments the digit lights.

    colon_lit is None on a panel without a colon, and otherwise says whether it is lit.
    """
    # Cleared under first. The ground's blended pixels fall a little short of opaque, so without the
    # clear the frame's last digit shows through them
    frame.antialias = ANTIALIAS
    frame.pen = CASE
    frame.clear()
    frame.blit(ground, 0, 0)

    frame.pen = LIT
    for name in LIGHTS[digit]:
        frame.shape(segments[name])

    if colon_lit is not None:
        frame.pen = LIT if colon_lit else GHOST
        for dot in colon:
            frame.shape(dot)
