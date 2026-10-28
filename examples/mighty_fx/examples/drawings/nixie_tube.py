from picovector import color, font, image, rect, shape

"""
Drawing: Nixie tube
A nixie tube, ten cathodes bent into digits and stacked in a glass cylinder, counting.
Section: Mechanical and glowing displays
"""

# Entry: screenA: graphics file=nixie_tube.py fps=100   (a 2.8" screen)

# Constants for drawing
TUBE_FONT = "/rom/fonts/AlumniSansPinstripe.af"
ANTIALIAS = image.X4
NEON = color.rgb(255, 102, 34)
CORE = color.rgb(255, 170, 102)
BACKGROUND = color.black

CATHODE_FRONT = (51, 43, 36)
CATHODE_BACK = (22, 20, 18)

ORDER = (6, 7, 5, 8, 4, 3, 9, 2, 0, 1)
DEPTH_SCALE = 0.978
DEPTH_Y = 1
DIGIT_H = 185
LIT = 255
REF = 200

TUBE_W = 130
TUBE_TOP = 6
TUBE_FOOT = 292
FOOT_CORNER = 8
TINT = color.rgb(34, 17, 0)
RIM = color.rgb(255, 221, 170)
SHADE = 18
SHADE_DARK = 170
PINS = 11
PIN = color.rgb(119, 102, 85)
BOARD = color.rgb(17, 17, 17)
ROD = color.rgb(68, 60, 52)
MICA = color.rgb(102, 94, 85)

ENVELOPE = 60
BASE_GLOW = 110
BASE_ROWS = 34
SHEATH = 2
SHEATH_LEVEL = 0.28

GLOW_FROM = 100
GLOW = 220
GLOW_SPREAD = 10
MESH = 4
MESH_DARK = 30
CURVE = 80

COUNT_MS = 1000
CHANGE_MS = 200

# The canvas this drawing expects, a 2.8" screen at rotation 0, stated as the module body
# cannot see the canvas
WIDTH, HEIGHT = 240, 320

CATHODES = len(ORDER)
DEPTH_OF = {digit: depth for depth, digit in enumerate(ORDER)}
UNLIT = tuple(color.rgb(*(round(front + (back - front) * depth / (CATHODES - 1))
                          for front, back in zip(CATHODE_FRONT, CATHODE_BACK)))
              for depth in range(CATHODES))

tube_font = font.load(TUBE_FONT)
stack = image(WIDTH, HEIGHT)
stack.antialias = ANTIALIAS
stack.font = tube_font
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


def place(digit):
    """Where a cathode's digit is drawn and at what size, for its depth."""
    depth = DEPTH_OF[digit]
    size = SIZE * DEPTH_SCALE ** depth
    return ((WIDTH - ADVANCE[digit] * size / SIZE) / 2,
            (HEIGHT - DIGIT_H * size / SIZE) / 2 - LETTERING_DOWN * size - DEPTH_Y * depth, size)


TUBE_X = (WIDTH - TUBE_W) // 2
TUBE_R = TUBE_W / 2
TUBE_CX = WIDTH / 2
DOME_CY = TUBE_TOP + TUBE_R
SIDE = TUBE_FOOT - DOME_CY
GLASS = shape.rounded_rectangle(TUBE_X, TUBE_TOP, TUBE_W, TUBE_FOOT - TUBE_TOP,
                                TUBE_R, TUBE_R, FOOT_CORNER, FOOT_CORNER)

FRONT = (
    (RIM.with_alpha(80), shape.rounded_rectangle(TUBE_X, TUBE_TOP, TUBE_W, TUBE_FOOT - TUBE_TOP,
                                                 TUBE_R, TUBE_R, FOOT_CORNER, FOOT_CORNER).stroke(1.5)),
    (RIM.with_alpha(30), shape.rounded_rectangle(TUBE_X + 3, TUBE_TOP + 3, TUBE_W - 6, TUBE_FOOT - TUBE_TOP - 5,
                                                 TUBE_R - 3, TUBE_R - 3, FOOT_CORNER - 2,
                                                 FOOT_CORNER - 2).stroke(1)),
    (RIM.with_alpha(22), shape.rounded_rectangle(TUBE_X + 8, DOME_CY - 6, 7, SIDE - 20, 3.5)),
    (RIM.with_alpha(150), shape.rounded_rectangle(TUBE_X + 10.5, DOME_CY + 24, 2, SIDE - 80, 1)),
    (RIM.with_alpha(55), shape.rounded_rectangle(TUBE_X + TUBE_W - 11, DOME_CY + 40, 2, SIDE - 120, 1)),
    (RIM.with_alpha(110), shape.arc(TUBE_CX, DOME_CY, TUBE_R - 9, TUBE_R - 6, -62, -24)),
    (RIM.with_alpha(40), shape.arc(TUBE_CX, DOME_CY, TUBE_R - 9, TUBE_R - 7, 30, 52)),
    (RIM.with_alpha(60), shape.rounded_rectangle(TUBE_X + 10, TUBE_FOOT - 3, TUBE_W - 20, 1.5, 0.75)),
)

TIP = ((color.rgb(68, 51, 34), shape.rounded_rectangle(TUBE_CX - 9, TUBE_TOP - 5, 18, 13, 8, 8, 3, 3)),
       (RIM.with_alpha(80), shape.rounded_rectangle(TUBE_CX - 9, TUBE_TOP - 5, 18, 13, 8, 8, 3, 3).stroke(1)),
       (RIM.with_alpha(140), shape.rounded_rectangle(TUBE_CX - 5, TUBE_TOP - 3, 3, 7, 1.5)))

SHEATH_AT = tuple((dx, dy) for dx in (-SHEATH, 0, SHEATH) for dy in (-SHEATH, 0, SHEATH) if dx or dy)


def build():
    """Draw the background every frame starts from."""
    stack.pen = BACKGROUND
    stack.clear()

    board_y = TUBE_FOOT + 16
    stack.pen = PIN
    for pin in range(PINS):
        stack.vspan(round(TUBE_X + 14 + pin * (TUBE_W - 28) / (PINS - 1)), TUBE_FOOT, board_y - TUBE_FOOT)
    stack.pen = BOARD
    stack.rectangle(rect(0, board_y, WIDTH, HEIGHT - board_y))

    stack.pen = TINT
    stack.shape(GLASS)
    wall = TUBE_FOOT - round(DOME_CY)
    for step in range(SHADE):
        stack.pen = BACKGROUND.with_alpha(round(SHADE_DARK * (1 - step / SHADE) ** 2))
        stack.vspan(TUBE_X + step, round(DOME_CY), wall - FOOT_CORNER // 2)
        stack.vspan(TUBE_X + TUBE_W - 1 - step, round(DOME_CY), wall - FOOT_CORNER // 2)
        stack.shape(shape.arc(TUBE_CX, DOME_CY, TUBE_R - step - 1, TUBE_R - step, -90, 90))

    stack.pen = NEON.with_alpha(ENVELOPE)
    stack.vspan(TUBE_X + 1, round(DOME_CY), wall - FOOT_CORNER)
    stack.vspan(TUBE_X + TUBE_W - 2, round(DOME_CY), wall - FOOT_CORNER)
    for row in range(BASE_ROWS):
        stack.pen = NEON.with_alpha(round(BASE_GLOW * (1 - row / BASE_ROWS) ** 2))
        stack.hspan(TUBE_X + 3, TUBE_FOOT - 2 - row, TUBE_W - 6)

    top = (HEIGHT - DIGIT_H) // 2 - 12
    bottom = (HEIGHT + DIGIT_H) // 2 + 8
    stack.pen = ROD
    stack.vspan(TUBE_X + 18, top, TUBE_FOOT - top)
    stack.vspan(TUBE_X + TUBE_W - 19, top, TUBE_FOOT - top)
    for y in (top - 2, bottom + 2):
        stack.pen = MICA.with_alpha(150)
        stack.shape(shape.ellipse(TUBE_CX, y, TUBE_R - 12, 3))
        stack.pen = MICA
        stack.shape(shape.ellipse(TUBE_CX, y, TUBE_R - 12, 3).stroke(1))

    for pen, part in TIP:
        stack.pen = pen
        stack.shape(part)

    for depth in range(CATHODES - 1, -1, -1):
        x, y, size = place(ORDER[depth])
        stack.pen = UNLIT[depth]
        stack.text(str(ORDER[depth]), x, y, size)


def frame(canvas, showing):
    """Draw one frame, the background, the cathode or two carrying current, and the tube."""
    canvas.pen = BACKGROUND
    canvas.clear()
    canvas.blit(stack, 0, 0)

    for digit, level in showing:
        if level:
            x, y, size = place(digit)
            canvas.pen = NEON.with_alpha(round(level * SHEATH_LEVEL))
            for dx, dy in SHEATH_AT:
                canvas.text(str(digit), x + dx, y + dy, size)
            canvas.pen = CORE.with_alpha(level)
            canvas.text(str(digit), x, y, size)

    canvas.bloom(GLOW_FROM, GLOW, GLOW_SPREAD)
    canvas.grid(MESH, MESH_DARK)
    canvas.vignette(CURVE)
    for pen, glass in FRONT:
        canvas.pen = pen
        canvas.shape(glass)


build()
shown = None


def draw(canvas, elapsed):
    global shown
    if shown is None:
        if (canvas.width, canvas.height) != (WIDTH, HEIGHT):
            raise ValueError(f'this drawing is laid out for {WIDTH}x{HEIGHT}, a 2.8" screen at '
                             f"rotation 0, and was given {canvas.width}x{canvas.height}")
        canvas.antialias = ANTIALIAS
        canvas.font = tube_font

    count, into = divmod(int(elapsed * 1000), COUNT_MS)
    up = min(1.0, into / CHANGE_MS)
    showing = ((count % 10, round(LIT * up)), ((count - 1) % 10, round(LIT * (1 - up))))
    if showing != shown:
        frame(canvas, showing)
        shown = showing
