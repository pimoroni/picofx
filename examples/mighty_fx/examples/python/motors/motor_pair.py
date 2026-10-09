import math
import time
from mighty_fx import MightyFX, SPCE
from spce import MotorDriver

"""
Sweep a pair of motors up and down their speed range together, on a SP/CE connector
spent on a motor driver.

The driver is built from the connector's pins and holds the two motors they reach, along
with the power those share. Both are given the same speed here, following a sine, so a
cycle runs from a stop out to full forward, back through a stop to full reverse, and round
again.

The driver comes up unpowered, so nothing wired to it moves until enable() is called.

Press "Boot" to exit the program.
"""

# Constants
SPEED_EXTENT = 1.0      # How far from zero to drive the motors when sweeping

mighty = MightyFX(spce_a=SPCE.GPIO_PWM)

driver = MotorDriver(mighty.spce_a.pins)    # The driver on the A connector, and the two motors it holds
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

# The driver is this program's, not the board's, so it stops the motors itself
finally:
    driver.disable()
    mighty.shutdown()
