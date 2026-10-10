from aye_arr.nec.remotes import PimoroniRemote
from sensor import IR
from tiny_fx import TinyFX

from picofx import MonoPlayer
from picofx.mono import BlinkFX, NoneFX, PulseFX, RandomFX, StaticFX

"""
Play effects for each "postcard" on the Tales Of The Space Age set,
and turn them on and off by pressing the number buttons on the
Pimoroni Aye Arr Remote.

Actions:
- (1)-(4) Button [Press] = Toggle Channel

An IR Stick should be connected to the Sensor port on Tiny FX.

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX(sensor=IR)           # Create a new TinyFX object, with the infrared receiver on its sensor connector
player = MonoPlayer(tiny.outputs)   # Create a new effect player to control TinyFX's mono outputs

# Set up the effects to play
effects = [
    PulseFX(speed=0.2),
    RandomFX(interval=0.01, brightness_min=0.5, brightness_max=1.0),
    NoneFX(),
    NoneFX(),
    StaticFX(brightness=0.5),
    BlinkFX(speed=0.5)
]
player.effects = effects

# Function to toggle the specified channel
def toggle_channel(channel):
    print(f"Toggle Channel #{channel}")
    new_effects = []
    player.stop()
    player.start()
    for i in range(len(tiny.outputs)):
        old_fx = player.effects[i]
        if i == channel - 1:
            if type(old_fx) is not NoneFX:
                new_effects.append(NoneFX())
            else:
                new_effects.append(effects[i])
        else:
            new_effects.append(old_fx)
    player.effects = new_effects


# Create the remote and setup up what each of the buttons will do
remote = PimoroniRemote()
remote.bind("1_RED", on_press=(toggle_channel, 6), on_repeat=None)
remote.bind("2_GREEN", on_press=(toggle_channel, 5), on_repeat=None)
remote.bind("3_BLUE", on_press=(toggle_channel, 2), on_repeat=None)
remote.bind("4_CYAN", on_press=(toggle_channel, 1), on_repeat=None)

# Take the receiver the board set up, and bind the remote to it.
receiver = tiny.sensor
receiver.bind(remote)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()

    # Loop until the "Boot" button is pressed
    while not tiny.boot_pressed():
        receiver.decode()

# Stop any running effects and turn off all the outputs
finally:
    player.stop()
    tiny.shutdown()
