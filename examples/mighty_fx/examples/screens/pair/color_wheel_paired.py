# A spinny rainbow wheel, on a pair of screens held in step. Change up some of the constants below to see what happens.

from mighty_fx import MightyFX, SPCE
from screens import Reserve, Screen280, ScreenPair
from picovector import image, color, shape, mat3

# Constants for drawing
INNER_RADIUS = 40
OUTER_RADIUS = 120
NUMBER_OF_LINES = 24
HUE_SHIFT = 4
ROTATION_SPEED = 2
LINE_THICKNESS = 2

# Create a MightyFX object with both SP/CE ports set up for screens, and a 2.8" screen on each
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# A pair holds its two panels to one refresh rate and keeps their scans together, so a
# frame reaches both without a tear band walking across either. Working out how takes a
# few seconds when the pair is created, and it goes on correcting as the program runs.
#
# Both panels change on the one frame, so both canvases are converted inside a single
# frame's time where two independent screens would each have a frame of their own. That
# is what the deeper reserve buys, and a pair drawing at full size refuses without it.
# color_wheel_in_turn.py draws the same wheel without a pair, for comparison.
pair = ScreenPair(Screen280(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES),
                  Screen280(mighty.spce_b, reserve=Reserve.FULL_SIZE_IMAGES))

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

        # Update the pair with the latest canvas, which draws it to both panels
        pair.update(canvas)

        # Advance both the rotation and the hue
        r += ROTATION_SPEED
        t += HUE_SHIFT

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
