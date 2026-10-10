import sys
from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES, Reserve, ScreenPair
from picovector import image, color, shape, mat3

"""
Spin a rainbow wheel on a pair of screens arranged to face each other, one of them
mirrored to suit. Change up some of the constants below to see what happens.

Press "Boot" to exit the program.
"""

# Constants for drawing
INNER_RADIUS = 40
OUTER_RADIUS = 120
NUMBER_OF_LINES = 24
HUE_SHIFT = 4
ROTATION_SPEED = 2
LINE_THICKNESS = 2

# Which screen is on both ports, "2.8" or "1.54", or what the effects file passes in args.
# A pair aligns its panels, which needs their rates close, and the two sizes default
# too far apart to bridge, so both panels take one size here
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with both SP/CE ports set up for screens, and one on each
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# A pair, so both panels change on the one frame. color_wheel_paired.py says what that
# buys and why it needs the deeper reserve
pair = ScreenPair(ScreenType(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES),
                  ScreenType(mighty.spce_b, reserve=Reserve.FULL_SIZE_IMAGES))

# Access the first screen and create a canvas to draw to. A pair's panels are the same
# size as each other, so either one gives the size to draw at
first = pair.screens[0]
canvas = image(first.width, first.height)

# Pre-calculate the screen centre
centre_x, centre_y = first.width / 2, first.height / 2

# Variables to keep track of rotation and hue positions
r = 0
t = 0

# Create a line shape to use throughout the program
line = shape.line(INNER_RADIUS, 0,  # Start position (x, y)
                  0, OUTER_RADIUS,  # End position (x, y)
                  LINE_THICKNESS)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Clear the canvas to black
        canvas.pen = color.black
        canvas.clear()

        # Go from 0 to 360 degrees, in equal divisions for the number of lines
        for i in range(0, 360, 360 // NUMBER_OF_LINES):
            # Calculate the colour hue of the line, giving full saturation and value
            hue = (i * 255) // 360
            canvas.pen = color.hsv((hue + t) % 256, 255, 255)

            # Rotate the line we originally create, and move it towards the screen centre
            line.transform = mat3().translate(centre_x, centre_y).rotate(i + r)

            # Apply the line with the current pen colour to the canvas
            canvas.shape(line)

        # One frame, placed differently on each panel: a pair takes one value for both
        # screens or a 2-tuple giving one each, so only the second is mirrored. Two panels
        # mounted back to back, or either side of a model, then read the same way round
        pair.update(canvas, mirror=(False, True))

        # Advance both the rotation and the hue
        r += ROTATION_SPEED
        t += HUE_SHIFT

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
