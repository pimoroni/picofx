# A spinny rainbow wheel. Change up some of the constants below to see what happens.

import math
from mighty_fx import MightyFX, SPCE

# Constants for drawing
INNER_RADIUS = 40
OUTER_RADIUS = 120
NUMBER_OF_LINES = 24
HUE_SHIFT = 0.02
ROTATION_SPEED = 2
LINE_THICKNESS = 2

mighty = MightyFX(spce_a=SPCE.SCREEN_154, spce_b=SPCE.SCREEN_154)
screens = [mighty.screen_a, mighty.screen_b]

# Variables to keep track of rotation and hue positions
r = 0
t = 0

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        for screen in screens:
            BLACK = screen.create_pen(0, 0, 0)
            WIDTH, HEIGHT = screen.get_bounds()
            screen.set_pen(BLACK)
            screen.clear()
            for i in range(0, 360, 360 // NUMBER_OF_LINES):
                screen.set_pen(screen.create_pen_hsv((i / 360) + t, 1.0, 1.0))

                # Draw some lines, offset by the rotation variable
                screen.line(int(WIDTH / 2 + math.cos(math.radians(i + r)) * INNER_RADIUS),
                            int(HEIGHT / 2 + math.sin(math.radians(i + r)) * INNER_RADIUS),
                            int(WIDTH / 2 + math.cos(math.radians(i + 90 + r)) * OUTER_RADIUS),
                            int(HEIGHT / 2 + math.sin(math.radians(i + 90 + r)) * OUTER_RADIUS),
                            LINE_THICKNESS)
            screen.update()
            r += ROTATION_SPEED
            t += HUE_SHIFT

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
