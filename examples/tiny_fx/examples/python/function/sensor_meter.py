from sensor import ANALOG
from timing import Pacer
from tiny_fx import TinyFX

"""
Use Tiny FX's mono outputs as a bargraph to show the voltage
measured from a sensor attached to the sensor connector.

The top output of the bar is lit as far into its step as the
reading has gone, so the bar moves smoothly.

Press "Boot" to exit the program.
"""

# Constants
BRIGHTNESS = 0.6    # The brightness to set the outputs
MIN_VOLTAGE = 0     # The min voltage, in volts, the sensor returns
MAX_VOLTAGE = 3.3   # The max voltage, in volts, the sensor returns
SAMPLES = 50        # The number of measurements to take per reading, to reduce noise
INTERVAL = 0.1      # How often to take a voltage measurement, in seconds

# Variables
tiny = TinyFX(sensor=ANALOG)            # Create a new TinyFX object, with an analog sensor on its connector

# Reading a sensor takes time of its own, so a pacer holds the readings to the interval
pacer = Pacer(INTERVAL)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not tiny.boot_pressed():
        # Read the voltage output by the sensor
        voltage = tiny.sensor.read_voltage(SAMPLES)

        # Print out the sensor value to a sensible number of decimal places
        print("Voltage =", round(voltage, 2))

        # Convert the voltage to a percentage of the min to max we want to show
        percent = (voltage - MIN_VOLTAGE) / (MAX_VOLTAGE - MIN_VOLTAGE)

        # How much of the bar the reading fills, in outputs
        filled = min(len(tiny.outputs), max(0.0, percent * len(tiny.outputs)))

        # Update all the outputs
        for i in range(len(tiny.outputs)):
            # Full below the top of the bar, part lit at the top, and out above it
            level = min(1.0, max(0.0, filled - i))
            tiny.outputs[i].brightness(BRIGHTNESS * level)

        pacer.hold()

# Turn off all the outputs
finally:
    tiny.shutdown()
