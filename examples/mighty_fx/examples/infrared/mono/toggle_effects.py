from aye_arr.nec.remotes import PimoroniRemote
from mighty_fx import MightyFX
from sensor import IR

from picofx import ColourPlayer
from picofx.colour import BLUE, CYAN, GREEN, MAGENTA, RED, WARM, YELLOW
from picofx.mono import BlinkFX, NoneFX, PulseFX, RandomFX, StaticFX

"""
Play a different effect on each of Mighty FX's outputs, and turn them on and off by
pressing the number buttons on the Pimoroni Aye Arr Remote.

Every effect here is a mono one, giving a brightness rather than a colour, so each
output draws its effect in the colour it was given. That is what makes a flicker read
as a candle on one output and as a fault light on another.

Actions:
- (1)-(7) Button [Press] = Toggle Output

An IR Stick should be connected to the Sensor port on Mighty FX.

Press "Boot" to exit the program.
"""

# Variables
mighty = MightyFX(sensor=IR)            # Create a new MightyFX object, with the infrared receiver on its sensor connector
player = ColourPlayer(mighty.outputs)   # Create a new effect player to control MightyFX's RGB outputs


# The colour each output draws its effect in, matching the button that toggles it
player.colours = [RED, GREEN, BLUE, CYAN, MAGENTA, YELLOW, WARM]

# Set up the effects to play, one for each output
effects = [
    PulseFX(speed=0.2),
    RandomFX(interval=0.01, brightness_min=0.5, brightness_max=1.0),
    StaticFX(brightness=0.5),
    BlinkFX(speed=0.5),
    PulseFX(speed=0.5),
    NoneFX(),
    NoneFX(),
]
player.effects = effects


# Function to toggle the specified output
def toggle_output(output):
    print(f"Toggle Output #{output}")
    new_effects = []
    for i in range(len(mighty.outputs)):
        old_fx = player.effects[i]
        if i == output - 1:
            # An output that is playing something goes quiet, and one that is quiet
            # takes its own effect back
            if type(old_fx) is not NoneFX:
                new_effects.append(NoneFX())
            else:
                new_effects.append(effects[i])
        else:
            new_effects.append(old_fx)
    player.effects = new_effects


# Create the remote and setup up what each of the buttons will do
remote = PimoroniRemote()
remote.bind("1_RED", on_press=(toggle_output, 1), on_repeat=None)
remote.bind("2_GREEN", on_press=(toggle_output, 2), on_repeat=None)
remote.bind("3_BLUE", on_press=(toggle_output, 3), on_repeat=None)
remote.bind("4_CYAN", on_press=(toggle_output, 4), on_repeat=None)
remote.bind("5_MAGENTA", on_press=(toggle_output, 5), on_repeat=None)
remote.bind("6_YELLOW", on_press=(toggle_output, 6), on_repeat=None)
remote.bind("7_WARM", on_press=(toggle_output, 7), on_repeat=None)

# Take the receiver the board set up, and bind the remote to it.
receiver = mighty.sensor
receiver.bind(remote)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()

    # Loop until the "Boot" button is pressed
    while not mighty.boot_pressed():
        receiver.decode()

# Stop any running effects and turn off all the outputs
finally:
    player.stop()
    mighty.shutdown()
