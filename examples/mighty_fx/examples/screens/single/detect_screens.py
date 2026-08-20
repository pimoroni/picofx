from mighty_fx import MightyFX, SPCE
from screens import Screen280
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

# Create a MightyFX object with both SP/CE ports set up for screens
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# A screen refuses to be created where no panel answered on its port, and claims
# nothing when it does, so an empty port can be skipped and the rest carry on. The
# message it raises says which chip select went quiet
screens = []
for port in (mighty.spce_a, mighty.spce_b):
    try:
        screens.append(Screen280(port))
    except ValueError as e:
        print(e)

if screens:
    # Create a canvas to draw to, sized from the first screen that answered
    canvas = image(screens[0].width, screens[0].height)

    # Pre-calculate the screen centre
    centre_x, centre_y = screens[0].width / 2, screens[0].height / 2
else:
    print("No screens answered, so there is nothing to draw to. Plug one into SP/CE A or B.")

# Variable to keep track of the hue position
t = 0

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    # Loop until the "Boot" button is pressed, and fall straight through with no screens
    while screens and not mighty.boot_pressed():
        for position, screen in enumerate(screens):
            # Fill the canvas with the next colour in the cycle, giving each screen its
            # own place in the cycle so the two are never showing the same colour
            canvas.pen = color.hsv((t + position * 128) % 256, 255, 255)
            canvas.clear()

            # Count out this screen's position down the middle, one dot for the first
            # screen that answered and two for the second
            canvas.pen = color.black
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
