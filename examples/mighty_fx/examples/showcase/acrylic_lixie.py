import time
from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import color, font, image, shape

"""
Draw a lixie: ten engraved acrylic sheets stacked front to back with a digit on each, an LED
under every sheet, and only the one being shown lit. The engraving is what the light escapes
through, so a lit sheet reads as its digit in fine bright lines while the nine unlit ones stay a
faint tracery, and a sheet further back appears a size smaller, which is why the edges nest.

Nothing here is an image of a sheet: the nine that never change are drawn once into the frame
every real frame starts from, and the lit one goes straight onto it. The face is a hairline, and
one measurement sizes every digit, a face's ink being proportional to the size asked for.

The glow goes on the frame, which is opaque, and not on any sheet.

Press "Boot" to exit the program.
"""

# Constants for drawing
LIXIE_FONT = "/rom/fonts/AlumniSansPinstripe.af"
ANTIALIAS = image.X4        # A vector face needs it, and a line a pixel wide is all edge
GROUND = color.black        # Behind the stack, which is a dark box

# The stack, front sheet first, and the digit each sheet carries in that order
ORDER = (1, 2, 3, 4, 5, 6, 7, 8, 9, 0)
DEPTH_SCALE = 0.984         # How much smaller a sheet one place further back appears
SHEET_W = 226               # The front sheet, the rest being scaled from it
SHEET_H = 304
CORNER = 14                 # How far a sheet's corners are rounded
EDGE = 2                    # The width of a cut edge, which is the brightest thing on a lit sheet
DIGIT_H = 186               # The ink height of the front sheet's digit, in panel pixels
LIT = 255                   # The sheet with its LED on
GHOST = 20                  # And one without, the engraving picking up a little of its neighbour's light
REF = 200                   # A size to measure the face at, its ink scaling with it from there

# The LEDs, which are RGB and under the sheets. A pass through the digits is one colour, changed while the
# stack is being drawn again anyway
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
# One digit going out as the next comes up. A frame costs about 130ms of that, so a change lands in a
# frame or two: what it buys is that both digits are seen together on the way
CHANGE_MS = 220

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

canvas = screen.canvas()
WIDTH, HEIGHT = canvas.width, canvas.height
canvas.antialias = ANTIALIAS

SHEETS = len(ORDER)
DEPTH_OF = {digit: depth for depth, digit in enumerate(ORDER)}
SCALE_AT = tuple(DEPTH_SCALE ** depth for depth in range(SHEETS))

# The nine unlit sheets, drawn once. Panel sized, and it stands in as the scratch the measurement below is
# taken on before it holds that frame
stack = image(WIDTH, HEIGHT)
stack.antialias = ANTIALIAS
# The face goes on both: a sheet is drawn onto the stack while it is unlit and onto the frame once it is
stack.font = canvas.font = font.load(LIXIE_FONT)
BLANK = bytes(len(stack.raw))


def ink_rows(letters, size, at):
    """The first and last rows a drawing of these characters inks, taken off the scratch.

    Read off a drawing, the face's own metrics being the em box and the advance, and neither is the ink.
    Both ends of the buffer are stripped whole, which is two C calls.
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
print(f"a digit {DIGIT_H} tall at font size {SIZE:.0f}, on sheets of {SHEET_W}x{SHEET_H} down to"
      f" {round(SHEET_W * SCALE_AT[-1])}x{round(SHEET_H * SCALE_AT[-1])}")

# A sheet's cut edges, one shape per depth. Made once: a stroked outline is a path of its own, and a shape
# built per frame is what makes an animation judder
EDGES = []
for depth in range(SHEETS):
    wide, tall = SHEET_W * SCALE_AT[depth], SHEET_H * SCALE_AT[depth]
    EDGES.append(shape.rounded_rectangle((WIDTH - wide) / 2, (HEIGHT - tall) / 2, wide, tall,
                                         CORNER * SCALE_AT[depth]).stroke(EDGE))


def sheet(into, digit, ink):
    """One sheet onto this image: its cut edges, and the digit engraved on it.

    Both are drawn at the size that sheet's depth appears at, and centred, the stack being seen face on.
    """
    depth = DEPTH_OF[digit]
    scale = SCALE_AT[depth]
    into.pen = ink
    into.shape(EDGES[depth])
    into.text(str(digit), (WIDTH - ADVANCE[digit] * scale) / 2,
              (HEIGHT - DIGIT_H * scale) / 2 - INK_DOWN * SIZE * scale, SIZE * scale)


def build(light):
    """The whole stack unlit, and the light out of the base, in the colour the LEDs are set to.

    This is the ground a frame starts from, so it holds everything that does not change while one colour
    is being shown: nine of the ten sheets are always unlit, and the tenth is drawn again over the top.
    """
    stack.pen = GROUND
    stack.clear()
    for row in range(FOOT):
        stack.pen = light.with_alpha(round(SPILL * (1 - row / FOOT) ** 2))
        stack.hspan(0, HEIGHT - 1 - row, WIDTH)

    unlit = light.with_alpha(GHOST)
    for depth in range(SHEETS - 1, -1, -1):
        sheet(stack, ORDER[depth], unlit)


def draw(showing, light):
    """One frame: the stack, the sheet or two with light in them, and the glow off the whole picture.

    showing pairs a digit with its brightness, so a change is the one going out and the one coming up drawn
    together, each at its own place in the stack.
    """
    canvas.blit(stack, 0, 0)
    for digit, level in showing:
        if level:
            sheet(canvas, digit, light.with_alpha(level))

    canvas.bloom(GLOW_FROM, GLOW, GLOW_SPREAD)
    canvas.vignette(CURVE)


turn = 0
light = COLOURS[turn]
marked = time.ticks_ms()
build(light)
print(f"{SHEETS} sheets drawn unlit in {time.ticks_diff(time.ticks_ms(), marked)}ms")

shown = None
started = time.ticks_ms()

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        elapsed = time.ticks_diff(time.ticks_ms(), started)
        count, into = divmod(elapsed, COUNT_MS)
        if count >= SHEETS:
            # A pass through every digit is done, so the LEDs take the next colour and the stack, which
            # carries that colour in nine sheets and the light out of the base, is drawn again
            turn = (turn + 1) % len(COLOURS)
            light = COLOURS[turn]
            build(light)
            started = time.ticks_ms()
            continue

        # A sheet's LED switches quickly, and for that moment the sheet losing it still has some light
        up = min(1.0, into / CHANGE_MS)
        showing = ((ORDER[count], round(LIT * up)), (ORDER[count - 1], round(LIT * (1 - up))))
        if showing != shown:
            draw(showing, light)
            screen.update(canvas)
            shown = showing

        time.sleep_ms(10)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
