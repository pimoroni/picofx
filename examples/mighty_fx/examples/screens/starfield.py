# A spinny rainbow wheel. Change up some of the constants below to see what happens.

import random
from mighty_fx import MightyFX, SPCE

# Constants for drawing
NUMBER_OF_STARS = 200
TRAVEL_SPEED = 1.2
STAR_GROWTH = 0.12

mighty = MightyFX(spce_a=SPCE.SCREEN_280)

screen = mighty.screen_a
WIDTH, HEIGHT = screen.get_bounds()

BLACK = screen.create_pen(0, 0, 0)
WHITE = screen.create_pen(255, 255, 255)


def new_star():
    # Create a new star, with initial x, y, and size
    # Initial x will fall between -WIDTH / 2 and +WIDTH / 2 and y between -HEIGHT/2 and +HEIGHT/2
    # These are relative values for now, treating (0, 0) as the centre of the screen.
    return [random.randint(0, WIDTH) - WIDTH // 2, random.randint(0, HEIGHT) - HEIGHT // 2, 0.5]


stars = [new_star() for _ in range(NUMBER_OF_STARS)]

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while True:
        screen.set_pen(BLACK)
        screen.clear()
        screen.set_pen(WHITE)
        for i in range(NUMBER_OF_STARS):
            # Load a star from the stars list
            s = stars[i]

            # Update x
            s[0] = s[0] * TRAVEL_SPEED

            # Update y
            s[1] = s[1] * TRAVEL_SPEED

            if s[0] <= - WIDTH // 2 or s[0] >= WIDTH // 2 or s[1] <= - HEIGHT // 2 or s[1] >= HEIGHT // 2 or s[2] >= 5:
                # This star has fallen off the screen (or rolled dead centre and grown too big!)
                # Replace it with a new one
                s = new_star()

            # Grow the star as it travels outward
            s[2] += STAR_GROWTH

            # Save the updated star to the list
            stars[i] = s

            # Draw star, adding offsets to our relative coordinates to allow for (0, 0) being in the top left corner.
            screen.circle(int(s[0]) + WIDTH // 2, int(s[1]) + HEIGHT // 2, int(s[2]))

        screen.update()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
