from picovector import color, font, image, shape

"""
Draw a lixie display that lights one engraved acrylic sheet at a time to show each digit.

The engraving lets the light out, so a lit sheet reads as its digit in fine bright lines while the
nine unlit ones stay a faint tracery. A sheet further back looks a size smaller, so the edges nest.

The nine unlit sheets are drawn once into every frame's background, and the lit one straight onto it.

The glow goes on the frame, which is opaque, and not on any sheet.

Drawing: Acrylic lixie
Section: Retro displays
"""

# Constants for drawing
LIXIE_FONT = "/rom/fonts/AlumniSansPinstripe.af"
ANTIALIAS = image.X4        # A vector face needs it, and a line a pixel wide is all edge
BACKGROUND = color.black    # Behind the stack, which is a dark box

# The stack, front sheet first, and the digit each sheet carries in that order
ORDER = (1, 2, 3, 4, 5, 6, 7, 8, 9, 0)
DEPTH_SCALE = 0.984         # How much smaller a sheet one place further back appears
SHEET_INSET = (7, 8)        # The front sheet's edges in from the panel's, across and down, the rest scaled from it
CORNER = 14                 # How far a sheet's corners are rounded
EDGE = 2                    # The width of a cut edge, which is the brightest thing on a lit sheet
DIGIT_FILL = 0.612          # How much of the front sheet's height its digit is drawn
LIT = 255                   # The sheet with its LED on
GHOST = 20                  # And one without, the engraving picking up a little of its neighbour's light
REF = 200                   # A size to measure the face at, its lettering scaling with it from there

# The LEDs under the sheets, one colour for each pass through the digits
COLOURS = (color.rgb(80, 170, 255),     # Ice blue, which is the colour these are usually seen in
           color.rgb(255, 90, 170),     # Pink
           color.rgb(255, 150, 60),     # Amber, for the tube it stands in for
           color.rgb(140, 255, 190))    # Green
SPILL = 150                 # The light entering along the bottom edge, out of the base
FOOT = 34                   # How far up it reaches, falling away over that distance

# What makes it a light rather than a drawing of one
GLOW_FROM = 80              # The brightness a pixel glows from, well above an unlit sheet's
GLOW = 240                  # How much of the halo is added back, 255 being all of it
GLOW_SPREAD = 10            # How far it reaches, in panel pixels
CURVE = 70                  # How far the picture falls away at the edges

COUNT_MS = 1000             # A digit a second, this being the seconds place of a clock
CHANGE_MS = 220             # One digit going out as the next comes up, so both are seen together

# The canvas is the size of the screen, as the effects file turns it
WIDTH, HEIGHT = canvas.width, canvas.height
canvas.antialias = ANTIALIAS
SHEET_W, SHEET_H = WIDTH - SHEET_INSET[0] * 2, HEIGHT - SHEET_INSET[1] * 2
DIGIT_H = round(SHEET_H * DIGIT_FILL)   # The front sheet's digit, in panel pixels

SHEETS = len(ORDER)
# Each digit's place in the stack, front first, and the scale a sheet at that place is drawn at
DEPTH_OF = {digit: depth for depth, digit in enumerate(ORDER)}
SCALE_AT = tuple(DEPTH_SCALE ** depth for depth in range(SHEETS))

# The nine unlit sheets, drawn once. It doubles as the scratch the measurement below uses
stack = image(WIDTH, HEIGHT)
stack.antialias = ANTIALIAS
# The face goes on both, as a sheet is drawn onto the stack while unlit and onto the frame once lit
stack.font = canvas.font = font.load(LIXIE_FONT)
BLANK = bytes(len(stack.raw))           # A cleared stack's bytes, copied in to wipe it before a measurement


def lettering_rows(letters, size, at):
    """
    Measure the first and last rows these characters fill.

    A face's metrics are not where its lettering lands.
    """
    stack.raw[:] = BLANK
    stack.pen = color.white
    stack.text(letters, at, at, size)

    filled = bytes(stack.raw)
    # The first and last bytes holding any lettering, turned into rows by the stride
    return ((len(filled) - len(filled.lstrip(b"\0"))) // stack.stride,
            (len(filled.rstrip(b"\0")) - 1) // stack.stride)


TOP, BOTTOM = lettering_rows("8", REF, 0)
SIZE = REF * DIGIT_H / (BOTTOM - TOP + 1)
LETTERING_DOWN = TOP / REF  # How far below the y it is drawn at a digit's lettering starts, per unit of size
ADVANCE = {digit: stack.measure_text(str(digit), font_size=SIZE)[0] for digit in ORDER}

# A sheet's cut edges as one shape per depth, made once so the animation does not judder
EDGES = []
for depth in range(SHEETS):
    wide, tall = SHEET_W * SCALE_AT[depth], SHEET_H * SCALE_AT[depth]
    EDGES.append(shape.rounded_rectangle((WIDTH - wide) / 2, (HEIGHT - tall) / 2, wide, tall,
                                         CORNER * SCALE_AT[depth]).stroke(EDGE))


def sheet(into, digit, colour):
    """Draw one sheet's cut edges and digit onto this image, at the size its depth appears."""
    depth = DEPTH_OF[digit]
    scale = SCALE_AT[depth]
    into.pen = colour
    into.shape(EDGES[depth])
    into.text(str(digit), (WIDTH - ADVANCE[digit] * scale) / 2,
              (HEIGHT - DIGIT_H * scale) / 2 - LETTERING_DOWN * SIZE * scale, SIZE * scale)


def build(light):
    """Draw the unlit stack and the LEDs' light from the base, the background every frame starts from."""
    stack.pen = BACKGROUND
    stack.clear()
    for row in range(FOOT):
        stack.pen = light.with_alpha(round(SPILL * (1 - row / FOOT) ** 2))
        stack.hspan(0, HEIGHT - 1 - row, WIDTH)

    unlit = light.with_alpha(GHOST)
    # Back to front, so a nearer sheet's lines cross over those behind it
    for depth in range(SHEETS - 1, -1, -1):
        sheet(stack, ORDER[depth], unlit)


def draw_stack(showing, light):
    """
    Draw one frame, the stack, the sheet or two with light in them, and the glow.

    The digit coming on and the one going out arrive in showing, each with its brightness.
    """
    # The background is cleared under first, as its blended pixels fall a little short of opaque
    # and the previous frame would show through them
    canvas.pen = BACKGROUND
    canvas.clear()
    canvas.blit(stack, 0, 0)
    for digit, level in showing:
        if level:
            sheet(canvas, digit, light.with_alpha(level))

    canvas.bloom(GLOW_FROM, GLOW, GLOW_SPREAD)
    canvas.vignette(CURVE)


turn = 0
light = COLOURS[turn]
build(light)

shown = None
pass_start = 0              # The ticks the pass through the digits started at


def draw():
    """Draw the stack for the time the drawing has played, only where a sheet's brightness changes."""
    global turn, light, shown, pass_start
    # Which digit the count is on, and how far into it
    count, into = divmod(ticks - pass_start, COUNT_MS)
    if count >= SHEETS:
        # A pass is done, so the LEDs take the next colour and the stack is drawn again
        turn = (turn + 1) % len(COLOURS)
        light = COLOURS[turn]
        build(light)
        pass_start += SHEETS * COUNT_MS
        return

    # A sheet's LED switches quickly, and for that moment the sheet losing it still has some light
    up = min(1.0, into / CHANGE_MS)
    showing = ((ORDER[count], round(LIT * up)), (ORDER[count - 1], round(LIT * (1 - up))))
    if showing != shown:
        draw_stack(showing, light)
        shown = showing
