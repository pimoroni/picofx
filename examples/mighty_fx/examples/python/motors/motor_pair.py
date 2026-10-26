import math
import time
from mighty_fx import MightyFX, SPCE

"""
Sweep a pair of motors up and down their speed range together, on a SP/CE port
spent on a motor driver.

Both motors are given the same speed following a sine, so each cycle runs from a stop to
full forward, back through a stop to full reverse, and round again.

Press "Boot" to exit the program.
"""

# Constants
SPEED_EXTENT = 1.0      # How far from zero to drive the motors when sweeping

mighty = MightyFX(spce_a=SPCE.MOTOR_DRIVER)

driver = mighty.spce_a.driver   # The driver on port A, and the two motors it holds
i = 0

driver.enable()             # Power it, which the board leaves off until asked

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        speed = math.sin(math.radians(i)) * SPEED_EXTENT
        for motor in driver.motors:
            motor.speed(speed)
        i = (i + 1) % 360
        time.sleep(0.02)

# Stop the motors and turn off all the outputs
finally:
    mighty.shutdown()
