import sys
import time
from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import image, color, shape

"""
Fade a screen's backlight up and down over a still frame. Change up some of the constants
below to see what happens.

Press "Boot" to exit the program.
"""

# Constants for drawing
FADE_STEPS = 50         # How many steps the backlight takes from off to full
STEP_INTERVAL = 0.02    # The time (in seconds) each of those steps is held for
RING_THICKNESS = 30     # How wide the ring drawn on the screen is

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a)

# Access the screen and create a canvas to draw to
canvas = image(screen.width, screen.height)

# Pre-calculate the screen centre
centre_x, centre_y = screen.width / 2, screen.height / 2

# Draw a ring for the backlight to light up
canvas.pen = color.black
canvas.clear()
canvas.pen = color.white
canvas.shape(shape.circle(centre_x, centre_y, centre_x * 0.8))
canvas.pen = color.black
canvas.shape(shape.circle(centre_x, centre_y, centre_x * 0.8 - RING_THICKNESS))

# Show that frame before touching the backlight. A backlight stays dark until a frame
# has reached the glass, so nothing lights up on whatever the panel held at power-on,
# and asking for a brightness is one of the things that ends the wait
screen.update(canvas)

# Variables to keep track of the fade
level = FADE_STEPS
direction = -1

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Every screen on a port shares its backlight line, and so its setting. The
        # steps are evenly spaced to the eye rather than in duty, and every setting
        # above zero lands somewhere the panel actually answers
        screen.backlight.brightness(level / FADE_STEPS)

        # Turn around at either end of the fade
        level += direction
        if level in (0, FADE_STEPS):
            direction = -direction

        time.sleep(STEP_INTERVAL)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
