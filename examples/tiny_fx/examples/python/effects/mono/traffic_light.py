from tiny_fx import TinyFX

from picofx import MonoPlayer, ease
from picofx.mono import TrafficLightFX

"""
Play a traffic light sequence on TinyFX's outputs.

The three lights ease on and off rather than switching, which is how the filament
lamps in a real signal behave. Softening belongs to the outputs, so it is set on the
player and works the same for any effect.

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                                     # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)                   # Create a new effect player to control TinyFX's mono outputs


# Effects
traffic = TrafficLightFX(red_interval=5,            # The time (in seconds) to stay on Red
                         red_amber_interval=2.5,    # The time (in seconds) to stay on Red+Amber
                         green_interval=5,          # The time (in seconds) to stay on Green
                         amber_interval=2.5)        # The time (in seconds) to stay on Amber


# How long each output takes to reach what the effect asks for. A single value
# covers every output, and ease() is the curve a warming filament follows
player.curves = ease(0.3)


# Set up the traffic light effect to play.
# The 3 light colours are assigned to the first 3 outputs
player.effects = [
    traffic.red(),
    traffic.amber(),
    traffic.green(),

    # No effects played on the rest of the outputs (unnecessary to list, but show for clarity)
    None,
    None,
    None,
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
