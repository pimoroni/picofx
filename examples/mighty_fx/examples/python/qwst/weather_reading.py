import time

from breakout_bme280 import BreakoutBME280
from mighty_fx import MightyFX
from timing import Pacer

"""
Show the temperature on Mighty FX's RGB outputs as a bargraph, read from a weather
sensor on Qw/ST.

Plug a BME280 breakout into the Qw/ST connector, which the board sets up as mighty.i2c.

The bar fills from blue at the cold end through purple to red at the warm one, its top
output lit part way so the bar moves smoothly. Hold the sensor between your fingers to watch
it climb. Pressure and humidity are printed too.

Press "Boot" to exit the program.
"""

# Constants
BRIGHTNESS = 0.6    # The brightness to set the outputs
MIN_TEMP = 18       # The temperature, in celsius, the bar starts at
MAX_TEMP = 30       # The temperature, in celsius, the bar is full at
INTERVAL = 0.5      # How often to take a sensor reading, in seconds
SETTLE = 0.1        # The time to give the sensor to make its first measurement
COLD_HUE = 0.666    # The hue of the coldest output, being blue
WARM_HUE = 1.0      # The hue of the warmest, being red again at the top of the wheel

# Variables
mighty = MightyFX()                     # Create a new MightyFX object to interact with the board
try:
    bme = BreakoutBME280(mighty.i2c)    # The weather sensor, on the board's Qw/ST bus
except RuntimeError:
    raise RuntimeError("No BME280 found on Qw/ST. Plug in a multi sensor stick or another BME280 breakout") from None

# The sensor reports its reset values until it has measured and reading again does not
# hurry it, so one read starts it and the wait lets that measurement finish
bme.read()
time.sleep(SETTLE)


# Reading a sensor takes time of its own, so a pacer holds the readings to the interval
pacer = Pacer(INTERVAL)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        temperature, pressure, humidity = bme.read()

        # Print out the readings to a sensible number of decimal places
        print("Temperature =", round(temperature, 1), "C,",
              "Pressure =", round(pressure / 100, 1), "hPa,",
              "Humidity =", round(humidity, 1), "%")

        # How much of the bar the reading fills, in outputs
        percent = (temperature - MIN_TEMP) / (MAX_TEMP - MIN_TEMP)
        filled = min(len(mighty.outputs), max(0.0, percent * len(mighty.outputs)))

        # Update all the outputs
        for i in range(len(mighty.outputs)):
            # Full below the top of the bar, part lit at the top, and out above it
            level = min(1.0, max(0.0, filled - i))

            # Spread the hue between the two ends, so the ramp fits any number of outputs
            hue = COLD_HUE + (WARM_HUE - COLD_HUE) * i / (len(mighty.outputs) - 1)
            mighty.outputs[i].set_hsv(hue, 1.0, BRIGHTNESS * level)

        pacer.hold()

# Turn off all the outputs
finally:
    mighty.shutdown()
