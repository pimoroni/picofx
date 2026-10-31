from mighty_fx import MightyFX

from picofx import ColourPlayer, ease
from picofx.mono import TrafficLightFX

"""
Play a traffic light sequence on three of Mighty FX's RGB outputs.

TrafficLightFX brings no colour of its own, so the board supplies each light's colour and
the signal needs no coloured lamps.

They ease on and off like the filament lamps of a real signal. The easing is set on the
player, so it works the same for any effect.

Press "Boot" to exit the program.
"""

# Constants
RED = (255, 0, 0)                       # The three a UK traffic light shows
AMBER = (255, 120, 0)                   # Nearer orange than yellow
GREEN = (0, 210, 140)                   # A blue-green rather than a pure one


# Variables
mighty = MightyFX()                     # Create a new MightyFX object to interact with the board
player = ColourPlayer(mighty.outputs)   # Create a new effect player to control Mighty FX's RGB outputs


# Effects
traffic = TrafficLightFX(red_interval=5,            # The time (in seconds) to stay on Red
                         red_amber_interval=2.5,    # The time (in seconds) to stay on Red+Amber
                         green_interval=5,          # The time (in seconds) to stay on Green
                         amber_interval=2.5)        # The time (in seconds) to stay on Amber


# How long each output takes to reach its level. One value covers all, along a warming filament's curve
player.curves = ease(0.3)


# The colour each output draws its light in
player.colours = [RED, AMBER, GREEN]


# Set up the traffic light effect to play, on the first 3 outputs and nothing on the rest
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
