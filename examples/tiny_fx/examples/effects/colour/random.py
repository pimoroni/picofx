from tiny_fx import TinyFX
from picofx import MonoPlayer
from picofx.mono import RandomFX

"""
Play a randomly changing brightness and colour effect on TinyFX's RGB output.

Press "Boot" to exit the program.
"""

# Constants
INTERVAL = 0.2                          # The time (in seconds) between each random brightness
BRIGHTNESS_MIN = 0.0                    # The min brightness to randomly go down to
BRIGHTNESS_MAX = 1.0                    # The max brightness to randomly go up to


# Variables
tiny = TinyFX()                         # Create a new TinyFX object to interact with the board
player = MonoPlayer([tiny.rgb.led_r,    # Create a new effect player to control TinyFX's RGB output as mono outputs
                     tiny.rgb.led_g,
                     tiny.rgb.led_b])


# Create and set up a blink effect to play
player.effects = [
    RandomFX(interval=INTERVAL,
             brightness_min=BRIGHTNESS_MIN,
             brightness_max=BRIGHTNESS_MAX),
    RandomFX(interval=INTERVAL,
             brightness_min=BRIGHTNESS_MIN,
             brightness_max=BRIGHTNESS_MAX),
    RandomFX(interval=INTERVAL,
             brightness_min=BRIGHTNESS_MIN,
             brightness_max=BRIGHTNESS_MAX)
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
