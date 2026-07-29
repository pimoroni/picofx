# A spinny rainbow wheel, driven by the RGB444 reference driver.
#
# Same effect as examples/mighty_fx/examples/screens/color_wheel.py, but built on
# st7789_viper_rgb444 instead of MightyFX, so it shows what the driver needs and
# nothing else: an SPI peripheral, three pins, and a source image.
#
# It cycles every mode the driver supports, holding each for MODE_FRAMES frames
# and printing it, since a spinning wheel on its own does not tell you which one
# is active.
#
# Change the panel and PIN blocks to move this to another board.

from machine import SPI, Pin
from picovector import image, color, shape, mat3
from st7789_viper_rgb444 import ST7789_RGB444

# Panel and bus. 24MHz is the ceiling on a 48MHz clk_peri, since the PL022
# divider bottoms out at half the peripheral clock.
WIDTH = 240
HEIGHT = 320
FRAME_RATE = 42
BAUDRATE = 24_000_000
V_SYNC = True

# MightyFX SP/CE port A. On another board, put its numbers here.
SPI_ID = 0
SCK_PIN = 34
MOSI_PIN = 35
CS_PIN = 33
DC_PIN = 32
BL_PIN = 36

# Constants for drawing
INNER_RADIUS = 40
OUTER_RADIUS = 120
NUMBER_OF_LINES = 24
HUE_SHIFT = 4
ROTATION_SPEED = 2
LINE_THICKNESS = 2
BG_BRIGHTNESS = 60

# How long each mode is held for, in frames
MODE_FRAMES = 24

# Every combination the driver handles. Rotation changes fastest, so the four
# angles are seen together before mirroring or doubling changes.
MODES = [(rotation, mirror, pixel_double)
         for pixel_double in (False, True)
         for mirror in (False, True)
         for rotation in (0, 90, 180, 270)]

spi = SPI(id=SPI_ID, baudrate=BAUDRATE, sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN))
screen = ST7789_RGB444(spi, Pin(CS_PIN), Pin(DC_PIN), Pin(BL_PIN),
                      WIDTH, HEIGHT, FRAME_RATE)

# Create a canvas to draw to. Any object exposing the buffer protocol plus width
# and height works, so a picovector image is the convenient choice.
canvas = image(screen.width, screen.height)

# The area a rotated or doubled canvas does not cover, filled by the driver rather
# than drawn. Brighter than the quadrants below so it reads as outside the image.
# The driver takes a packed integer, which is a picovector colour's .p
BACKGROUND = color.hsv(0, 0, 100).p

# Four off-black quadrants behind the wheel. The wheel itself is symmetrical
# enough that a flip is hard to spot; these make every operation obvious, since
# each one moves the tints somewhere different. They cover the whole canvas, so
# there is no need to clear it first.
half_w = screen.width // 2
half_h = screen.height // 2
QUADRANTS = (
    (shape.rectangle(0, 0, half_w, half_h), color.hsv(0, 255, BG_BRIGHTNESS)),
    (shape.rectangle(half_w, 0, screen.width - half_w, half_h), color.hsv(85, 255, BG_BRIGHTNESS)),
    (shape.rectangle(0, half_h, half_w, screen.height - half_h), color.hsv(170, 255, BG_BRIGHTNESS)),
    (shape.rectangle(half_w, half_h, screen.width - half_w, screen.height - half_h), color.hsv(0, 0, BG_BRIGHTNESS)),
)

# Pre-calculate the screen centre
centre_x, centre_y = screen.width / 2, screen.height / 2

# Variables to keep track of rotation and hue positions
r = 0
t = 0

# Frame counter, and the mode last announced
frame = 0
announced = -1

# Create a line shape to use throughout the program
line = shape.line(INNER_RADIUS, 0,  # Start position (x, y)
                  0, OUTER_RADIUS,  # End position (x, y)
                  LINE_THICKNESS)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while True:
        # Pick the mode for this frame, and announce it when it changes
        index = (frame // MODE_FRAMES) % len(MODES)
        rotation, mirror, pixel_double = MODES[index]
        if index != announced:
            announced = index
            print(f"mode {index + 1}/{len(MODES)}: rotation={rotation}, "
                  f"mirror={mirror}, pixel_double={pixel_double}")

        # Lay down the quadrants, which also clears the previous frame
        for rectangle, pen in QUADRANTS:
            canvas.pen = pen
            canvas.shape(rectangle)

        # Go from 0 to 360 degrees, in equal divisions for the number of lines
        for i in range(0, 360, 360 // NUMBER_OF_LINES):
            # Calculate the colour hue of the line, giving full saturation and value
            hue = (i * 255) // 360
            canvas.pen = color.hsv((hue + t) % 256, 255, 255)

            # Rotate the line we originally create, and move it towards the screen centre
            line.transform = mat3().translate(centre_x, centre_y).rotate(i + r)

            # Apply the line with the current pen colour to the canvas
            canvas.shape(line)

        # Update the screen with the latest canvas. v_sync waits for the panel's
        # tearing effect signal, which this driver reads on the DC line.
        screen.update(canvas, rotation=rotation, mirror=mirror,
                      pixel_double=pixel_double, bg=BACKGROUND, v_sync=V_SYNC)

        # Advance both the rotation and the hue
        r += ROTATION_SPEED
        t += HUE_SHIFT
        frame += 1

# Turn the backlight off on the way out
finally:
    screen.BL.off()
