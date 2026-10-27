import sys
from mighty_fx import MightyFX, SPCE
from timing import Pacer
from screens import SCREEN_TYPES
from picovector import color, spritesheet

"""
Bounce a logo around the screen, recolouring it at each edge
while the drifting background shows through its darkest parts.

Change up some of the constants below to see what happens.

Press "Boot" to exit the program.

Section: Animation
"""

# Constants for drawing
LOGO_PATH = "/examples/assets/pirate_face.gif"  # The logo to bounce
HOLLOW_LOGO = True      # Whether the logo's darkest colour is left open for the background
STEP = 3                # How many pixels the logo moves each frame
FRAME_DURATION = 0.02   # How long each position is shown for, in seconds
BG_VALUE = 48           # How bright the background shades are out of 255, kept dark under a bright logo
HUE_SHIFT = 2           # How far the background hue moves each frame, out of 256
COLORS = (color.rgb(0, 96, 255), color.rgb(255, 32, 96), color.rgb(64, 208, 32),
          color.rgb(255, 176, 0), color.rgb(160, 64, 255))

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a)

# A single-frame GIF loads as one sprite, drawn through a colour table that rewriting recolours
try:
    logo = spritesheet.load(LOGO_PATH).sprite(0)
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{LOGO_PATH}' is missing! Check it is on the board") from None

palette = logo.palette

# Pick entries by brightness, as an export may reorder the table.
# The darkest is the shading and the rest take the changing colour
opaque = [i for i in range(logo.palette_size) if palette[i].a != 0]
darkest = min(opaque, key=lambda i: palette[i].r + palette[i].g + palette[i].b)
brighter = [i for i in opaque if i != darkest]

# Should the darkest parts be holes that show the background?
if HOLLOW_LOGO:
    palette[darkest] = color.transparent


def recolor(new_color):
    """Recolour the logo by rewriting every brighter entry of its colour table."""
    for i in brighter:
        palette[i] = new_color


# How far the logo can travel each way, with the panel's sides swapped for its quarter turn
limit_x = screen.height - logo.width
limit_y = screen.width - logo.height

x, y = 0, 0
step_x, step_y = STEP, STEP
index = 0
hue = 0

recolor(COLORS[index])

# A pacer holds the frame rate, so the logo moves at the speed set here
pacer = Pacer(FRAME_DURATION)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Whatever the logo leaves uncovered takes bg_color,
        # so a drifting background costs no more than a still one
        screen.update(logo, rotation=90, offset=(x, y),
                      bg_color=color.hsv(hue, 255, BG_VALUE))

        x += step_x
        y += step_y
        hue = (hue + HUE_SHIFT) % 256

        # Turn around at each edge, clamping so a step that overshoots does not leave
        # the logo part way off the screen, and take the next colour
        if x <= 0 or x >= limit_x:
            x = min(max(x, 0), limit_x)
            step_x = -step_x
            index = (index + 1) % len(COLORS)
            recolor(COLORS[index])

        if y <= 0 or y >= limit_y:
            y = min(max(y, 0), limit_y)
            step_y = -step_y
            index = (index + 1) % len(COLORS)
            recolor(COLORS[index])

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
