from sensor import PIR
from timing import Roller
from tiny_fx import TinyFX

from picofx import MonoPlayer
from picofx.mono import BlinkFX, PulseFX, RandomFX, StaticFX

"""
Play effects for each space themed "postcard" when someone walks past.
A PIR sensor is used to activate the effect, which will turn off after a certain time.

Press "Boot" to exit the program.
"""

# Constants
PIR_TIMEOUT = 10      # The time to wait before turning off the lights after the PIR sensor stops detecting motion (in seconds)

# Variables
tiny = TinyFX(sensor=PIR)           # Create a new TinyFX object, with a PIR on its sensor connector
player = MonoPlayer(tiny.outputs)   # Create a new effect player to control TinyFX's mono outputs

# Take the PIR sensor the board set up on its sensor connector
pir = tiny.sensor

# Set up the effects to play
player.effects = [
    PulseFX(speed=0.2),
    RandomFX(interval=0.01, brightness_min=0.5, brightness_max=1.0),
    StaticFX(brightness=0.5),
    BlinkFX(speed=0.5),
    None,
    None
]

# When to turn off the lights, pushed back each time the PIR sensor detects motion
lights_out = Roller(PIR_TIMEOUT)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    # Loop until the "Boot" button is pressed
    while not tiny.boot_pressed():

        # Has motion been detected?
        if pir.value() == 1:
            player.start()   # Start the effects running
            lights_out.restart()

        if player.is_running() and lights_out.is_due():
            player.stop(reset_fx=True)
            tiny.clear()

# Stop any running effects and turn off all the outputs
finally:
    player.stop()
    tiny.shutdown()
