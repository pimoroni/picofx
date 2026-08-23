import time

from breakout_ltr559 import BreakoutLTR559
from mighty_fx import MightyFX

from picofx import ColourPlayer
from picofx.mono import FlickerFX

"""
Bring MightyFX's lights up when the room gets dark, read from a light sensor on Qw/ST.

Plug an LTR559 breakout into the Qw/ST connector. The board makes the bus itself, as
mighty.i2c, so the sensor takes that and nothing else needs setting up.

The two thresholds are apart on purpose. A single one has the lamps switching back and
forth whenever the reading sits on it, so the level that turns them on is lower than
the level that turns them off.

Press "Boot" to exit the program.
"""

# Constants
LAMP_COLOUR = (255, 170, 80)    # The warm colour the lamps light in
LUX_LOW = 60                    # The light level, in Lux, below which the lamps come on
LUX_HIGH = 70                   # The light level, in Lux, above which they go off again
SLEEP = 0.1                     # The time to sleep between each light measurement

# Variables
mighty = MightyFX()                     # Create a new MightyFX object to interact with the board
player = ColourPlayer(mighty.outputs)   # Create a new effect player to control MightyFX's RGB outputs
ltr = BreakoutLTR559(mighty.i2c)        # The light sensor, on the board's Qw/ST bus


# The colour each output draws its light in. A flicker gives a level rather than a
# colour, so the colour comes from here
player.colours = LAMP_COLOUR


# Set up a flicker effect to play on every output, so the lamps are never quite steady
player.effects = [FlickerFX() for _ in mighty.outputs]


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        reading = ltr.get_reading()

        # The sensor has nothing new to give between its own measurements
        if reading is not None:
            lux = reading[BreakoutLTR559.LUX]
            print("Light level =", lux, "Lux")

            if lux < LUX_LOW:
                player.start()
            elif lux > LUX_HIGH:
                player.stop()
                mighty.clear()

        time.sleep(SLEEP)

# Stop any running effects and turn off all the outputs
finally:
    player.stop()
    mighty.shutdown()
