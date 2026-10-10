import time

from timing import Pacer
from breakout_bme280 import BreakoutBME280
from tiny_fx import TinyFX

"""
Show the temperature on TinyFX's RGB output, read from a weather sensor on Qw/ST.

Plug a BME280 breakout into the Qw/ST connector. The board makes the bus itself, as
tiny.i2c, so the sensor takes that and nothing else needs setting up.

The colour runs from blue at the cold end of the range, through purple, to red at the
warm end. The
pressure and humidity the sensor also reports are printed.

Press "Boot" to exit the program.
"""

# Constants
BRIGHTNESS = 0.6    # The brightness to set the RGB output
MIN_TEMP = 15       # The temperature, in celsius, to show as fully cold
MAX_TEMP = 30       # The temperature, in celsius, to show as fully warm
COLD_HUE = 0.666    # The hue shown at and below the min temperature, being blue
WARM_HUE = 1.0      # The hue shown at and above the max, being red again at the top of the wheel
INTERVAL = 1.0      # How often to take a sensor reading, in seconds
SETTLE = 0.1        # The time to give the sensor to make its first measurement

# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
rgb = tiny.rgb                      # The board's RGB output
bme = BreakoutBME280(tiny.i2c)      # The weather sensor, on the board's Qw/ST bus

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
    while not tiny.boot_pressed():
        temperature, pressure, humidity = bme.read()

        # Print out the readings to a sensible number of decimal places
        print("Temperature =", round(temperature, 1), "C,",
              "Pressure =", round(pressure / 100, 1), "hPa,",
              "Humidity =", round(humidity, 1), "%")

        # Convert the temperature to a percentage of the min to max we want to show,
        # kept within the range so a colder or warmer room still gives a colour
        percent = (temperature - MIN_TEMP) / (MAX_TEMP - MIN_TEMP)
        percent = min(1.0, max(0.0, percent))

        # The hue between the two ends carries the scale, running blue through purple
        # to red, so no mixing of colours is needed to cross it
        rgb.set_hsv(COLD_HUE + (WARM_HUE - COLD_HUE) * percent, 1.0, BRIGHTNESS)

        pacer.hold()

# Turn off all the outputs
finally:
    tiny.shutdown()
