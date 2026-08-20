import time

from mighty_fx import MightyFX

from picofx import StripPlayer
from picofx.colour import RainbowWaveFX

"""
Run a rainbow along an LED strip on the L connector.

Plug a WS2812 strip into the connector marked L and set LEDS below to however many it
has, since that is the one thing the board cannot work out for itself. Both L and R
share one power rail, so anything on R is live too. Press "Boot" to exit the program.

A strip takes the same effects the RGB outputs do, one per LED, so anything under
picofx.colour or picofx.mono can play here.
"""

# Constants
LEDS = 60               # How many LEDs the strip has
SPEED = 0.3             # How fast the rainbow travels along it


# Variables
mighty = MightyFX(strip_l=LEDS)                     # Create a new MightyFX object, with a strip on L
player = StripPlayer(mighty.strip_l, LEDS)          # Create a new effect player to control the strip

# One effect per LED, each reading the same wave from a position of its own
wave = RainbowWaveFX(speed=SPEED, length=LEDS)
player.effects = [wave(position) for position in range(LEDS)]


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()                                  # Start the effects running

    while not mighty.boot_pressed():
        time.sleep(0.01)

# Stop the effects, darken the strip, drop the connectors' power and turn off all the outputs
finally:
    player.stop()
    mighty.shutdown()
