from mighty_fx import MightyFX
from servo import ANGULAR, CONTINUOUS, LINEAR, Calibration

"""
Show the three kinds of servo Mighty FX's L and R connectors can drive, and how to
widen or rescale what their values mean.

A servo is declared ANGULAR, LINEAR or CONTINUOUS, which decides whether value() takes
degrees, a distance, or a speed from -1.0 to 1.0. Each has a calibration that can be read,
adjusted and given back, for a servo that travels further than the default.

Nothing moves here. It prints what each calibration says, to be read against the servo
in hand before anything is driven.
"""

# Constants
WIDE_ANGLE_RANGE = 270  # The travel of a wide angle servo, in degrees
LINEAR_RANGE = 50       # The travel of a linear servo, in millimetres
CONTINUOUS_SPEED = 10   # The top speed of a continuous servo, in revolutions a minute

# Variables
mighty = MightyFX(servo_l=ANGULAR, servo_r=LINEAR)


# An angular servo takes degrees, from -90 to +90 until it is told otherwise
angular = mighty.servo_l
print("Angular servo:", angular.calibration(), end="\n\n")

# Widening it, for a servo that travels further than most
cal = angular.calibration()
cal.first_value(-WIDE_ANGLE_RANGE / 2)
cal.last_value(WIDE_ANGLE_RANGE / 2)
angular.calibration(cal)
print("Wide angle servo:", angular.calibration(), end="\n\n")


# A linear servo takes 0.0 to 1.0 by default, which says nothing about how far it goes
linear = mighty.servo_r
cal = linear.calibration()
cal.last_value(LINEAR_RANGE)
linear.calibration(cal)
print("Linear servo, in millimetres:", linear.calibration(), end="\n\n")


# A continuous servo takes a speed rather than a position. A calibration can be built
# without a servo to hold it, which is how a third kind is shown on two connectors
cal = Calibration(CONTINUOUS)
print("Continuous servo:", cal, end="\n\n")

cal.first_value(-CONTINUOUS_SPEED)
cal.last_value(CONTINUOUS_SPEED)
print("Continuous servo, in revolutions a minute:", cal)

mighty.shutdown()
