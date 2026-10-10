from tiny_fx import TinyFX

from picofx import MonoPlayer
from picofx.mono import SweepFX

"""
Sweep a light back and forth across TinyFX's outputs.

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)   # Create a new effect player to control TinyFX's mono outputs


# Create and set up a sweep effect to play
sweep = SweepFX(speed=0.5,          # The speed to sweep at, with 1.0 being one crossing a second
                length=6.0,         # How many outputs the light crosses. Usually the number of them (6)
                extent=1.0)         # How far the light reaches from itself, in outputs


# Set up the sweep effect to play. Each output has a different position
# for the light to be measured against as it passes
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
