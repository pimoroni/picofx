from mighty_fx import MightyFX

from picofx import MonoPlayer
from picofx.mono import SweepFX

"""
Sweep a light back and forth across every colour of MightyFX's outputs.

They run red, green then blue along each output, so the light changes colour as it
travels, passing through each output's three components in turn.

Press "Boot" to exit the program.
"""

# Variables
mighty = MightyFX()                 # Create a new MightyFX object to interact with the board
player = MonoPlayer(mighty.monos)   # Create a new effect player to control each colour of MightyFX's outputs


# Create and set up a sweep effect to play
sweep = SweepFX(speed=0.5,                      # The speed to sweep at, with 1.0 being one crossing a second
                length=len(mighty.monos),       # How many of them the light crosses. Usually the number of them (21)
                extent=2.0)                     # How far the light reaches from itself, in outputs


# Set up the sweep effect to play. Each one has a different position
# for the light to be measured against as it passes
player.effects = [sweep(position) for position in range(len(mighty.monos))]


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
