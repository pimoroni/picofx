from tiny_fx import TinyFX
from picofx import ColourPlayer
from picofx.colour import RainbowFX

import aye_arr.logging as logging
from aye_arr.nec import NECRemoteReceiver
from aye_arr.nec.remotes import PimoroniRemote

"""
Play a rainbow effect on TinyFX's RGB output that is controllable
by the directional buttons on a Pimoroni Aye Arr Remote.

Actions:
- ANTICLOCK [Press + Hold] = Decrease Speed
- CLOCKWISE [Press + Hold] = Increase Speed
- UP [Press + Hold] = Increase Brightness
- DOWN [Press + Hold] = Decrease Brightness
- LEFT [Press + Hold] = Decrease Saturation
- RIGHT [Press + Hold] = Increase Saturation

An IR Stick should be connected to the Sensor port on Tiny FX.

Press "Boot" to exit the program.
"""

# Constants
STARTING_SPEED = 0.2                # The speed to cycle through colours at, with 1.0 being 1 second
STARTING_SATURATION = 1.0           # The saturation/intensity of the colour (from 0.0 to 1.0)
STARTING_VALUE = 1.0                # The value/brightness of the colour (from 0.0 to 1.0)

SPEED_MULT = 1.1                    # The amount to multiply or divide the effects speed by each press / repeat
SAT_STEP = 0.01                     # The amount that saturation will change by with each press / repeat
VAL_STEP = 0.05                     # The amount that value will change by with each press / repeat


# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
player = ColourPlayer(tiny.rgb)     # Create a new effect player to control TinyFX's RGB output


# Create and set up a static colour effect to "play"
rainbow = RainbowFX(speed=STARTING_SPEED,
                    sat=STARTING_SATURATION,
                    val=STARTING_VALUE)
player.effects = rainbow


# Function called to change the speed of the colour effect
def adjust_speed(amount):
    global rainbow
    rainbow.speed = max(min(rainbow.speed * amount, 10), 0.01)
    print(f"Speed = {rainbow.speed:.2f}")


# Function called to change the saturation of the colour
def adjust_sat(amount):
    global rainbow
    rainbow.sat = max(min(rainbow.sat + amount, 1.0), 0.0)
    print(f"Sat = {rainbow.sat:.2f}")


# Function called to change the value (brightness) of the colour
def adjust_val(amount):
    global rainbow
    rainbow.val = max(min(rainbow.val + amount, 1.0), 0.0)
    print(f"Val = {rainbow.val:.2f}")


# Create the remote and setup up what each of the buttons will do
remote = PimoroniRemote()
remote.bind("ANTICLOCK", (adjust_speed, 1 / SPEED_MULT))
remote.bind("CLOCKWISE", (adjust_speed, SPEED_MULT))
remote.bind("RIGHT", (adjust_sat, SAT_STEP))
remote.bind("LEFT", (adjust_sat, -SAT_STEP))
remote.bind("UP", (adjust_val, VAL_STEP))
remote.bind("DOWN", (adjust_val, -VAL_STEP))

# Set up a receiver on the RX pin, using PIO 1 and SM 0, and bind the remote to it.
receiver = NECRemoteReceiver(TinyFX.SENSOR_PIN, 1, 0, logging_level=logging.LOG_NONE)
receiver.bind(remote)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    receiver.start()
    player.start()   # Start the effects running

    # Loop until the effect stops or the "Boot" button is pressed
    while not tiny.boot_pressed():
        # Decode any IR pulses received since the last time this was called.
        # This should be done as frequently as possible to avoid inputs feeling sluggish
        receiver.decode()

# End the program by stopping any active systems
finally:
    receiver.stop()
    player.stop()
    tiny.shutdown()
