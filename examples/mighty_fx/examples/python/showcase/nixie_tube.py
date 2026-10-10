import time
from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import color, font, image, rect, shape

"""
Draw a nixie tube: ten cathodes bent into digits and stacked front to back in a glass cylinder,
the one carrying current glowing red-orange through the anode mesh.

The glass, the nine unlit cathodes and the glow at the tube's foot never change, so they are drawn
once into the ground every frame starts from. A frame is that ground, the lit cathode over it, three
filters, and the front of the glass.

Press "Boot" to exit the program.

Section: Signs and displays
"""

# Constants for drawing
TUBE_FONT = "/rom/fonts/AlumniSansPinstripe.af"
ANTIALIAS = image.X4                # A vector face needs it, and a line a pixel wide is all edge
NEON = color.rgb(255, 102, 34)      # The red-orange a nixie's neon glows. rgb(120, 190, 255) is an argon tube
CORE = color.rgb(255, 170, 102)     # And the paler middle of it, along the wire itself
GROUND = color.black                # Behind the tube

# An unlit cathode is bare metal, drawn opaque. Drawn in the neon's colour at a low alpha, ten digits
# crossing would build up towards the lit colour and hide the one being shown
CATHODE_FRONT = (51, 43, 36)        # At the front of the stack, warmed by the neon behind it
CATHODE_BACK = (22, 20, 18)         # And at the back, further into the dark

# The stack, front cathode first, in an order tubes commonly use so the ones in front hide the lit one
# least. One further back shows smaller and a little higher, the tube being seen from just above
ORDER = (6, 7, 5, 8, 4, 3, 9, 2, 0, 1)
DEPTH_SCALE = 0.978
DEPTH_Y = 1
DIGIT_H = 185                       # The ink height of the front cathode's digit, in panel pixels
LIT = 255                           # The cathode carrying current
# A size to measure the face at, its ink scaling with it from there. Its em box has to fit the scratch,
# or the measurement reports the ink that landed and not the ink the face would have drawn
REF = 200

# The tube, a glass cylinder stood on its pins, domed at the top and flat at the foot
TUBE_W = 130
TUBE_TOP = 6
TUBE_FOOT = 292                     # Where the glass ends and the pins begin
FOOT_CORNER = 8
TINT = color.rgb(34, 17, 0)         # The glass, warmed by what is inside it
RIM = color.rgb(255, 221, 170)      # What catches the light on the glass
SHADE = 18                          # How far in from the wall the glass darkens, which rounds the cylinder
SHADE_DARK = 170                    # How dark it is at the wall itself, of 255
PINS = 11
PIN = color.rgb(119, 102, 85)
BOARD = color.rgb(17, 17, 17)       # What the tube is stood in
ROD = color.rgb(68, 60, 52)         # The supports down either side of the stack
MICA = color.rgb(102, 94, 85)       # The spacers the stack is held between

# What the glow reaches besides the cathode itself
ENVELOPE = 60                       # The glass down either side of the tube, catching a little of it
BASE_GLOW = 110                     # The gas low in the tube, where the cathodes' leads gather
BASE_ROWS = 34                      # How far up that reaches, falling away over the distance
SHEATH = 2                          # How far the neon's sheath reaches past the wire, in panel pixels
SHEATH_LEVEL = 0.28                 # Its brightness against the core's

# The filters over the whole frame, the neon's glow, the anode mesh in front of it, and the glass
GLOW_FROM = 100                     # The brightness a pixel glows from, well above an unlit cathode's
GLOW = 220                          # How much of the halo is added back, 255 being all of it
GLOW_SPREAD = 10                    # How far it reaches, in panel pixels
MESH = 4                            # Every this many rows and columns is darkened
MESH_DARK = 30                      # By this much, of 255
CURVE = 80                          # How far the picture falls away at the edges

COUNT_MS = 1000                     # A digit a second, this being the seconds place of a clock
# One digit going out as the next comes up. Drawing a frame costs about 95ms of that, so a change lands in
# a frame or two, which is what a tube does, and both digits are seen together on the way
CHANGE_MS = 200

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

canvas = screen.canvas()
WIDTH, HEIGHT = canvas.width, canvas.height
canvas.antialias = ANTIALIAS

CATHODES = len(ORDER)
DEPTH_OF = {digit: depth for depth, digit in enumerate(ORDER)}
UNLIT = tuple(color.rgb(*(round(front + (back - front) * depth / (CATHODES - 1))
                          for front, back in zip(CATHODE_FRONT, CATHODE_BACK)))
              for depth in range(CATHODES))

# The ground, drawn once. Panel sized, and it stands in as the scratch the measurement below is taken on
# before it holds the ground
stack = image(WIDTH, HEIGHT)
stack.antialias = ANTIALIAS
# The face goes on both, a cathode being drawn onto the ground while it is unlit and onto the frame once it is
stack.font = canvas.font = font.load(TUBE_FONT)
BLANK = bytes(len(stack.raw))


def ink_rows(letters, size, at):
    """The first and last rows a drawing of these characters inks, taken off the scratch.

    Both ends of the buffer are stripped whole, which is two C calls where a row at a time over a panel is
    a second and a half of allocation. Read off a drawing, the face's own metrics being the em box and the
    advance, and neither is the ink.
    """
    stack.raw[:] = BLANK
    stack.pen = color.white
    stack.text(letters, at, at, size)

    filled = bytes(stack.raw)
    return ((len(filled) - len(filled.lstrip(b"\0"))) // stack.stride,
            (len(filled.rstrip(b"\0")) - 1) // stack.stride)


TOP, BOTTOM = ink_rows("8", REF, 0)
SIZE = REF * DIGIT_H / (BOTTOM - TOP + 1)
INK_DOWN = TOP / REF        # How far below the y it is drawn at a digit's ink starts, per unit of size
ADVANCE = {digit: stack.measure_text(str(digit), font_size=SIZE)[0] for digit in ORDER}
print(f"a digit {DIGIT_H} tall at font size {SIZE:.0f}, over a stack {CATHODES} deep")


def place(digit):
    """Where a cathode's digit is drawn, and at what size, for its depth in the stack.

    Every digit is centred, as a tube's cathodes are, so the count does not walk across the tube as the
    shapes change width. The em box a digit is drawn in is taller than the tube, so the y it is drawn at
    is where its ink has to land less how far below that y the ink starts.
    """
    depth = DEPTH_OF[digit]
    size = SIZE * DEPTH_SCALE ** depth
    return ((WIDTH - ADVANCE[digit] * size / SIZE) / 2,
            (HEIGHT - DIGIT_H * size / SIZE) / 2 - INK_DOWN * size - DEPTH_Y * depth, size)


TUBE_X = (WIDTH - TUBE_W) // 2
TUBE_R = TUBE_W / 2
TUBE_CX = WIDTH / 2
DOME_CY = TUBE_TOP + TUBE_R
SIDE = TUBE_FOOT - DOME_CY          # The length of the straight wall, under the dome
GLASS = shape.rounded_rectangle(TUBE_X, TUBE_TOP, TUBE_W, TUBE_FOOT - TUBE_TOP,
                                TUBE_R, TUBE_R, FOOT_CORNER, FOOT_CORNER)

# The front of the glass, drawn over the mesh and everything behind it. Made once, a shape built per frame
# being an allocation
FRONT = (
    # The outline, and a fainter line just inside it where the wall's thickness shows
    (RIM.with_alpha(80), shape.rounded_rectangle(TUBE_X, TUBE_TOP, TUBE_W, TUBE_FOOT - TUBE_TOP,
                                                 TUBE_R, TUBE_R, FOOT_CORNER, FOOT_CORNER).stroke(1.5)),
    (RIM.with_alpha(30), shape.rounded_rectangle(TUBE_X + 3, TUBE_TOP + 3, TUBE_W - 6, TUBE_FOOT - TUBE_TOP - 5,
                                                 TUBE_R - 3, TUBE_R - 3, FOOT_CORNER - 2,
                                                 FOOT_CORNER - 2).stroke(1)),
    # A streak down the lit side, a faint wide one with a bright narrow one in it, and a thinner one opposite
    (RIM.with_alpha(22), shape.rounded_rectangle(TUBE_X + 8, DOME_CY - 6, 7, SIDE - 20, 3.5)),
    (RIM.with_alpha(150), shape.rounded_rectangle(TUBE_X + 10.5, DOME_CY + 24, 2, SIDE - 80, 1)),
    (RIM.with_alpha(55), shape.rounded_rectangle(TUBE_X + TUBE_W - 11, DOME_CY + 40, 2, SIDE - 120, 1)),
    # The dome catching the light on both shoulders, and the foot where the glass turns under
    (RIM.with_alpha(110), shape.arc(TUBE_CX, DOME_CY, TUBE_R - 9, TUBE_R - 6, -62, -24)),
    (RIM.with_alpha(40), shape.arc(TUBE_CX, DOME_CY, TUBE_R - 9, TUBE_R - 7, 30, 52)),
    (RIM.with_alpha(60), shape.rounded_rectangle(TUBE_X + 10, TUBE_FOOT - 3, TUBE_W - 20, 1.5, 0.75)),
)

# The tip on top of the dome, where the tube was sealed, dark glass with the light on one side of it
TIP = ((color.rgb(68, 51, 34), shape.rounded_rectangle(TUBE_CX - 9, TUBE_TOP - 5, 18, 13, 8, 8, 3, 3)),
       (RIM.with_alpha(80), shape.rounded_rectangle(TUBE_CX - 9, TUBE_TOP - 5, 18, 13, 8, 8, 3, 3).stroke(1)),
       (RIM.with_alpha(140), shape.rounded_rectangle(TUBE_CX - 5, TUBE_TOP - 3, 3, 7, 1.5)))

SHEATH_AT = tuple((dx, dy) for dx in (-SHEATH, 0, SHEATH) for dy in (-SHEATH, 0, SHEATH) if dx or dy)


def build(light):
    """The tube and its stack unlit, and what the glow reaches besides the cathodes.

    This is the ground a frame starts from, so it holds everything that does not change: nine of the ten
    cathodes are always unlit, and the tenth is drawn again over the top.
    """
    stack.pen = GROUND
    stack.clear()

    # The pins, from the foot of the glass into the board, and the board
    board_y = TUBE_FOOT + 16
    stack.pen = PIN
    for pin in range(PINS):
        stack.vspan(round(TUBE_X + 14 + pin * (TUBE_W - 28) / (PINS - 1)), TUBE_FOOT, board_y - TUBE_FOOT)
    stack.pen = BOARD
    stack.rectangle(rect(0, board_y, WIDTH, HEIGHT - board_y))

    # The glass, darkening towards its walls as a cylinder does
    stack.pen = TINT
    stack.shape(GLASS)
    wall = TUBE_FOOT - round(DOME_CY)
    for step in range(SHADE):
        stack.pen = GROUND.with_alpha(round(SHADE_DARK * (1 - step / SHADE) ** 2))
        stack.vspan(TUBE_X + step, round(DOME_CY), wall - FOOT_CORNER // 2)
        stack.vspan(TUBE_X + TUBE_W - 1 - step, round(DOME_CY), wall - FOOT_CORNER // 2)
        stack.shape(shape.arc(TUBE_CX, DOME_CY, TUBE_R - step - 1, TUBE_R - step, -90, 90))

    # And the light of the gas held in it, down the walls and gathered at the foot
    stack.pen = light.with_alpha(ENVELOPE)
    stack.vspan(TUBE_X + 1, round(DOME_CY), wall - FOOT_CORNER)
    stack.vspan(TUBE_X + TUBE_W - 2, round(DOME_CY), wall - FOOT_CORNER)
    for row in range(BASE_ROWS):
        stack.pen = light.with_alpha(round(BASE_GLOW * (1 - row / BASE_ROWS) ** 2))
        stack.hspan(TUBE_X + 3, TUBE_FOOT - 2 - row, TUBE_W - 6)

    # The supports down either side of the stack, and the spacers it is held between. A spacer is a disc
    # seen from just above, so the top of it shows as a thin ellipse
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


def draw(showing, light):
    """One frame: the ground, the cathode or two carrying current, and the tube over both.

    showing pairs a digit with its brightness, so a change is the one going out and the one coming up
    drawn together, each at its own place in the stack.
    """
    # The ground is cleared under first. Its blended pixels fall a little short of opaque, so without the clear
    # the previous frame shows through them
    canvas.pen = GROUND
    canvas.clear()
    canvas.blit(stack, 0, 0)

    # A lit cathode is drawn over the whole stack. In a tube the neon outshines the wires in front of it by
    # far more than a panel's range can show, so drawn behind them it reads as hidden. Its sheath is the
    # digit again around the wire, and its core the digit on the wire
    for digit, level in showing:
        if level:
            x, y, size = place(digit)
            canvas.pen = light.with_alpha(round(level * SHEATH_LEVEL))
            for dx, dy in SHEATH_AT:
                canvas.text(str(digit), x + dx, y + dy, size)
            canvas.pen = CORE.with_alpha(level)
            canvas.text(str(digit), x, y, size)

    # The bloom goes on the frame, which is opaque. On an image with transparency it would lift a channel
    # above that pixel's alpha, which blit relies on never happening
    canvas.bloom(GLOW_FROM, GLOW, GLOW_SPREAD)
    canvas.grid(MESH, MESH_DARK)
    canvas.vignette(CURVE)
    for pen, glass in FRONT:
        canvas.pen = pen
        canvas.shape(glass)


marked = time.ticks_ms()
build(NEON)
print(f"{CATHODES} cathodes drawn, the nine unlit ones into the ground, in"
      f" {time.ticks_diff(time.ticks_ms(), marked)}ms")

shown = None
started = time.ticks_ms()

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        elapsed = time.ticks_diff(time.ticks_ms(), started)
        count, into = divmod(elapsed, COUNT_MS)
        # A tube switches quickly, and for that moment the cathode losing the current still glows
        up = min(1.0, into / CHANGE_MS)
        showing = ((count % 10, round(LIT * up)), ((count - 1) % 10, round(LIT * (1 - up))))
        if showing != shown:
            draw(showing, NEON)
            screen.update(canvas)
            shown = showing

        time.sleep_ms(10)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
