from timing import Pacer
from tiny_fx import TinyFX

"""
Use TinyFX's mono outputs as a bargraph to show the voltage that is powering the board.

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


# Reading a sensor takes time of its own, so a pacer holds the readings to the
# interval rather than adding it to each one, as sleeping the whole interval would
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

        # Update all the outputs
        for i in range(len(tiny.outputs)):
            # Calculate the voltage level the output represents
            level = (i + 0.5) / len(tiny.outputs)

            # If the percent is above the level, turn the output on, otherwise turn it off
            tiny.outputs[i].brightness(BRIGHTNESS if percent >= level else 0)

        pacer.hold()

# Turn off all the outputs
finally:
    tiny.shutdown()
