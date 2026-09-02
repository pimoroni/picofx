import time

from timing import Pacer
from lsm6ds3 import LSM6DS3
from mighty_fx import MightyFX

"""
Use MightyFX's RGB outputs as a spirit level, read from an accelerometer on Qw/ST.

Plug a multi sensor stick, or another LSM6DS3 breakout, into the Qw/ST connector. The
board makes the bus itself, as mighty.i2c, so the sensor takes that and nothing else
needs setting up.

A board lying flat has gravity pulling straight down through it, and tilting it moves
some of that pull sideways. That sideways part is what places the bubble: it sits on
the middle output when level and travels towards whichever side is lower, spreading
across two outputs as it passes between them so it slides rather than hops.

The bubble is green while the board is level and reddens as it tilts, so a glance says
both where it is and how far off it is. Rest the board on something and lift one edge.

Which way to tilt it is set by AXIS, and readings are smoothed on the way in: a bubble
spread across two outputs shows every fraction of a degree the sensor wobbles by.

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
mighty = MightyFX()             # Create a new MightyFX object to interact with the board
imu = LSM6DS3(mighty.i2c)       # The accelerometer, on the board's Qw/ST bus
middle = (len(mighty.outputs) - 1) / 2

# The sensor answers with the values its registers hold from reset until it has made a
# measurement of its own, so one reading is taken and thrown away
imu.get_readings()
time.sleep(SETTLE)

# What the bubble is placed by. A single reading jitters by a fraction of a degree,
# which a bubble spread across two outputs shows plainly, so each new one is mixed into
# what was there rather than replacing it
smoothed = imu.get_readings()[AXIS] / ONE_G


# Reading a sensor takes time of its own, so a pacer holds the readings to the
# interval rather than adding it to each one, as sleeping the whole interval would
pacer = Pacer(INTERVAL)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The first three readings are the acceleration along each axis, and gravity is
        # what tilting moves between them
        sideways = imu.get_readings()[AXIS] / ONE_G
        smoothed += (sideways - smoothed) * SMOOTHING

        # Where the bubble sits, from the first output to the last, with the middle
        # one being level
        tilt = min(1.0, max(-1.0, smoothed / TILT_EXTENT))
        position = middle + tilt * middle

        # Level is green and either end is red, so how far off it is reads as colour
        hue = LEVEL_HUE + (TILTED_HUE - LEVEL_HUE) * abs(tilt)

        # Each output lights by how near the bubble is to it, so the bubble spreads
        # across two as it passes between them rather than stepping from one to the next
        for i, output in enumerate(mighty.outputs):
            nearness = max(0.0, 1.0 - abs(position - i))
            output.set_hsv(hue, 1.0, BRIGHTNESS * nearness)

        pacer.hold()

# Turn off all the outputs
finally:
    mighty.shutdown()
