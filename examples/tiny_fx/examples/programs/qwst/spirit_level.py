import time

from lsm6ds3 import LSM6DS3
from timing import Pacer
from tiny_fx import TinyFX

"""
Use Tiny FX's mono outputs as a spirit level, read from an accelerometer on Qw/ST.

Plug a multi sensor stick or another LSM6DS3 breakout into the Qw/ST connector, which
the board sets up as tiny.i2c.

The bubble moves towards the lower side, spread across two outputs as it passes between
them.

Six outputs have no middle one, so a level board lights the middle two equally. The RGB
output shows how far off level it is, green when level and redder as it tilts. Rest the
board on something and lift one edge.

Press "Boot" to exit the program.
"""

# Constants
ACROSS, ALONG, THROUGH = 0, 1, 2    # The three axes the sensor measures

AXIS = ALONG        # Which way of tilting the board moves the bubble
SMOOTHING = 0.2     # How much of each reading is taken, the rest being what was there
BRIGHTNESS = 0.8    # The brightness to set the outputs
TILT_EXTENT = 0.5   # The sideways pull, as a fraction of gravity, that reaches the end
LEVEL_HUE = 0.333   # The hue of a level board, being green
TILTED_HUE = 0.0    # The hue at the ends of the travel, being red
ONE_G = 16384       # What the sensor reads for gravity alone, at its default scale
INTERVAL = 0.02     # How often to take a reading, in seconds
SETTLE = 0.1        # The time to give the sensor to make its first measurement

# Variables
tiny = TinyFX()                 # Create a new TinyFX object to interact with the board
try:
    imu = LSM6DS3(tiny.i2c)     # The accelerometer, on the board's Qw/ST bus
except OSError:
    raise RuntimeError("No LSM6DS3 found on Qw/ST. Plug in a multi sensor stick or another LSM6DS3 breakout") from None
middle = (len(tiny.outputs) - 1) / 2

# The sensor answers with the values its registers hold from reset until it has made a
# measurement of its own, so one reading is taken and thrown away
imu.get_readings()
time.sleep(SETTLE)

# What places the bubble. Each reading is mixed into the last, since a bubble spread across
# two outputs shows every fraction of a degree the sensor jitters by
smoothed = imu.get_readings()[AXIS] / ONE_G


# Reading a sensor takes time of its own, so a pacer holds the readings to the interval
pacer = Pacer(INTERVAL)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not tiny.boot_pressed():
        # The first three readings are the acceleration along each axis, and gravity is
        # what tilting moves between them
        sideways = imu.get_readings()[AXIS] / ONE_G
        smoothed += (sideways - smoothed) * SMOOTHING

        # Where the bubble sits from the first output to the last, level between the middle two
        tilt = min(1.0, max(-1.0, smoothed / TILT_EXTENT))
        position = middle + tilt * middle

        # Each output lights by how near the bubble is, so it spreads across two between them
        for i, output in enumerate(tiny.outputs):
            nearness = max(0.0, 1.0 - abs(position - i))
            output.brightness(BRIGHTNESS * nearness)

        # The RGB output shows how far off level it is, which the mono outputs cannot
        tiny.rgb.set_hsv(LEVEL_HUE + (TILTED_HUE - LEVEL_HUE) * abs(tilt), 1.0, BRIGHTNESS)

        pacer.hold()

# Turn off all the outputs
finally:
    tiny.shutdown()
