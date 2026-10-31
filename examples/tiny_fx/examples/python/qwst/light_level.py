from breakout_ltr559 import BreakoutLTR559
from timing import Pacer
from tiny_fx import TinyFX

from picofx import MonoPlayer
from picofx.mono import FlickerFX

"""
Bring Tiny FX's lights up when the room gets dark, read from a light sensor on Qw/ST.

Plug an LTR559 breakout into the Qw/ST connector, which the board sets up as tiny.i2c.

The lamps come on below LUX_LOW and go off above LUX_HIGH, so a reading that sits near one
level does not switch them back and forth.

Press "Boot" to exit the program.
"""

# Constants
LUX_LOW = 60        # The light level, in Lux, below which the lamps come on
LUX_HIGH = 70       # The light level, in Lux, above which they go off again
INTERVAL = 0.1      # How often to take a light measurement, in seconds
LTR559_ADDRESS = 0x23   # The sensor's address on the bus, which is fixed

# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)   # Create a new effect player to control Tiny FX's mono outputs

# Check if the sensor answers on the bus, since a missing one raises nothing
if LTR559_ADDRESS not in tiny.i2c.scan():
    raise RuntimeError("No LTR559 found on Qw/ST. Plug in a multi sensor stick or another LTR559 breakout")
ltr = BreakoutLTR559(tiny.i2c)      # The light sensor, on the board's Qw/ST bus

# The first reading holds whatever the sensor had before measuring, so it is thrown away
ltr.get_reading()


# Set up a flicker effect to play on every output, so the lamps are never quite steady
player.effects = [FlickerFX() for _ in tiny.outputs]


# Reading a sensor takes time of its own, so a pacer holds the readings to the interval
pacer = Pacer(INTERVAL)

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

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    player.stop()
    tiny.shutdown()
