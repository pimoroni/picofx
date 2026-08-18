from mighty_fx import MightyFX

from picofx import ColourPlayer, ease
from picofx.mono import TrafficLightFX

"""
Play a traffic light sequence on three of MightyFX's RGB outputs.

TrafficLightFX brings no colour of its own: it reports which of the three lights is
lit, and each output is set to the colour that light should be. So the signal needs no
coloured lamps, and changing what red or amber look like is one line here.

They ease on and off rather than switching, which is how the filament lamps in a real
signal behave. Softening belongs to the outputs, so it is set on the player and works
the same for any effect.

Press "Boot" to exit the program.
"""

# Constants
RED = (255, 0, 0)                       # The three a UK traffic light shows
AMBER = (255, 120, 0)                   # Nearer orange than yellow
GREEN = (0, 210, 140)                   # A blue-green rather than a pure one


# Variables
mighty = MightyFX()                     # Create a new MightyFX object to interact with the board
player = ColourPlayer(mighty.outputs)   # Create a new effect player to control MightyFX's RGB outputs


# Effects
traffic = TrafficLightFX(red_interval=5,            # The time (in seconds) to stay on Red
                         red_amber_interval=2.5,    # The time (in seconds) to stay on Red+Amber
                         green_interval=5,          # The time (in seconds) to stay on Green
                         amber_interval=2.5)        # The time (in seconds) to stay on Amber


# How long each output takes to reach what the effect asks for. A single value
# covers every output, and ease() is the curve a warming filament follows
player.curves = ease(0.3)


# The colour each output draws its light in. The outputs after the third play
# nothing, so the colours they are given never show
player.colours = [RED, AMBER, GREEN]


# Set up the traffic light effect to play. The 3 lights are assigned to the first 3
# outputs; the rest are left without one, which the player takes as nothing to play
player.effects = [
    traffic.red(),
    traffic.amber(),
    traffic.green(),
]


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
