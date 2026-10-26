from timing import Pacer
from tiny_fx import TinyFX

"""
Use TinyFX's mono outputs as a bargraph to show the voltage that is powering the board.

The top output of the bar is lit as far into its step as the reading has gone, so the bar
moves smoothly.

Press "Boot" to exit the program.
"""

# Constants
BRIGHTNESS = 0.6    # The brightness to set the outputs
MIN_VOLTAGE = 4     # The min voltage, in volts, to show on the meter
MAX_VOLTAGE = 6     # The max voltage, in volts, to show on the meter
SAMPLES = 50        # The number of measurements to take per reading, to reduce noise
INTERVAL = 0.1      # How often to take a voltage measurement, in seconds

# Variables
tiny = TinyFX()                         # Create a new TinyFX object to interact with the board


# Reading a sensor takes time of its own, so a pacer holds the readings to the interval
pacer = Pacer(INTERVAL)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not tiny.boot_pressed():
        # Read the voltage powering the board
        voltage = tiny.read_voltage(SAMPLES)

        # Print out the voltage sense value to a sensible number of decimal places
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
