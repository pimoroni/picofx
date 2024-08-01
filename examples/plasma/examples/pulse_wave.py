import plasma
from plasma import plasma2040
from picofx import StripPlayer
from picofx.mono import PulseWaveFX
from pimoroni import Button

"""
Play a wave of pulses on Plasma 2040's strip output.
This is an *experimental* feature, that can struggle when
complex effects with high update rates are applied to many LEDs.

Press "Boot" to exit the program.
"""

# Constants
NUM_LEDS = 60       # How many LEDs are on the connected Strip
SPEED = 0.2         # The speed to cycle the pulses at, with 1.0 being 1 second
UPDATES = 30        # How many times the LEDs and effects updated per second


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

# Create a PulseWaveFX effect
wave = PulseWaveFX(speed=SPEED, length=NUM_LEDS)

# Set up the wave effect to play, mirrored at the middle of the strip.
# Each output has a different position along the wave, with the value being related to the effect's length
player.effects = [wave(i) for i in range(NUM_LEDS)]


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
