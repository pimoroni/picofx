from aye_arr.nec import NECRemoteReceiver
from aye_arr.nec.remotes import PimoroniRemote
from tiny_fx import TinyFX

from picofx import MonoPlayer
from picofx.mono import PulseWaveFX

"""
Play a wave of pulses on TinyFX's outputs that is controllable
by the directional buttons on a Pimoroni Aye Arr Remote.

Actions:
- ANTICLOCK [Press + Hold] = Decrease Speed
- CLOCKWISE [Press + Hold] = Increase Speed
- LEFT [Press + Hold] = Decrease Length
- RIGHT [Press + Hold] = Increase Length

An IR Stick should be connected to the Sensor port on Tiny FX.

Press "Boot" to exit the program.
"""

# Constants
STARTING_SPEED = 0.2                # The speed to pulse at, with 1.0 being 1 second
STARTING_LENGTH = 6.0               # The length of the wave before positions repeat. Usually the number of outputs (6)

SPEED_MULT = 1.1                    # The amount to multiply or divide the effects speed by each press / repeat
LENGTH_STEP = 0.1                   # The amount that length will change by with each press / repeat

# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)   # Create a new effect player to control TinyFX's mono outputs


# Create a PulseWaveFX effect
wave = PulseWaveFX(speed=STARTING_SPEED,
                   length=STARTING_LENGTH)

# Set up the wave effect to play. Each output has a different position
# along the wave, with the value being related to the effect's length
player.effects = [
    wave(0),
    wave(1),
    wave(2),
    wave(3),
    wave(4),
    wave(5)
]


# Function called to change the speed of the colour effect
def adjust_speed(amount):
    global wave
    wave.speed = max(min(wave.speed * amount, 10), 0.01)
    print(f"Speed = {wave.speed:.2f}")


# Function called to change the saturation of the colour
def adjust_length(amount):
    global wave
    wave.length = max(min(wave.length + amount, 20), 1)
    print(f"Length = {wave.length:.2f}")


# Create the remote and setup up what each of the buttons will do
remote = PimoroniRemote()
remote.bind("ANTICLOCK", (adjust_speed, 1 / SPEED_MULT))
remote.bind("CLOCKWISE", (adjust_speed, SPEED_MULT))
remote.bind("RIGHT", (adjust_length, LENGTH_STEP))
remote.bind("LEFT", (adjust_length, -LENGTH_STEP))

# Set up a receiver on Tiny FX's sensor pin, using PIO 1 and SM 0, and bind the remote to it.
receiver = NECRemoteReceiver(TinyFX.SENSOR_PIN, 1, 0)
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
