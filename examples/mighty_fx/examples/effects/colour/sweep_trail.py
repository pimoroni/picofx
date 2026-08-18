from mighty_fx import MightyFX
from picofx import ColourPlayer, fade
from picofx.colour import RED
from picofx.mono import SweepFX

"""
Sweep a red light back and forth across MightyFX's outputs, leaving a trail behind it,
which is the scanner a certain talking car wears across its nose.

SweepFX brings no colour of its own, so the player gives it one: a mono effect on a
colour output is drawn in whatever that output is set to. The trail is the outputs
taking their time to go dark, which is a curve on the player rather than anything the
effect does. The sweep waits at each end until the trail has gone, so it comes back
over dark outputs rather than over its own trail.

Press "Boot" to exit the program.
"""

# Constants
SCANNER_COLOUR = RED                    # The colour the light and its trail are drawn in


# Variables
mighty = MightyFX()                     # Create a new MightyFX object to interact with the board
player = ColourPlayer(mighty.outputs)   # Create a new effect player to control MightyFX's RGB outputs


# Create and set up a sweep effect to play
sweep = SweepFX(speed=1.0,              # The speed to sweep at, with 1.0 being one crossing a second
                length=7.0,             # How many outputs the light crosses. Usually the number of them (7)
                extent=1.0,             # How far the light reaches from itself, in outputs
                hold=1.0)               # The seconds to wait at each end, long enough for the trail to clear


# How long each output takes to reach what the effect asks for. Coming up quickly and
# going out slowly is what leaves the trail, and fade() spends that time at a steady rate
player.curves = fade(0.05,              # The seconds an output takes to come up
                     1.0)               # The seconds it takes to go out


# The colour every output draws its share of the sweep in
player.colours = SCANNER_COLOUR


# Set up the sweep effect to play. Each output has a different position
# for the light to be measured against as it passes
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
