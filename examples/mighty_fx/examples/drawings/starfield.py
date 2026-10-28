import random
from picovector import color, shape

"""
Drawing: Starfield
Travel through a star field.
Section: Animation
"""

# Entry: screenA: graphics file=starfield.py fps=30

# Constants for drawing
NUMBER_OF_STARS = 50
TRAVEL_SPEED = 1.2
STAR_GROWTH = 0.12

# The canvas's size and centre, and the stars, set on the first call
width = height = centre_x = centre_y = None
stars = None


class RandomStar:
    def __init__(self):
        # A new star at a random position relative to the centre, and its starting size
        self.x = random.randint(0, width) - centre_x
        self.y = random.randint(0, height) - centre_y
        self.size = 0.5


def draw(canvas, _elapsed):
    global width, height, centre_x, centre_y, stars
    if stars is None:
        width, height = canvas.width, canvas.height
        centre_x, centre_y = width / 2, height / 2
        stars = [RandomStar() for _ in range(NUMBER_OF_STARS)]

    canvas.pen = color.black
    canvas.clear()

    canvas.pen = color.white
    for i in range(NUMBER_OF_STARS):
        s = stars[i]
        s.x *= TRAVEL_SPEED
        s.y *= TRAVEL_SPEED

        if s.x <= -centre_x or s.x >= centre_x or s.y <= -centre_y or s.y >= centre_y or s.size >= 5:
            s = RandomStar()

        s.size += STAR_GROWTH
        stars[i] = s

        canvas.shape(shape.circle(s.x + centre_x, s.y + centre_y, s.size))
