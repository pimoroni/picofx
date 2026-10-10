import time

from timing import Pacer
from breakout_bme280 import BreakoutBME280
from mighty_fx import MightyFX

"""
Show the temperature on MightyFX's RGB outputs as a bargraph, read from a weather
sensor on Qw/ST.

Plug a BME280 breakout into the Qw/ST connector. The board makes the bus itself, as
mighty.i2c, so the sensor takes that and nothing else needs setting up.

The bar fills from the cold end to the warm one, each output lit in the colour its own
part of the range stands for, the hue running blue through purple to red. The output at the top
of the bar is lit as far into its own step as the reading has gone, so the bar moves
smoothly rather than a whole output at a time. Hold the sensor between your fingers to
watch it climb. The pressure and
humidity the sensor also reports are printed.

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
mighty = MightyFX()                 # Create a new MightyFX object to interact with the board
bme = BreakoutBME280(mighty.i2c)    # The weather sensor, on the board's Qw/ST bus

# The sensor answers with the values its registers hold from reset until it has made a
# measurement of its own, and reading again does not hurry it. So one read starts it
# measuring, and the wait is what the reading after it needs to be real
bme.read()
time.sleep(SETTLE)


# Reading a sensor takes time of its own, so a pacer holds the readings to the
# interval rather than adding it to each one, as sleeping the whole interval would
pacer = Pacer(INTERVAL)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        temperature, pressure, humidity = bme.read()

        # Print out the readings to a sensible number of decimal places
        print("Temperature =", round(temperature, 1), "C,",
              "Pressure =", round(pressure / 100, 1), "hPa,",
              "Humidity =", round(humidity, 1), "%")

        # How much of the bar the reading fills, in outputs rather than as a fraction
        percent = (temperature - MIN_TEMP) / (MAX_TEMP - MIN_TEMP)
        filled = min(len(mighty.outputs), max(0.0, percent * len(mighty.outputs)))

        # Update all the outputs
        for i in range(len(mighty.outputs)):
            # An output below the top of the bar is full, the one at the top is lit as
            # far into its own step as the reading has gone, and the rest are out
            level = min(1.0, max(0.0, filled - i))

            # The hue between the two ends carries the scale, so no table of colours
            # is needed and the ramp fits however many outputs a board has
            hue = COLD_HUE + (WARM_HUE - COLD_HUE) * i / (len(mighty.outputs) - 1)
            mighty.outputs[i].set_hsv(hue, 1.0, BRIGHTNESS * level)

        pacer.hold()

# Turn off all the outputs
finally:
    mighty.shutdown()
