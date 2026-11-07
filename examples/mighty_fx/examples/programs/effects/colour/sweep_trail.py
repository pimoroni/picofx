from mighty_fx import MightyFX
from picofx import ColourPlayer, fade
from picofx.colour import RED
from picofx.mono import SweepFX

"""
Sweep a red light back and forth across Mighty FX's outputs with a trail behind it, like
the scanner a certain talking car wears across its nose.

SweepFX brings no colour of its own, so the player draws it in SCANNER_COLOUR. The trail
is a slow fade set on the player, so the same two lines add a trail to any effect. The
sweep holds at each end until the trail clears.

Press "Boot" to exit the program.
"""

# Constants
SCANNER_COLOUR = RED                    # The colour the light and its trail are drawn in


# Variables
mighty = MightyFX()                     # Create a new MightyFX object to interact with the board
player = ColourPlayer(mighty.outputs)   # Create a new effect player to control Mighty FX's RGB outputs


# Create and set up a sweep effect to play
sweep = SweepFX(speed=1.0,              # The speed to sweep at, with 1.0 being one crossing a second
                length=7.0,             # How many outputs the light crosses. Usually the number of them (7)
                extent=1.0,             # How far the light reaches from itself, in outputs
                hold=1.0)               # The seconds to wait at each end, long enough for the trail to clear


# Outputs come up quickly and go out slowly, which leaves the trail. fade() changes at a steady rate
player.curves = fade(0.05,              # The seconds an output takes to come up
                     1.0)               # The seconds it takes to go out


# The colour every output draws its share of the sweep in
player.colours = SCANNER_COLOUR


# Set up the sweep effect to play, each output at its own position for the light to pass
player.effects = [sweep(position) for position in range(len(mighty.outputs))]


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
