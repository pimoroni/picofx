from tiny_fx import TinyFX
from picofx import MonoPlayer
from picofx.mono import TrafficLightFX

"""
Play a traffic light sequence on TinyFX's outputs.

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                                     # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)                   # Create a new effect player to control TinyFX's mono outputs


# Effects
traffic = TrafficLightFX(red_interval=5,            # The time (in seconds) to stay on Red
                         red_amber_interval=2.5,    # The time (in seconds) to stay on Red+Amber (or Amber Flashing if enabled)
                         green_interval=5,          # The time (in seconds) to stay on Green
                         amber_interval=2.5,        # The time (in seconds) to stay on Amber
                         fade_rate=0.01,            # How quickly the lights respond to changes. Low values are more like bulbs
                         amber_flashing=False)      # Whether to have Amber be flashing rather than Red+Amber, as some traffic lights use


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
