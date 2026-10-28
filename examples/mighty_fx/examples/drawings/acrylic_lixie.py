from picovector import color, font, image, shape

"""
Drawing: Acrylic lixie
A lixie, ten engraved acrylic sheets stacked front to back, only the one being shown lit.
Section: Mechanical and glowing displays
"""

# Entry: screenA: graphics file=acrylic_lixie.py fps=100   (a 2.8" screen)

# Constants for drawing
LIXIE_FONT = "/rom/fonts/AlumniSansPinstripe.af"
ANTIALIAS = image.X4
BACKGROUND = color.black

ORDER = (1, 2, 3, 4, 5, 6, 7, 8, 9, 0)
DEPTH_SCALE = 0.984
SHEET_W = 226
SHEET_H = 304
CORNER = 14
EDGE = 2
DIGIT_H = 186
LIT = 255
GHOST = 20
REF = 200

COLOURS = (color.rgb(80, 170, 255),
           color.rgb(255, 90, 170),
           color.rgb(255, 150, 60),
           color.rgb(140, 255, 190))
SPILL = 150
FOOT = 34

GLOW_FROM = 80
GLOW = 240
GLOW_SPREAD = 10
CURVE = 70

COUNT_MS = 1000
CHANGE_MS = 220

# The canvas this drawing expects, a 2.8" screen at rotation 0, stated as the stack is
# built before the first call
WIDTH, HEIGHT = 240, 320

SHEETS = len(ORDER)
DEPTH_OF = {digit: depth for depth, digit in enumerate(ORDER)}
SCALE_AT = tuple(DEPTH_SCALE ** depth for depth in range(SHEETS))

lixie_font = font.load(LIXIE_FONT)
stack = image(WIDTH, HEIGHT)
stack.antialias = ANTIALIAS
stack.font = lixie_font
BLANK = bytes(len(stack.raw))


def lettering_rows(letters, size, at):
    """Measure the first and last rows these characters fill."""
    stack.raw[:] = BLANK
    stack.pen = color.white
    stack.text(letters, at, at, size)
    filled = bytes(stack.raw)
    return ((len(filled) - len(filled.lstrip(b"\0"))) // stack.stride,
            (len(filled.rstrip(b"\0")) - 1) // stack.stride)


TOP, BOTTOM = lettering_rows("8", REF, 0)
SIZE = REF * DIGIT_H / (BOTTOM - TOP + 1)
LETTERING_DOWN = TOP / REF
ADVANCE = {digit: stack.measure_text(str(digit), font_size=SIZE)[0] for digit in ORDER}

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
    for depth in range(SHEETS - 1, -1, -1):
        sheet(stack, ORDER[depth], unlit)


def frame(canvas, showing, light):
    """Draw one frame, the stack, the sheet or two with light in them, and the glow."""
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
pass_from = 0           # When the pass through the digits began, in elapsed ms


def draw(canvas, elapsed):
    global turn, light, shown, pass_from
    now = elapsed * 1000
    if shown is None:
        if (canvas.width, canvas.height) != (WIDTH, HEIGHT):
            raise ValueError(f'this drawing is laid out for {WIDTH}x{HEIGHT}, a 2.8" screen at '
                             f"rotation 0, and was given {canvas.width}x{canvas.height}")
        canvas.antialias = ANTIALIAS
        canvas.font = lixie_font

    count, into = divmod(int(now - pass_from), COUNT_MS)
    if count >= SHEETS:
        # A pass is done, so the LEDs take the next colour and the stack is drawn again
        turn = (turn + 1) % len(COLOURS)
        light = COLOURS[turn]
        build(light)
        pass_from = now
        count, into = 0, 0
        shown = ()

    up = min(1.0, into / CHANGE_MS)
    showing = ((ORDER[count], round(LIT * up)), (ORDER[count - 1], round(LIT * (1 - up))))
    if showing != shown:
        frame(canvas, showing, light)
        shown = showing
