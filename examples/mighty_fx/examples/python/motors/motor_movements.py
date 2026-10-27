import time

from mighty_fx import MightyFX, SPCE

from picofx.colour import RED, WHITE

"""
Drive a two wheeled robot through a fixed sequence of movements, on a driver on SP/CE
port A.

The remote_robot.py robot driving itself through forwards, back, spins and curves, which
makes it the one for checking a chassis is wired and scaled correctly.

Give it room, or hold it off the ground.

Press "Boot" to exit the program.

Section: Moving things
Thumbnail: motor
"""

# Constants
DRIVE_SPEED = 0.8       # How fast to drive, from 0.0 to 1.0
TURN_SPEED = 0.4        # How fast to spin on the spot, slower being easier to aim
CURVE_INNER = 0.3       # What the inside wheel of a curve is given, against the outside
MOVE_TIME = 1.5         # The time, in seconds, each movement lasts
PAUSE_TIME = 0.5        # The time, in seconds, to stand still between movements

# Variables
mighty = MightyFX(spce_a=SPCE.MOTOR_DRIVER)
driver = mighty.spce_a.driver

driver.enable()         # Power the driver, which the board leaves off until asked


# Function to drive both wheels, each at its own speed. The wheels face opposite ways
# on a robot, so the right one is given the negative of what it should turn
def wheels(left, right, colour=WHITE):
    mighty.two.set_rgb(*colour)
    driver.motor_a.speed(left)
    driver.motor_b.speed(-right)


# Function to stand still between movements
def pause():
    mighty.clear()
    for motor in driver.motors:
        motor.stop()
    time.sleep(PAUSE_TIME)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        print("Forwards")
        wheels(DRIVE_SPEED, DRIVE_SPEED)
        time.sleep(MOVE_TIME)
        pause()

        print("Backwards")
        wheels(-DRIVE_SPEED, -DRIVE_SPEED, RED)
        time.sleep(MOVE_TIME)
        pause()

        print("Spinning left")
        wheels(-TURN_SPEED, TURN_SPEED)
        time.sleep(MOVE_TIME)
        pause()

        print("Spinning right")
        wheels(TURN_SPEED, -TURN_SPEED)
        time.sleep(MOVE_TIME)
        pause()

        # A curve drives both wheels forwards, the inside one slower
        print("Curving left")
        wheels(DRIVE_SPEED * CURVE_INNER, DRIVE_SPEED)
        time.sleep(MOVE_TIME)
        pause()

        print("Curving right")
        wheels(DRIVE_SPEED, DRIVE_SPEED * CURVE_INNER)
        time.sleep(MOVE_TIME)
        pause()

# Stop the motors and turn off all the outputs
finally:
    mighty.shutdown()
