from machine import Pin
from mighty_fx import MightyFX, SPCE
from timing import Pacer

"""
Read buttons wired to a SP/CE port's five pins, brightening an RGB output while each is held.

Wire up to five buttons, each between one of SP/CE A's BL, DC, MOSI, SCK and CS lines and
ground. Each pin pulls itself high, so no resistors are needed, and a held button reads low.
The first five outputs glow dim in a colour each, and brighten while their buttons are held,
in the pins' order along the connector from its GND end, so no screen is needed.

Press "Boot" to exit the program.
"""

# Constants
# The colour of each output in turn, one for each pin along the connector
COLOURS = (
    (255, 64, 0),       # Brown
    (160, 0, 255),      # Purple
    (0, 0, 255),        # Blue
    (0, 255, 0),        # Green
    (255, 180, 0),      # Yellow
)
DIM = 0.12             # How bright an output glows while its button is up (from 0.0 to 1.0)
BRIGHT = 1.0            # And while its button is held
INTERVAL = 0.02         # How often the buttons are read, in seconds


# Variables
mighty = MightyFX(spce_a=SPCE.GPIO)     # Create a new MightyFX object, spending SP/CE port A on pins

# The port's five GPIOs in the order they sit along the connector, BL, DC, MOSI, SCK, CS,
# so the outputs light in the order the pins sit. Each is taken as an input held high
buttons = mighty.spce_a.pins_along
for button in buttons:
    button.init(Pin.IN, Pin.PULL_UP)

pacer = Pacer(INTERVAL)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        for button, output, (r, g, b) in zip(buttons, mighty.outputs, COLOURS):
            # A held button joins its pin to ground, so it reads low
            level = BRIGHT if button.value() == 0 else DIM
            output.set_rgb(r * level, g * level, b * level)

        pacer.hold()

# Turn off all the outputs
finally:
    mighty.shutdown()
