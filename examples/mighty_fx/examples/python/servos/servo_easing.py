import math
import random

from mighty_fx import MightyFX
from timing import Pacer
from servo import ANGULAR

"""
Move a servo smoothly between random positions on MightyFX's L connector.

A servo asked to jump from one angle to another goes as fast as it can and arrives with
a jolt. Moving it in small steps along a cosine gives it a start and a finish instead,
slow at both ends and quickest in the middle, which is how a limb or a head moves.

Set USE_COSINE to False to travel at a steady rate and feel the difference.

Press "Boot" to exit the program.
"""

# Constants
UPDATES = 50                            # How many times a second to move the servo
TIME_FOR_EACH_MOVE = 2                  # The time, in seconds, to travel between positions
SERVO_EXTENT = 80                       # How far from zero to move the servo, in degrees
USE_COSINE = True                       # Whether to ease between positions or cross at a steady rate

UPDATES_PER_MOVE = TIME_FOR_EACH_MOVE * UPDATES

# Variables
mighty = MightyFX(servo_l=ANGULAR)      # Create a new MightyFX object, with an angular servo on L
servo = mighty.servo_l

mighty.enable_rail()                    # Power the L and R connectors, which stay off until asked
servo.enable()

# Where this movement began, and the position it is heading for
start_value = servo.mid_value()
end_value = random.uniform(-SERVO_EXTENT, SERVO_EXTENT)
update = 0

# The movement is stepped a count at a time, so its length depends on the steps landing
# on the rate they were counted for. A pacer holds that where sleeping the interval
# would add whatever each step costs
pacer = Pacer(fps=UPDATES)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # How far along this movement the servo should be
        percent_along = update / UPDATES_PER_MOVE

        if USE_COSINE:
            # A cosine leaves and arrives slowly, and is quickest in the middle
            servo.to_percent(math.cos(percent_along * math.pi), 1.0, -1.0, start_value, end_value)
        else:
            servo.to_percent(percent_along, 0.0, 1.0, start_value, end_value)

        update += 1

        # At the end of a movement, the position reached becomes the next one's start
        if update >= UPDATES_PER_MOVE:
            update = 0
            start_value = end_value
            end_value = random.uniform(-SERVO_EXTENT, SERVO_EXTENT)
            print("Heading for", round(end_value, 1), "degrees")

        pacer.hold()

# Stop driving the servo, drop the connectors' power and turn off all the outputs
finally:
    mighty.shutdown()
