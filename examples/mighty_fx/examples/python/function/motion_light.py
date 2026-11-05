from mighty_fx import MightyFX
from sensor import PIR
from timing import Pacer

from picofx.colour import WARM

"""
Fade Mighty FX's RGB outputs up while a PIR sensor on the sensor connector sees motion,
and back down once it stops.

With no sensor plugged in, the connector reads as motion and the outputs stay lit.

Press "Boot" to exit the program.

Section: With a sensor
Thumbnail: outputs warm
"""

# Constants
COLOUR = WARM       # The colour to light the outputs
RISE = 0.5          # How long the outputs take to fade up, in seconds, under the 2s a PIR Stick holds for
FADE = 0.5          # How long the outputs take to fade out, in seconds
INTERVAL = 0.02     # How often to read the sensor and update the outputs, in seconds

# Variables
mighty = MightyFX(sensor=PIR)   # Create a new MightyFX object, with a PIR sensor on its connector
pir = mighty.sensor             # Take the PIR sensor the board set up on its sensor connector
level = 0.0                     # How brightly the outputs are lit, from 0.0 to 1.0

pacer = Pacer(INTERVAL)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Has motion been seen? If so, fade a step at a time up to full
        if pir.value() == 1:
            if level == 0.0:
                print("Motion seen, lights on")
            level = min(1.0, level + INTERVAL / RISE)

        # With none, fade a step at a time until the outputs are out
        elif level > 0.0:
            level = max(0.0, level - INTERVAL / FADE)
            if level == 0.0:
                print("No motion, lights out")

        for output in mighty.outputs:
            output.set_rgb(*(channel * level for channel in COLOUR))

        pacer.hold()

# Turn off all the outputs
finally:
    mighty.shutdown()
