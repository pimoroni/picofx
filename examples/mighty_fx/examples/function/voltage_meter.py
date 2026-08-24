import time

from mighty_fx import MightyFX

"""
Use MightyFX's RGB outputs as a bargraph to show the voltage that is powering the board.

The output at the top of the bar is lit as far into its own step as the reading has
gone, so the bar moves smoothly rather than a whole output at a time. Each lights in the
colour its part of the range stands for, the hue running from
red at the bottom, through amber, to green at the top.

Press "Boot" to exit the program.
"""

# Constants
BRIGHTNESS = 0.6            # The brightness to set the outputs
MIN_VOLTAGE = 4             # The min voltage, in volts, to show on the meter
MAX_VOLTAGE = 6             # The max voltage, in volts, to show on the meter
SAMPLES = 50                # The number of measurements to take per reading, to reduce noise
SLEEP = 0.1                 # The time to sleep between each voltage measurement
LOW_HUE = 0.0           # The hue of the lowest output, being red
HIGH_HUE = 0.333        # The hue of the highest, being green by way of amber

# Variables
mighty = MightyFX()         # Create a new MightyFX object to interact with the board


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Read the voltage powering the board
        voltage = mighty.read_voltage(SAMPLES)

        # Print out the voltage sense value to a sensible number of decimal places
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
