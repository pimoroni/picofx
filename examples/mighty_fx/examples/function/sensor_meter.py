import time

from mighty_fx import MightyFX
from sensor import ANALOG

"""
Use MightyFX's RGB outputs as a bargraph to show the voltage measured from a sensor
attached to the sensor connector.

Each output lights in the colour its part of the range stands for, so the bar runs
from blue at the bottom, through green, to red at the top.

Press "Boot" to exit the program.
"""

# Constants
BRIGHTNESS = 0.6    # The brightness to set the outputs
MIN_VOLTAGE = 0     # The min voltage, in volts, the sensor returns
MAX_VOLTAGE = 3.3   # The max voltage, in volts, the sensor returns
SAMPLES = 50        # The number of measurements to take per reading, to reduce noise
SLEEP = 0.1         # The time to sleep between each voltage measurement
COLOURS = (
    (0, 0, 255),    # The colour each output lights in, lowest reading first
    (0, 120, 255),
    (0, 255, 200),
    (0, 255, 0),
    (200, 255, 0),
    (255, 120, 0),
    (255, 0, 0),
)

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

        # Update all the outputs
        for i in range(len(mighty.outputs)):
            # Calculate the voltage level the output represents
            level = (i + 0.5) / len(mighty.outputs)

            # If the percent is above the level, light the output in its colour, otherwise turn it off
            if percent >= level:
                mighty.outputs[i].set_rgb(*(c * BRIGHTNESS for c in COLOURS[i]))
            else:
                mighty.outputs[i].off()

        time.sleep(SLEEP)

# Turn off all the outputs
finally:
    mighty.shutdown()
