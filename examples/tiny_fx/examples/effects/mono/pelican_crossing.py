from tiny_fx import TinyFX

from picofx import MonoPlayer, ease
from picofx.mono import PelicanCrossingFX

"""
Play a pelican crossing on five of TinyFX's outputs.

The first three are the traffic lights and the next two are the figures a pedestrian
reads, stop and walk. Where an ordinary signal shows red and amber together, a pelican
flashes its amber and its walking figure, which is the phase telling drivers to go if
the crossing is clear and pedestrians not to start.

It comes round on its own clock, so there is no button to press. The lights ease on and
off, which is how the filament lamps in a real crossing behave.

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                                     # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)                   # Create a new effect player to control TinyFX's mono outputs


# Effects
pelican = PelicanCrossingFX(green_interval=20,      # The time (in seconds) traffic is moving
                            amber_interval=3,       # The time (in seconds) traffic is clearing
                            red_interval=8,         # The time (in seconds) pedestrians are crossing
                            flashing_interval=6)    # The time (in seconds) the amber and the walking figure flash


# How long each output takes to reach what the effect asks for. A single value
# covers every output, and ease() is the curve a warming filament follows
player.curves = ease(0.3)


# Set up the crossing to play. The 3 traffic lights are assigned to the first 3
# outputs and the 2 figures to the next 2, leaving the last output without one
player.effects = [
    pelican.red(),
    pelican.amber(),
    pelican.green(),

    pelican.stop(),
    pelican.walk(),
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
