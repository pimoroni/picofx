import random
import sys
from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES, ScreenGroup
from picovector import image, color, shape

"""
Travel through a star field, across every panel a screen hub reaches.

Change up some of the constants below to see what happens.

Press "Boot" to exit the program.
"""

# Constants for drawing
NUMBER_OF_STARS = 50
TRAVEL_SPEED = 1.2
STAR_GROWTH = 0.12

# Which screen is on every hub position, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object driving a screen hub, which takes SP/CE port B for extra chip selects
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.HUB_SELECTS)

# Build a screen on every hub port and keep those that answer, as a hub need not be full
panels = []
for port in mighty.hub.ports:
    try:
        panels.append(ScreenType(port))
    except ValueError:
        pass

if not panels:
    # Release the hub first, as one of its chip selects is a panel's backlight pin
    mighty.shutdown()
    raise RuntimeError("No panels answered! Check the hub is plugged into SP/CE A, with its panels on the hub rather than on the board")

# A group draws one frame to every panel it holds, however many answered
wall = ScreenGroup(*panels)
print(f"{len(panels)} of {len(mighty.hub.ports)} hub positions answered")

# Access the first panel and create a canvas to draw to
canvas = image(panels[0].width, panels[0].height)

# Pre-calculate the panel centre
centre_x, centre_y = panels[0].width / 2, panels[0].height / 2


class RandomStar:
    def __init__(self):
        # A new star at a random position relative to the panel centre, and its starting size
        self.x = random.randint(0, panels[0].width) - centre_x
        self.y = random.randint(0, panels[0].height) - centre_y
        self.size = 0.5


stars = [RandomStar() for _ in range(NUMBER_OF_STARS)]

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Clear the canvas to black
        canvas.pen = color.black
        canvas.clear()

        canvas.pen = color.white
        for i in range(NUMBER_OF_STARS):
            # Load a star from the stars list
            s = stars[i]

            # Update x and y
            s.x *= TRAVEL_SPEED
            s.y *= TRAVEL_SPEED

            if s.x <= -centre_x or s.x >= centre_x or s.y <= -centre_y or s.y >= centre_y or s.size >= 5:
                # Replace a star that has left the panel or grown too big
                s = RandomStar()

            # Grow the star as it travels outward
            s.size += STAR_GROWTH

            # Save the updated star to the list
            stars[i] = s

            # Draw star, adding offsets to our relative coordinates to allow for (0, 0) being in the top left corner.
            circle = shape.circle(s.x + centre_x, s.y + centre_y, s.size)
            canvas.shape(circle)

        # Update every panel in the group with the latest canvas
        wall.update(canvas)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
