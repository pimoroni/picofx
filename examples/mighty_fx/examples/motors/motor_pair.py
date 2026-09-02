import math
import time
from mighty_fx import MightyFX, SPCE
from motor_driver import MotorDriver

"""
Sweep a pair of motors up and down their speed range together, on an SP/CE connector
declared as a motor driver.

A connector declared that way hands back a driver, holding the two motors its data pins
reach and the power they share. Both are given the same speed here, following a sine, so a
cycle runs from a stop out to full forward, back through a stop to full reverse, and round
again.

The driver comes up unpowered, so nothing wired to it moves until enable() is called.

Press "Boot" to exit the program.
"""

# Constants
SPEED_EXTENT = 1.0      # How far from zero to drive the motors when sweeping

mighty = MightyFX(spce_a=SPCE.MOTOR_DRIVER)

driver = MotorDriver(mighty.spce_a)    # The driver on the A connector, and the two motors it holds
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

# Stop the motors, take the driver's power away and turn off all the outputs
finally:
    mighty.shutdown()
