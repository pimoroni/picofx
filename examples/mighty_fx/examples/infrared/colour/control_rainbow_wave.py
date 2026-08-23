from aye_arr.nec.remotes import PimoroniRemote
from mighty_fx import MightyFX
from sensor import IR

from picofx import ColourPlayer
from picofx.colour import RainbowWaveFX

"""
Play a rainbow that travels along Mighty FX's outputs, controllable by the
directional buttons on a Pimoroni Aye Arr Remote.

Where the rainbow example gives every output the same colour at once, this gives each
one a different place in the rainbow, so the colours move along the board. The length
is how many outputs the rainbow spans before it repeats: at seven the whole spectrum
sits across the board once, and below that it repeats within it.

Actions:
- ANTICLOCK [Press + Hold] = Decrease Speed
- CLOCKWISE [Press + Hold] = Increase Speed
- LEFT [Press + Hold] = Decrease Length
- RIGHT [Press + Hold] = Increase Length
- UP [Press + Hold] = Increase Brightness
- DOWN [Press + Hold] = Decrease Brightness

An IR Stick should be connected to the Sensor port on Mighty FX.

Press "Boot" to exit the program.
"""

# Constants
STARTING_SPEED = 0.2                    # The speed to cycle through colours at, with 1.0 being 1 second
STARTING_LENGTH = 7.0                   # How many outputs the rainbow spans before it repeats
STARTING_SATURATION = 1.0               # The saturation/intensity of the colours (from 0.0 to 1.0)
STARTING_VALUE = 1.0                    # The value/brightness of the colours (from 0.0 to 1.0)

SPEED_MULT = 1.1                        # The amount to multiply or divide the effect's speed by each press / repeat
LENGTH_STEP = 0.1                       # The amount that length will change by with each press / repeat
VAL_STEP = 0.05                         # The amount that value will change by with each press / repeat

# Variables
mighty = MightyFX(sensor=IR)            # Create a new MightyFX object, with the infrared receiver on its sensor connector
player = ColourPlayer(mighty.outputs)   # Create a new effect player to control MightyFX's RGB outputs


# Create a rainbow wave effect
wave = RainbowWaveFX(speed=STARTING_SPEED,
                     length=STARTING_LENGTH,
                     sat=STARTING_SATURATION,
                     val=STARTING_VALUE)

# Set up the wave effect to play. Each output has a different position
# along the wave, with the value being related to the effect's length
player.effects = [
    wave(0),
    wave(1),
    wave(2),
    wave(3),
    wave(4),
    wave(5),
    wave(6)
]


# Function called to change the speed of the wave
def adjust_speed(amount):
    global wave
    wave.speed = max(min(wave.speed * amount, 10), 0.01)
    print(f"Speed = {wave.speed:.2f}")


# Function called to change how many outputs the rainbow spans
def adjust_length(amount):
    global wave
    wave.length = max(min(wave.length + amount, 20), 0.1)
    print(f"Length = {wave.length:.2f}")


# Function called to change the value (brightness) of the colours
def adjust_val(amount):
    global wave
    wave.val = max(min(wave.val + amount, 1.0), 0.0)
    print(f"Val = {wave.val:.2f}")


# Create the remote and setup up what each of the buttons will do
remote = PimoroniRemote()
remote.bind("ANTICLOCK", (adjust_speed, 1 / SPEED_MULT))
remote.bind("CLOCKWISE", (adjust_speed, SPEED_MULT))
remote.bind("RIGHT", (adjust_length, LENGTH_STEP))
remote.bind("LEFT", (adjust_length, -LENGTH_STEP))
remote.bind("UP", (adjust_val, VAL_STEP))
remote.bind("DOWN", (adjust_val, -VAL_STEP))

# Take the receiver the board set up, and bind the remote to it.
receiver = mighty.sensor
receiver.bind(remote)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()   # Start the effects running

    # Loop until the effect stops or the "Boot" button is pressed
    while player.is_running() and not mighty.boot_pressed():
        # Decode any IR pulses received since the last time this was called.
        # This should be done as frequently as possible to avoid inputs feeling sluggish
        receiver.decode()

# End the program by stopping any active systems
finally:
    player.stop()
    mighty.shutdown()
