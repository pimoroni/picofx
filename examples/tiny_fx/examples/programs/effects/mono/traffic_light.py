from tiny_fx import TinyFX

from picofx import MonoPlayer, ease
from picofx.mono import TrafficLightFX

"""
Play a traffic light sequence on Tiny FX's outputs.

The three lights ease on and off like the filament lamps of a real signal. The easing
is set on the player, so it works the same for any effect.

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                                     # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)                   # Create a new effect player to control Tiny FX's mono outputs


# Effects
traffic = TrafficLightFX(red_interval=5,            # The time (in seconds) to stay on Red
                         red_amber_interval=2.5,    # The time (in seconds) to stay on Red+Amber
                         green_interval=5,          # The time (in seconds) to stay on Green
                         amber_interval=2.5)        # The time (in seconds) to stay on Amber


# How long each output takes to reach its level. One value covers all, along a warming filament's curve
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
