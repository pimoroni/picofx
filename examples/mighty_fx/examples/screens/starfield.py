# Travelling through a star field. Change up some of the constants below to see what happens.

import random
from mighty_fx import MightyFX, SPCE
from picovector import image, color, shape

# Constants for drawing
NUMBER_OF_STARS = 50
TRAVEL_SPEED = 1.2
STAR_GROWTH = 0.12

# Create a MightyFX object with a screen set on SP/CE port A
mighty = MightyFX(spce_a=SPCE.SCREEN_280)
screen = mighty.screen_a

# Access the screen and create a canvas to draw to
canvas = image(screen.width, screen.height)

# Pre-calculate the screen centre
centre_x, centre_y = screen.width / 2, screen.height / 2


class RandomStar:
    def __init__(self):
        # Create a new star, with initial x, y, and size
        # Initial x will fall between -WIDTH / 2 and +WIDTH / 2 and y between -HEIGHT/2 and +HEIGHT/2
        # These are relative values for now, treating (0, 0) as the centre of the screen
        self.x = random.randint(0, screen.height) - centre_x
        self.y = random.randint(0, screen.height) - centre_y
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
                # This star has fallen off the screen (or rolled dead centre and grown too big!)
                # Replace it with a new one
                s = RandomStar()

            # Grow the star as it travels outward
            s.size += STAR_GROWTH

            # Save the updated star to the list
            stars[i] = s

            # Draw star, adding offsets to our relative coordinates to allow for (0, 0) being in the top left corner.
            circle = shape.circle(s.x + centre_x, s.y + centre_y, s.size)
            canvas.shape(circle)

        # Update the screen with the latest canvas
        screen.update(canvas)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
