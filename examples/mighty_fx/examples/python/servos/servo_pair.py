import math
import time

from mighty_fx import MightyFX
from servo import ANGULAR

"""
Sweep the servos on MightyFX's L and R connectors, together and then opposed.

Two servos given the same value move as one, which suits a pair of legs or a lift. Two
given opposite values mirror each other, which suits a gripper or a pair of eyes. The
same sweep is played both ways here so the difference is plain to watch.

Press "Boot" to exit the program.
"""

# Constants
SWEEP_EXTENT = 60.0     # How far from zero to move the servos, in degrees
STEP_INTERVAL = 0.02    # The time, in seconds, between each step of the sweep
STEPS = 10              # How many steps a stepped sweep takes to cross
STEP_HOLD = 0.3         # The time, in seconds, to hold each step of a stepped sweep

# Variables
mighty = MightyFX(servo_l=ANGULAR, servo_r=ANGULAR)

mighty.enable_rail()    # Power the L and R connectors, which stay off until asked
mighty.servo_l.enable()
mighty.servo_r.enable()


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Both servos to the middle, and to each end, so the travel can be seen
        print("To the middle, then each end")
        mighty.servo_l.to_mid()
        mighty.servo_r.to_mid()
        time.sleep(1)

        mighty.servo_l.to_min()
        mighty.servo_r.to_min()
        time.sleep(1)

        mighty.servo_l.to_max()
        mighty.servo_r.to_max()
        time.sleep(1)

        # A smooth sweep with both servos on the same value, moving as one
        print("Sweeping together")
        for i in range(360):
            value = math.sin(math.radians(i)) * SWEEP_EXTENT
            mighty.servo_l.value(value)
            mighty.servo_r.value(value)
            time.sleep(STEP_INTERVAL)

        # The same sweep with the values opposed, so the two mirror each other
        print("Sweeping opposed")
        for i in range(360):
            value = math.sin(math.radians(i)) * SWEEP_EXTENT
            mighty.servo_l.value(value)
            mighty.servo_r.value(-value)
            time.sleep(STEP_INTERVAL)

        # A stepped sweep, which arrives at each position rather than passing through it
        print("Stepping across")
        for i in range(STEPS + 1):
            for servo in (mighty.servo_l, mighty.servo_r):
                servo.to_percent(i, 0, STEPS, -SWEEP_EXTENT, SWEEP_EXTENT)
            time.sleep(STEP_HOLD)

# Stop driving the servos, drop the connectors' power and turn off all the outputs
finally:
    mighty.shutdown()
