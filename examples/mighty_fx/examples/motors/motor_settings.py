import time

from mighty_fx import MightyFX, SPCE
from motor import FAST_DECAY, SLOW_DECAY

from pimoroni import NORMAL_DIR, REVERSED_DIR

"""
Show what a motor can be told beyond its speed, on a driver on SP/CE port A.

Every setting here is one a real machine needs: which way the motor counts as forwards,
how much of the speed range does nothing because the motor cannot overcome its own
friction, how it behaves when asked to stop, and how fast it is switched.

The motor turns throughout, so give it room. Press "Boot" to exit the program.
"""

# Constants
SPEED = 0.5             # The speed to drive at while showing each setting
HOLD = 2                # The time, in seconds, to hold each setting

# Variables
mighty = MightyFX(spce_a=SPCE.MOTOR_DRIVER)
driver = mighty.driver_a
motor = driver.motor_a  # Everything here is shown on one of the driver's two motors

driver.enable()         # Power the driver, which the board leaves off until asked


def hold(message):
    print(message)
    time.sleep(HOLD)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Which way the motor treats a positive speed. Reversing it is how a wheel on
        # the far side of a robot is made to agree with the one opposite
        motor.direction(NORMAL_DIR)
        motor.speed(SPEED)
        hold("Normal direction")

        motor.direction(REVERSED_DIR)
        hold("Reversed direction, at the same speed")

        motor.direction(NORMAL_DIR)

        # The part of the range a motor cannot act on, being too slow to turn at all.
        # Raising it makes a small speed mean the slowest the motor really moves
        motor.deadzone(0.05)
        motor.speed(0.1)
        hold(f"A small speed with a deadzone of {motor.deadzone()}")

        motor.deadzone(0.2)
        hold(f"The same speed with a deadzone of {motor.deadzone()}")

        motor.deadzone(0.05)

        # How the motor behaves between the pulses that drive it. A slow decay holds
        # the motor against its own momentum and a fast one lets it run on
        motor.decay_mode(SLOW_DECAY)
        motor.speed(SPEED)
        hold("Driving with a slow decay")

        motor.decay_mode(FAST_DECAY)
        hold("Driving with a fast decay")

        motor.decay_mode(SLOW_DECAY)

        # How often the motor is switched. Low is audible and high is not, at the cost
        # of the driver's own switching losses
        motor.frequency(100)
        hold(f"Switching at {round(motor.frequency())}Hz, which can be heard")

        motor.frequency(20000)
        hold(f"Switching at {round(motor.frequency())}Hz, which cannot")

        motor.frequency(25000)

        # Stopping, and letting it run down of its own accord
        motor.stop()
        hold("Stopped, which holds the motor still")

        motor.speed(SPEED)
        time.sleep(HOLD)
        motor.coast()
        hold("Coasting, which lets it run down")

# Stop the motors, take the driver's power away and turn off all the outputs
finally:
    mighty.shutdown()
