# A spinny rainbow wheel. Change up some of the constants below to see what happens.

import math
import random
from mighty_fx import MightyFX, SPCE


class ColourWheel:
    # Constants for drawing
    INNER_RADIUS = 40
    OUTER_RADIUS = 120
    NUMBER_OF_LINES = 24
    HUE_SHIFT = 0.02
    ROTATION_SPEED = 2
    LINE_THICKNESS = 2

    def __init__(self, screen):
        self.screen = screen
        self.BLACK = screen.create_pen(0, 0, 0)
        self.WIDTH, self.HEIGHT = screen.get_bounds()
        self.r = 0
        self.t = 0

    def draw(self):
        self.screen.set_pen(self.BLACK)
        self.screen.clear()
        for i in range(0, 360, 360 // self.NUMBER_OF_LINES):
            self.screen.set_pen(self.screen.create_pen_hsv((i / 360) + self.t, 1.0, 1.0))

            # Draw some lines, offset by the rotation variable
            self.screen.line(int(self.WIDTH / 2 + math.cos(math.radians(i + self.r)) * self.INNER_RADIUS),
                             int(self.HEIGHT / 2 + math.sin(math.radians(i + self.r)) * self.INNER_RADIUS),
                             int(self.WIDTH / 2 + math.cos(math.radians(i + 90 + self.r)) * self.OUTER_RADIUS),
                             int(self.HEIGHT / 2 + math.sin(math.radians(i + 90 + self.r)) * self.OUTER_RADIUS),
                             self.LINE_THICKNESS)

    def update(self):
        self.screen.update()
        self.r += self.ROTATION_SPEED
        self.t += self.HUE_SHIFT


class Starfield:
    # Constants for drawing
    NUMBER_OF_STARS = 200
    TRAVEL_SPEED = 1.2
    STAR_GROWTH = 0.12

    def __init__(self, screen):
        self.screen = screen
        self.BLACK = screen.create_pen(0, 0, 0)
        self.WHITE = screen.create_pen(255, 255, 255)
        self.WIDTH, self.HEIGHT = screen.get_bounds()
        self.stars = [self.new_star() for _ in range(self.NUMBER_OF_STARS)]

    def new_star(self):
        # Create a new star, with initial x, y, and size
        # Initial x will fall between -WIDTH / 2 and +WIDTH / 2 and y between -HEIGHT/2 and +HEIGHT/2
        # These are relative values for now, treating (0, 0) as the centre of the screen.
        return [random.randint(0, self.WIDTH) - self.WIDTH // 2, random.randint(0, self.HEIGHT) - self.HEIGHT // 2, 0.5]

    def draw(self):
        self.screen.set_pen(self.BLACK)
        self.screen.clear()
        self.screen.set_pen(self.WHITE)
        for i in range(self.NUMBER_OF_STARS):
            # Load a star from the stars list
            s = self.stars[i]

            # Update x
            s[0] = s[0] * self.TRAVEL_SPEED

            # Update y
            s[1] = s[1] * self.TRAVEL_SPEED

            if s[0] <= - self.WIDTH // 2 or s[0] >= self.WIDTH // 2 or s[1] <= - self.HEIGHT // 2 or s[1] >= self.HEIGHT // 2 or s[2] >= 5:
                # This star has fallen off the screen (or rolled dead centre and grown too big!)
                # Replace it with a new one
                s = self.new_star()

            # Grow the star as it travels outward
            s[2] += self.STAR_GROWTH

            # Save the updated star to the list
            self.stars[i] = s

            # Draw star, adding offsets to our relative coordinates to allow for (0, 0) being in the top left corner.
            self.screen.circle(int(s[0]) + self.WIDTH // 2, int(s[1]) + self.HEIGHT // 2, int(s[2]))

    def update(self):
        self.screen.update()


mighty = MightyFX(spce_a=SPCE.SCREEN_154, spce_b=SPCE.SCREEN_154)
scenes = [ColourWheel(mighty.screen_a), Starfield(mighty.screen_b)]

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while True:
        for scene in scenes:
            scene.draw()

        for scene in scenes:
            scene.update()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
