from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import image, color, shape, mat3

"""
Spin a rainbow wheel on two screens, updated one after the other. Run
color_wheel_paired.py to see what a pair does differently.

Press "Boot" to exit the program.
"""

# Constants for drawing
INNER_RADIUS = 40
OUTER_RADIUS = 120
NUMBER_OF_LINES = 24
HUE_SHIFT = 4
ROTATION_SPEED = 2
LINE_THICKNESS = 2

# Create a MightyFX object with both SP/CE ports set up for screens, and a 2.8" screen on each
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# Two screens held separately, with no pair between them. update() does not return until
# its frame is on the glass, so the second panel only starts once the first has finished.
# Each waits its own tearing-effect signal and comes out clean, but the two are never
# showing the same frame and they drift as each runs to its own oscillator.
#
# What it buys is memory: each screen converts within a frame of its own, so the default
# reserve keeps up where a pair needs a deeper stage.
screens = Screen280(mighty.spce_a), Screen280(mighty.spce_b)

# Access the first screen and create a canvas to draw to
canvas = image(screens[0].width, screens[0].height)

# Pre-calculate the screen centre
centre_x, centre_y = screens[0].width / 2, screens[0].height / 2


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

        # Update the screens in turn, which spends two frames where a pair spends one
        screens[0].update(canvas)
        screens[1].update(canvas)

        # Advance both the rotation and the hue
        r += ROTATION_SPEED
        t += HUE_SHIFT

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
