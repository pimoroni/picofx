from picovector import color, mat3, shape

"""
Drawing: Colour wheel
A spinning rainbow wheel.
Section: Animation
"""

# Entry: screenA: graphics file=color_wheel.py

# Constants for drawing
INNER_RADIUS = 40
OUTER_RADIUS = 120
NUMBER_OF_LINES = 24
HUE_SHIFT = 4
ROTATION_SPEED = 2
LINE_THICKNESS = 2

# Rotation and hue positions, advanced a step a call
r = 0
t = 0

# The canvas's centre, set on the first call
centre_x = centre_y = None

line = shape.line(INNER_RADIUS, 0,
                  0, OUTER_RADIUS,
                  LINE_THICKNESS)


def draw(canvas, _elapsed):
    global r, t, centre_x, centre_y
    if centre_x is None:
        centre_x, centre_y = canvas.width / 2, canvas.height / 2

    canvas.pen = color.black
    canvas.clear()

    for i in range(0, 360, 360 // NUMBER_OF_LINES):
        hue = (i * 255) // 360
        canvas.pen = color.hsv((hue + t) % 256, 255, 255)
        line.transform = mat3().translate(centre_x, centre_y).rotate(i + r)
        canvas.shape(line)

    r += ROTATION_SPEED
    t += HUE_SHIFT
