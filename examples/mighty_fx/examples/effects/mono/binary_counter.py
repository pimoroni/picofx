from mighty_fx import MightyFX

from picofx import MonoPlayer
from picofx.mono import BinaryCounterFX

"""
Play an incrementing binary counter across every colour of MightyFX's outputs.

Each output carries three bits, so it steps through eight RGB mixes:
    dark, red, green, yellow, blue, magenta, cyan, white.

Press "Boot" to exit the program.
"""

# Variables
mighty = MightyFX()                     # Create a new MightyFX object to interact with the board
player = MonoPlayer(mighty.monos)       # Create a new effect player to control each colour of MightyFX's outputs


# Create a BinaryCounterFX effect
binary = BinaryCounterFX(interval=0.1)  # The time (in seconds) between each increment of the binary counter


# Set up the binary effect to play. Each one shows a different bit of the counter
player.effects = [binary(bit) for bit in range(len(mighty.monos))]


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()   # Start the effects running

    # Loop until the effect stops or the "Boot" button is pressed
    while player.is_running() and not mighty.boot_pressed():
        pass

# Stop any running effects and turn off all the outputs
finally:
    player.stop()
    mighty.shutdown()
