import time

from breakout_bme280 import BreakoutBME280
from tiny_fx import TinyFX

"""
Show the temperature on TinyFX's RGB output, read from a weather sensor on Qw/ST.

Plug a BME280 breakout into the Qw/ST connector. The board makes the bus itself, as
tiny.i2c, so the sensor takes that and nothing else needs setting up.

The colour runs from blue at the cold end of the range to red at the warm end. The
pressure and humidity the sensor also reports are printed.

Press "Boot" to exit the program.
"""

# Constants
BRIGHTNESS = 0.6    # The brightness to set the RGB output
MIN_TEMP = 15       # The temperature, in celsius, to show as fully cold
MAX_TEMP = 30       # The temperature, in celsius, to show as fully warm
COLD = (0, 0, 255)  # The colour to show at and below the min temperature
WARM = (255, 0, 0)  # The colour to show at and above the max temperature
SLEEP = 1.0         # The time to sleep between each sensor reading

# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
rgb = tiny.rgb                      # The board's RGB output
bme = BreakoutBME280(tiny.i2c)      # The weather sensor, on the board's Qw/ST bus


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

        # Mix the two ends of the range together in that proportion
        rgb.set_rgb(*((cold + (warm - cold) * percent) * BRIGHTNESS
                      for cold, warm in zip(COLD, WARM)))

        time.sleep(SLEEP)

# Turn off all the outputs
finally:
    tiny.shutdown()
