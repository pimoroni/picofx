# Bounces a logo around the screen, recolouring it at each edge while the drifting background shows through its darkest parts. Change up some of the constants below to see what happens.

import time
from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import color, spritesheet

# Constants for drawing
LOGO_PATH = "/examples/assets/pirate_face.gif"  # The logo to bounce, beside this example
HOLLOW_LOGO = True      # Whether the logo's darkest colour is left open for the background
STEP = 3                # How many pixels the logo moves each frame
FRAME_DURATION = 0.02   # How long each position is shown for, in seconds
BG_VALUE = 48           # How bright the background shades are, out of 255
HUE_SHIFT = 2           # How far the background hue moves each frame, out of 256
COLORS = (color.rgb(0, 96, 255), color.rgb(255, 32, 96), color.rgb(64, 208, 32),
          color.rgb(255, 176, 0), color.rgb(160, 64, 255))

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# A palettised source, such as a GIF or an indexed PNG, is drawn through its colour table,
# so nothing here is redrawn frame to frame: a transparent entry takes bg_color, and a
# recolour is a write to the table. A single-frame GIF arrives as a spritesheet of one
# sprite, which is how its palette comes along
logo = spritesheet.load(LOGO_PATH).sprite(0)
palette = logo.palette

# Entries are told apart by how bright they were drawn rather than by index, which is
# unsafe twice over: an export may reorder the table, and the decoder can present one
# colour as several identical entries. The darkest is the logo's own shading, and every
# other opaque entry carries the colour that changes, so a logo drawn in several colours
# comes out in one
opaque = [i for i in range(logo.palette_size) if palette[i].a != 0]
darkest = min(opaque, key=lambda i: palette[i].r + palette[i].g + palette[i].b)
brighter = [i for i in opaque if i != darkest]

# An entry is made transparent by writing one, so the darkest parts become holes and take
# the background, as everything outside the logo already does
if HOLLOW_LOGO:
    palette[darkest] = color.transparent


def recolor(new_color):
    for i in brighter:
        palette[i] = new_color


# The travel the logo has before its far edge reaches the far edge of the screen
limit_x = screen.height - logo.width
limit_y = screen.width - logo.height

x, y = 0, 0
step_x, step_y = STEP, STEP
index = 0
hue = 0

recolor(COLORS[index])

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Whatever the logo does not cover takes the background colour, and the colour
        # table is composited every frame, so a background that drifts costs no more than
        # a still one. Keeping the background dark and the logo bright is what stops one
        # disappearing into the other
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

        time.sleep(FRAME_DURATION)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
