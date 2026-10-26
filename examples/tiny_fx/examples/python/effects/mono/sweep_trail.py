from tiny_fx import TinyFX

from picofx import MonoPlayer, fade
from picofx.mono import SweepFX

"""
Sweep a light back and forth across Tiny FX's outputs with a trail behind it.

The trail is a slow fade set on the player, so the same two lines add a trail to any
effect. The sweep holds at each end until the trail clears.

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)   # Create a new effect player to control Tiny FX's mono outputs


# Create and set up a sweep effect to play
sweep = SweepFX(speed=1.0,          # The speed to sweep at, with 1.0 being one crossing a second
                length=6.0,         # How many outputs the light crosses. Usually the number of them (6)
                extent=1.0,         # How far the light reaches from itself, in outputs
                hold=1.0)           # The seconds to wait at each end, long enough for the trail to clear


# Outputs come up quickly and go out slowly, which leaves the trail. fade() changes at a steady rate
player.curves = fade(0.05,          # The seconds an output takes to come up
                     1.0)           # The seconds it takes to go out


# Set up the sweep effect to play, each output at its own position for the light to pass
player.effects = [
    sweep(0),
    sweep(1),
    sweep(2),
    sweep(3),
    sweep(4),
    sweep(5)
]


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()   # Start the effects running

    # Loop until the effect stops or the "Boot" button is pressed
    while player.is_running() and not tiny.boot_pressed():
        pass

# Stop any running effects and turn off all the outputs
finally:
    player.stop()
    tiny.shutdown()
