import time

from mighty_fx import MightyFX
from sensor import ANALOG

"""
Use MightyFX's RGB outputs as a bargraph to show the voltage measured from a sensor
attached to the sensor connector.

The output at the top of the bar is lit as far into its own step as the reading has
gone, so the bar moves smoothly rather than a whole output at a time. Each lights in the
colour its part of the range stands for, the hue running from
blue at the bottom, through green, to red at the top.

Press "Boot" to exit the program.
"""

# Constants
BRIGHTNESS = 0.6    # The brightness to set the outputs
MIN_VOLTAGE = 0     # The min voltage, in volts, the sensor returns
MAX_VOLTAGE = 3.3   # The max voltage, in volts, the sensor returns
SAMPLES = 50        # The number of measurements to take per reading, to reduce noise
SLEEP = 0.1         # The time to sleep between each voltage measurement
LOW_HUE = 0.666     # The hue of the lowest output, being blue
HIGH_HUE = 0.0      # The hue of the highest, coming back down the wheel to red

# Variables
mighty = MightyFX(sensor=ANALOG)    # Create a new MightyFX object, with an analog sensor on its connector


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Read the voltage output by the sensor
        voltage = mighty.sensor.read_voltage(SAMPLES)

        # Print out the sensor value to a sensible number of decimal places
        print("Voltage =", round(voltage, 2))

        # Convert the voltage to a percentage of the min to max we want to show
        percent = (voltage - MIN_VOLTAGE) / (MAX_VOLTAGE - MIN_VOLTAGE)

        # How much of the bar the reading fills, in outputs rather than as a fraction
        filled = min(len(mighty.outputs), max(0.0, percent * len(mighty.outputs)))

        # Update all the outputs
        for i in range(len(mighty.outputs)):
            # An output below the top of the bar is full, the one at the top is lit as
            # far into its own step as the reading has gone, and the rest are out
            level = min(1.0, max(0.0, filled - i))

            # The hue between the two ends carries the scale, so no table of colours is
            # needed and the ramp fits however many outputs a board has
            hue = LOW_HUE + (HIGH_HUE - LOW_HUE) * i / (len(mighty.outputs) - 1)
            mighty.outputs[i].set_hsv(hue, 1.0, BRIGHTNESS * level)

        time.sleep(SLEEP)

# Turn off all the outputs
finally:
    mighty.shutdown()
