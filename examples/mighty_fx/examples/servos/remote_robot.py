from aye_arr.nec.remotes import PimoroniRemote
from mighty_fx import MightyFX
from sensor import IR
from servo import CONTINUOUS

from picofx import ColourPlayer
from picofx.colour import RED, WHITE
from picofx.mono import BlinkFX, StaticFX

"""
Drive a two wheeled robot from a Pimoroni Aye Arr Remote, its wheels turned by a
continuous rotation servo on each of the L and R connectors.

A continuous servo takes a speed rather than an angle, from -1.0 to 1.0, and the two
face opposite ways on a robot, so driving forwards asks one for a speed and the other
for its negative. Turning on the spot asks both for the same.

Output 2 is the headlight and output 1 the tail light, lit for the direction being
driven, and outputs 3 and 4 are amber indicators, lit on the side being turned towards,
so the robot says which way it is about to go.

An IR Stick should be connected to the Sensor port on Mighty FX.

Actions:
- UP Button [Hold] = Drive forwards
- DOWN Button [Hold] = Drive backwards
- LEFT Button [Hold] = Spin left
- RIGHT Button [Hold] = Spin right

Press "Boot" to exit the program.
"""

# Constants
AMBER = (255, 120, 0)   # Nearer orange than yellow, as an indicator is
BLINK_SPEED = 2.0       # How many times a second an indicator blinks
DRIVE_SPEED = 0.8       # How fast to drive, from 0.0 to 1.0
TURN_SPEED = 0.4        # How fast to spin on the spot, slower being easier to aim

# Variables
mighty = MightyFX(servo_l=CONTINUOUS, servo_r=CONTINUOUS, sensor=IR)
mighty.enable_rail()    # Power the L and R connectors, which stay off until asked
mighty.servo_l.enable()
mighty.servo_r.enable()


# The lights are played rather than set: the head and tail lights are steady and the
# indicators blink, and a level of zero is how one is put out. Their colours come from
# the player, the effects giving a brightness and no colour of their own
player = ColourPlayer(mighty.outputs)
player.effects = [StaticFX(), StaticFX(), BlinkFX(speed=BLINK_SPEED), BlinkFX(speed=BLINK_SPEED)]
player.colours = [RED, WHITE, AMBER, AMBER]
player.levels = 0.0     # Every light out until a button asks for one


# Function to show a set of lights, each named for what it says, and put out the rest
def lights(tail=0.0, head=0.0, left=0.0, right=0.0):
    player.levels = [tail, head, left, right]


# Function to stop both wheels and put the lights out
def stop():
    print("Stop")
    lights()
    mighty.servo_l.value(0)
    mighty.servo_r.value(0)


# Function to drive both wheels the same way, forwards on a positive speed
def drive(speed):
    if speed > 0:
        print("Drive forwards")
        lights(head=1.0)
    else:
        print("Drive backwards")
        lights(tail=1.0)

    # The wheels face opposite ways, so one turns against the other to go straight
    mighty.servo_l.value(speed)
    mighty.servo_r.value(-speed)


# Function to spin on the spot, both wheels turning the same way
def spin(speed):
    print("Spin right" if speed > 0 else "Spin left")
    if speed > 0:
        lights(head=1.0, right=1.0)
    else:
        lights(head=1.0, left=1.0)
    mighty.servo_l.value(speed)
    mighty.servo_r.value(speed)


# Create the remote and setup up what each of the buttons will do
remote = PimoroniRemote()
remote.bind("UP", on_press=(drive, DRIVE_SPEED), on_release=stop)
remote.bind("DOWN", on_press=(drive, -DRIVE_SPEED), on_release=stop)
remote.bind("LEFT", on_press=(spin, -TURN_SPEED), on_release=stop)
remote.bind("RIGHT", on_press=(spin, TURN_SPEED), on_release=stop)

# Take the receiver the board set up, and bind the remote to it.
receiver = mighty.sensor
receiver.bind(remote)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()   # Start the lights running

    # Loop until the "Boot" button is pressed
    while not mighty.boot_pressed():
        # Decode any IR pulses received since the last time this was called.
        # This should be done as frequently as possible to avoid inputs feeling sluggish
        receiver.decode()

# Stop the wheels, drop the connectors' power and turn off all the outputs
finally:
    player.stop()
    mighty.shutdown()
