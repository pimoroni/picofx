import time
from machine import Pin
from mighty_fx import MightyFX, SPCE

"""
Borrow a SP/CE connector's five pins as general purpose outputs, and chase a high along them.

Wire an LED and resistor, or a scope probe, to the pins named below. Press "Boot" to exit the program.
"""

# Constants
STEP_INTERVAL = 0.2     # The time (in seconds) each pin is held high for


# Variables
mighty = MightyFX(spce_a=SPCE.GPIO)     # Create a new MightyFX object, spending SP/CE port A on pins

# The connector's five GPIOs, in the order DC, CS, SCK, MOSI, BL. Only a port declared
# SPCE.GPIO or SPCE.GPIO_PWM hands them over, so a connector given up for pins is visible
# in the call that declared it, and nothing else on the board can claim them behind your back
lines = mighty.spce_a.pins

# Take every line low to start with
for line in lines:
    line.init(Pin.OUT)
    line.low()


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    position = 0

    while not mighty.boot_pressed():
        # Take one line high and the rest low, moving along by one each time round
        for index, line in enumerate(lines):
            line.value(index == position)

        position = (position + 1) % len(lines)
        time.sleep(STEP_INTERVAL)

# Take the lines low again and turn off all the outputs
finally:
    for line in lines:
        line.low()

    mighty.shutdown()
