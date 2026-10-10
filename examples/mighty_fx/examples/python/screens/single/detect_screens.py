import sys
from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import image, color, shape

"""
Draw to whichever screens are plugged in, on one SP/CE port or both. Each screen counts
out its own position in dots.

Press "Boot" to exit the program.
"""

# Constants for drawing
HUE_SHIFT = 2           # How far around the colour wheel to move each frame
DOT_RADIUS = 14         # The size of the dots counting out a screen's position
DOT_SPACING = 40        # The gap between the centres of those dots

# Which screen is on each port, "2.8" or "1.54". The effects file can pass one for both
# ports, or one each, the ports being free to differ where a pair is not
SCREEN_SIZES = ("2.8", "2.8") if not sys.argv[1:] else (sys.argv[1], sys.argv[-1])

# Create a MightyFX object with both SP/CE ports set up for screens
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# A screen refuses to be created where no panel answered on its port, and claims
# nothing when it does, so an empty port can be skipped and the rest carry on. The
# message it raises says which chip select went quiet
screens = []
for port, size in zip((mighty.spce_a, mighty.spce_b), SCREEN_SIZES):
    try:
        screens.append(SCREEN_TYPES[size](port))
    except ValueError as e:
        print(e)

# A canvas each, since the two ports are free to hold different sizes and a canvas is
# drawn at the size of the panel it is going to
canvases = [image(screen.width, screen.height) for screen in screens]

if not screens:
    print("No screens answered, so there is nothing to draw to. Plug one into SP/CE A or B.")

# Variable to keep track of the hue position
t = 0

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    # Loop until the "Boot" button is pressed, and fall straight through with no screens
    while screens and not mighty.boot_pressed():
        for position, (screen, canvas) in enumerate(zip(screens, canvases)):
            # Fill the canvas with the next colour in the cycle, giving each screen its
            # own place in the cycle so the two are never showing the same colour
            canvas.pen = color.hsv((t + position * 128) % 256, 255, 255)
            canvas.clear()

            # Count out this screen's position down the middle, one dot for the first
            # screen that answered and two for the second
            canvas.pen = color.black
            centre_x, centre_y = canvas.width / 2, canvas.height / 2
            for dot in range(position + 1):
                y = centre_y + (dot - position / 2) * DOT_SPACING
                canvas.shape(shape.circle(centre_x, y, DOT_RADIUS))

            # Update this screen with the canvas as it now stands
            screen.update(canvas)

        # Advance the hue
        t += HUE_SHIFT

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
