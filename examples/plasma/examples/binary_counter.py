import plasma
from plasma import plasma2040
from picofx import StripPlayer
from picofx.mono import BinaryCounterFX
from pimoroni import Button

"""
Play a binary counter effect on Plasma 2040's strip output.
This is an *experimental* feature, that can struggle when
complex effects with high update rates are applied to many LEDs.

Press "Boot" to exit the program.
"""

# Constants
NUM_LEDS = 60       # How many LEDs are on the connected Strip
INTERVAL = 0.1      # The time (in seconds) between each increment of the binary counter
UPDATES = 60        # How many times the LEDs and effects updated per second


# Variables
boot = Button(plasma2040.USER_SW)

# Pick *one* LED type by uncommenting the relevant line below:

# APA102 / DotStar™ LEDs
# strip = plasma.APA102(NUM_LEDS, 0, 0, plasma2040.DAT, plasma2040.CLK)

# WS2812 / NeoPixel™ LEDs
strip = plasma.WS2812(NUM_LEDS, 0, 0, plasma2040.DAT,
                      color_order=plasma.COLOR_ORDER_RGB)

# Create a new effect player to control the LED strip
player = StripPlayer(strip, num_leds=NUM_LEDS)

# Create a BinaryCounterFX effect
binary = BinaryCounterFX(interval=INTERVAL)

# Set up the binary counter effect to play, mirrored at the middle of the strip.
player.effects = [
    binary(i) for i in range(NUM_LEDS // 2)
] + [
    binary(NUM_LEDS // 2 - 1 - i) for i in range(NUM_LEDS // 2)
]


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    strip.start(UPDATES)    # Start updating the LED strip
    player.start(UPDATES)   # Start the effects running, with a lower update rate than normal

    # Loop until the effect stops or the "Boot" button is pressed
    while player.is_running() and not boot.raw():
        pass

# Stop any running effects and turn off the LED strip
finally:
    player.stop()
    strip.clear()
