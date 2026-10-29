from picovector import color, font, image, shape

"""
A lixie digit for the hub clock, ten engraved acrylic sheets stacked front to back with an LED under
each, only the sheet carrying the digit lit. A colon is two LEDs set in the case beside the stack,
always lit. showcase/acrylic_lixie.py is the fuller version.
"""

LIXIE_FONT = "/rom/fonts/AlumniSansPinstripe.af"
ANTIALIAS = image.X4                # A vector face needs it, and a line a pixel wide is all edge
BACKGROUND = color.black            # Behind the stack, which is a dark box
COLON_BLINKS = True                 # Whether the colon blinks with the seconds, or stays lit
CHANGE_STEPS = 2                    # Frames between one digit and the next, the old sheet dimming as the new one lights
# The LEDs' colour. (255, 90, 170) is pink, (255, 150, 60) amber and (140, 255, 190) green
LED = color.rgb(80, 170, 255)       # Ice blue, the colour these are usually seen in

# The stack, front sheet first, and the digit each sheet carries in that order
ORDER = (1, 2, 3, 4, 5, 6, 7, 8, 9, 0)
DEPTH_SCALE = 0.984                 # How much smaller a sheet one place further back appears
SHEET_SIDE = 24                     # Panel pixels either side of the front sheet, room for a colon on the right
SHEET_END = 7                       # And above and below it
CORNER = 14                         # How far a sheet's corners are rounded
EDGE = 2                            # The width of a cut edge, which is the brightest thing on a lit sheet
DIGIT_SHARE = 0.58                  # How much of the panel's height the front sheet's digit takes
LIT = 255                           # The sheet with its LED on
GHOST = 20                          # And one without, the engraving picking up a little of its neighbour's light
REF = 200                           # A size to measure the face at, its lettering scaling with it from there
SPILL = 150                         # The light entering along the bottom edge, out of the base
FOOT = 34                           # How far up it reaches, falling away over that distance
COLON_R = 3.5                       # A colon LED's radius, in panel pixels
COLON_OFF = 40                      # How much a colon LED shows while it is off, of 255

# What makes it a light and not a drawing of one
GLOW_FROM = 80                      # The brightness a pixel glows from, well above an unlit sheet's
GLOW = 240                          # How much of the halo is added back, 255 being all of it
GLOW_SPREAD = 10                    # How far it reaches, in panel pixels
CURVE = 70                          # How far the picture falls away at the edges

SHEETS = len(ORDER)
DEPTH_OF = {digit: depth for depth, digit in enumerate(ORDER)}
SCALE_AT = tuple(DEPTH_SCALE ** depth for depth in range(SHEETS))

# Made by prepare() for the panel's size, and kept
face = None
stack = None                        # The unlit sheets and the light from the base, which every frame starts from
edges = []                          # A sheet's cut edges, one shape a depth
colon = []                          # The colon's two LEDs
width = height = 0
size = digit_h = lettering_down = 0
advance = {}


def lettering_rows(letters, at):
    """
    Measure the first and last rows these characters fill, drawn at REF on the stack as a scratch.

    A face's metrics are not where its lettering lands.
    """
    stack.raw[:] = bytes(len(stack.raw))
    stack.pen = color.white
    stack.text(letters, at, at, REF)

    filled = bytes(stack.raw)
    # The first and last bytes holding any lettering, turned into rows by the stride
    return ((len(filled) - len(filled.lstrip(b"\0"))) // stack.stride,
            (len(filled.rstrip(b"\0")) - 1) // stack.stride)


def sheet(into, digit, colour):
    """Draw one sheet's cut edges and digit onto this image, at the size its depth appears."""
    depth = DEPTH_OF[digit]
    scale = SCALE_AT[depth]
    into.pen = colour
    into.shape(edges[depth])
    into.text(str(digit), (width - advance[digit] * scale) / 2,
              (height - digit_h * scale) / 2 - lettering_down * size * scale, size * scale)


def prepare(panel_width, panel_height):
    """Build the sheets, sized to fill a panel this size, and draw the unlit stack every frame starts from."""
    global face, stack, width, height, size, digit_h, lettering_down
    width, height = panel_width, panel_height
    face = font.load(LIXIE_FONT)
    stack = image(width, height)
    stack.antialias = ANTIALIAS
    stack.font = face

    digit_h = round(height * DIGIT_SHARE)
    top, bottom = lettering_rows("8", 0)
    size = REF * digit_h / (bottom - top + 1)
    lettering_down = top / REF          # How far below the y it is drawn at a digit's lettering starts, per unit of size
    for digit in ORDER:
        advance[digit] = stack.measure_text(str(digit), font_size=size)[0]

    sheet_w, sheet_h = width - SHEET_SIDE * 2, height - SHEET_END * 2
    for depth in range(SHEETS):
        wide, tall = sheet_w * SCALE_AT[depth], sheet_h * SCALE_AT[depth]
        edges.append(shape.rounded_rectangle((width - wide) / 2, (height - tall) / 2, wide, tall,
                                             CORNER * SCALE_AT[depth]).stroke(EDGE))
    for y in (height * 0.42, height * 0.58):
        colon.append(shape.circle(width - SHEET_SIDE / 2, y, COLON_R))

    stack.pen = BACKGROUND
    stack.clear()
    for row in range(FOOT):
        stack.pen = LED.with_alpha(round(SPILL * (1 - row / FOOT) ** 2))
        stack.hspan(0, height - 1 - row, width)
    unlit = LED.with_alpha(GHOST)
    # Back to front, so a nearer sheet's lines cross over those behind it
    for depth in range(SHEETS - 1, -1, -1):
        sheet(stack, ORDER[depth], unlit)

    stack = settled(stack)


def settled(drawn):
    """
    Make the background every frame is copied from, opaque and with the edges' fall-off already in it.

    Its blended pixels fall a little short of opaque, so it is laid over black once here, and a frame can
    then take its bytes whole. The fall-off is at the edges, where nothing a frame adds reaches.
    """
    opaque = image(width, height)
    opaque.pen = BACKGROUND
    opaque.clear()
    opaque.blit(drawn, 0, 0)
    opaque.vignette(CURVE)
    return opaque


def draw(frame, digit, colon_lit, previous=None, progress=1.0):
    """
    Draw a whole panel into the frame, the stack with the digit's sheet lit, and the glow.

    colon_lit is None on a panel without a colon, and otherwise says whether it is lit. On the way from
    a previous digit its sheet keeps the light the new one has yet to take, by progress from 0 to 1.
    """
    frame.antialias = ANTIALIAS
    frame.font = face
    frame.raw[:] = stack.raw
    if previous is not None and previous != " ":
        sheet(frame, int(previous), LED.with_alpha(round(LIT * (1 - progress))))
    if digit != " ":
        sheet(frame, int(digit), LED.with_alpha(round(LIT * progress)))

    if colon_lit is not None:
        frame.pen = LED if colon_lit else LED.with_alpha(COLON_OFF)
        for lamp in colon:
            frame.shape(lamp)

    frame.bloom(GLOW_FROM, GLOW, GLOW_SPREAD)
