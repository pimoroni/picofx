import time

from breakout_ltr559 import BreakoutLTR559
from tiny_fx import TinyFX

from picofx import MonoPlayer
from picofx.mono import FlickerFX

"""
Bring TinyFX's lights up when the room gets dark, read from a light sensor on Qw/ST.

Plug an LTR559 breakout into the Qw/ST connector. The board makes the bus itself, as
tiny.i2c, so the sensor takes that and nothing else needs setting up.

The two thresholds are apart on purpose. A single one has the lamps switching back and
forth whenever the reading sits on it, so the level that turns them on is lower than
the level that turns them off.

Press "Boot" to exit the program.
"""

# Constants
LUX_LOW = 60        # The light level, in Lux, below which the lamps come on
LUX_HIGH = 70       # The light level, in Lux, above which they go off again
SLEEP = 0.1         # The time to sleep between each light measurement

# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)   # Create a new effect player to control TinyFX's mono outputs
ltr = BreakoutLTR559(tiny.i2c)      # The light sensor, on the board's Qw/ST bus

# The sensor's first reading is whatever it held before it was asked to measure, so it
# is taken and thrown away rather than acted on
ltr.get_reading()


# Set up a flicker effect to play on every output, so the lamps are never quite steady
player.effects = [FlickerFX() for _ in tiny.outputs]


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not tiny.boot_pressed():
        reading = ltr.get_reading()

        # The sensor has nothing new to give between its own measurements
        if reading is not None:
            lux = reading[BreakoutLTR559.LUX]
            print("Light level =", lux, "Lux")

            if lux < LUX_LOW:
                player.start()
            elif lux > LUX_HIGH:
                player.stop()
                tiny.clear()

        time.sleep(SLEEP)

# Stop any running effects and turn off all the outputs
finally:
    player.stop()
    tiny.shutdown()
