import sys
import time
from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import color, shape

"""
Fade a screen's backlight up and down over a still frame.

Change up some of the constants below to see what happens.

Press "Boot" to exit the program.
"""

# Constants for drawing
FADE_STEPS = 50         # How many steps the backlight takes from off to full
STEP_INTERVAL = 0.02    # The time (in seconds) each of those steps is held for
RING_THICKNESS = 30     # How wide the ring drawn on the screen is

# Which screen is on the port, "2.8" or "1.54", and how far it is turned, 0, 90, 180 or 270, or
# what the effects file passes in args, the size first
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ROTATION = 0 if not sys.argv[2:] else int(sys.argv[2])
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a, rotation=ROTATION)

# Create a canvas to draw to, sized as the screen is turned
canvas = screen.canvas()

# Pre-calculate the screen centre, and how far the ring reaches to fit its narrower side
centre_x, centre_y = canvas.width / 2, canvas.height / 2
reach = min(centre_x, centre_y) * 0.8

# Draw a ring for the backlight to light up
canvas.pen = color.black
canvas.clear()
canvas.pen = color.white
canvas.shape(shape.circle(centre_x, centre_y, reach))
canvas.pen = color.black
canvas.shape(shape.circle(centre_x, centre_y, reach - RING_THICKNESS))

# Show the frame first, as the backlight stays dark until a frame reaches the glass
screen.update(canvas)

# Variables to keep track of the fade
level = FADE_STEPS
direction = -1

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Every screen on a port shares its backlight. The steps are spaced evenly to the eye
        screen.backlight.brightness(level / FADE_STEPS)

        # Turn around at either end of the fade
        level += direction
        if level in (0, FADE_STEPS):
            direction = -direction

        time.sleep(STEP_INTERVAL)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
