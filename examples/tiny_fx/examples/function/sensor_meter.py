import time
from tiny_fx import TinyFX
from machine import Pin
from pimoroni import Analog

"""
Use TinyFX's mono outputs as a bargraph to show the voltage
measured from a sensor attached to the sensor connector.

Press "Boot" to exit the program.
"""

# Constants
BRIGHTNESS = 0.6    # The brightness to set the outputs
MIN_VOLTAGE = 0     # The min voltage, in volts, the sensor returns
MAX_VOLTAGE = 3.3   # The max voltage, in volts, the sensor returns
SAMPLES = 50        # The number of measurements to take per reading, to reduce noise
SLEEP = 0.1         # The time to sleep between each voltage measurement

# Variables
tiny = TinyFX()                         # Create a new TinyFX object to interact with the board
sensor = Analog(Pin(tiny.SENSOR_PIN))   # Create a new Analog object for reading the sensor connector

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not tiny.boot_pressed():
        # Read the voltage output by the sensor
        voltage = sensor.read_voltage(SAMPLES)

        # Print out the sensor value to a sensible number of decimal places
        print("Voltage =", round(voltage, 2))

        # Convert the voltage to a percentage of the min to max we want to show
        percent = (voltage - MIN_VOLTAGE) / (MAX_VOLTAGE - MIN_VOLTAGE)

        # Update all the outputs
        for i in range(len(tiny.outputs)):
            # Calculate the voltage level the output represents
            level = (i + 0.5) / len(tiny.outputs)

            # If the percent is above the level, turn the output on, otherwise turn it off
            tiny.outputs[i].brightness(BRIGHTNESS if percent >= level else 0)

        time.sleep(SLEEP)

# Turn off all the outputs
finally:
    tiny.shutdown()
