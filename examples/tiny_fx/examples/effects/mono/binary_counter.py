from tiny_fx import TinyFX
from picofx import MonoPlayer
from picofx.mono import BinaryCounterFX

"""
Play an incrementing binary counter on TinyFX's outputs.

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                         # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)       # Create a new effect player to control TinyFX's mono outputs


# Create a BinaryCounterFX effect
binary = BinaryCounterFX(interval=0.1)  # The time (in seconds) between each increment of the binary counter


# Set up the binary effect to play. Each output shows a different bit of the counter
player.effects = [
    binary(0),
    binary(1),
    binary(2),
    binary(3),
    binary(4),
    binary(5)
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
