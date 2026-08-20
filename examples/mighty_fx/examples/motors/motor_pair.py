import math
import time
from mighty_fx import MightyFX, SPCE

"""
Sweep a pair of motors up and down their speed range together, on an SP/CE connector
declared as a motor driver.

A connector declared that way hands back two motors, a pair of its data pins to each, and
both are given the same speed here. That speed follows a sine, so a cycle runs from a stop
out to full forward, back through a stop to full reverse, and round again.

Press "Boot" to exit the program.
"""

# Constants
SPEED_EXTENT = 1.0      # How far from zero to drive the motors when sweeping

mighty = MightyFX(spce_a=SPCE.MOTOR_DRIVER)

motors = mighty.motors_a
i = 0

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        speed = math.sin(math.radians(i)) * SPEED_EXTENT
        for m in motors:
            m.speed(speed)
        i = (i + 1) % 360
        time.sleep(0.02)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
