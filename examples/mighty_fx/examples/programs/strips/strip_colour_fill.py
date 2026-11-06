from mighty_fx import MightyFX
from timing import Pacer

"""
Fill an LED strip red, then green, then blue, one LED at a time, by setting each LED directly.

Plug a WS2812 strip into the connector marked L and set LEDS below to however many it
has. Each LED is given its colour from this program, with no effect player, and the strip
shows what it has been given only when update() is called.

Pure red, green and blue are the test for the order a strip takes its colours in. If the
green fill shows as red, change ORDER to match the strip, such as "rgb".

Press "Boot" to exit the program.
"""

# Constants
LEDS = 60               # How many LEDs the strip has
ORDER = "grb"           # The order the strip takes its red, green and blue in, which is most WS2812 strips'
STEP = 0.02             # The time (in seconds) between lighting one LED and the next
LEVEL = 64              # How bright each fill is (from 0 to 255), low enough for a long strip on the rail
FILLS = ((LEVEL, 0, 0), (0, LEVEL, 0), (0, 0, LEVEL))   # Red, green and blue, in turn


# Variables
mighty = MightyFX(strip_l=(LEDS, ORDER))            # Create a new MightyFX object, with a strip on L
strip = mighty.strip_l

mighty.enable_rail()                                # Power the L and R connectors, which stay off until asked

pacer = Pacer(STEP)
fill = 0                # Which of the fills is being drawn
lit = 0                 # And how many LEDs it has reached


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        strip.set_rgb(lit, *FILLS[fill])
        strip.update()                              # Send the strip what it has been given, which is when it shows

        lit += 1
        if lit == LEDS:
            # The strip is full, so the next colour starts again from the first LED
            lit = 0
            fill = (fill + 1) % len(FILLS)

        pacer.hold()

# Darken the strip, drop the connectors' power and turn off all the outputs
finally:
    mighty.shutdown()
