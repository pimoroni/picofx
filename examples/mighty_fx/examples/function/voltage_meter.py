import time

from mighty_fx import MightyFX

"""
Use MightyFX's RGB outputs as a bargraph to show the voltage that is powering the board.

Each output lights in the colour its part of the range stands for, so the bar runs from
red at the bottom, through amber, to green at the top.

Press "Boot" to exit the program.
"""

# Constants
BRIGHTNESS = 0.6            # The brightness to set the outputs
MIN_VOLTAGE = 4             # The min voltage, in volts, to show on the meter
MAX_VOLTAGE = 6             # The max voltage, in volts, to show on the meter
SAMPLES = 50                # The number of measurements to take per reading, to reduce noise
SLEEP = 0.1                 # The time to sleep between each voltage measurement
COLOURS = (
    (255, 0, 0),            # The colour each output lights in, lowest voltage first
    (255, 60, 0),
    (255, 120, 0),
    (255, 200, 0),
    (200, 255, 0),
    (100, 255, 0),
    (0, 255, 0),
)

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
