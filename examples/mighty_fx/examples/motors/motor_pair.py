# A spinny rainbow wheel. Change up some of the constants below to see what happens.

import math
import time
from mighty_fx import MightyFX, SPCE

# Constants for drawing
SWEEPS = 2              # How many speed sweeps of the motors to perform
STEPS = 10              # The number of discrete sweep steps
STEPS_INTERVAL = 0.5    # The time in seconds between each step of the sequence
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
