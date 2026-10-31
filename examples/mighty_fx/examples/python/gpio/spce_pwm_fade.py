import math
from machine import PWM
from mighty_fx import MightyFX, SPCE
from timing import Pacer

"""
Fade four LEDs on a SP/CE port's data lines with PWM, and report which output channels
that costs.

Wire four LEDs, each with a series resistor, from SP/CE B's DC, MOSI, SCK and CS lines to
ground. Every one of those lines shares its PWM channel with an LED channel of an output,
so declaring the port SPCE.GPIO_PWM hands the channels to the port and leaves the outputs'
shared channels dark. Declared SPCE.GPIO, the same PWM would take them with no warning.

Press "Boot" to exit the program.
"""

# Constants
FREQUENCY = 1000        # The PWM frequency, in Hz, fast enough not to flicker
PERIOD = 2.0            # How long one LED takes to fade up and back down, in seconds
INTERVAL = 0.02         # How often the brightness is updated, in seconds


# Variables
mighty = MightyFX(spce_b=SPCE.GPIO_PWM)     # Create a new MightyFX object, spending SP/CE port B on PWM pins

# Every output channel the port's PWM costs. Each one left behind is a stand-in that stays dark,
# and its in_use_by says why, where a channel free to light has None
for number, output in enumerate(mighty.outputs, start=1):
    for colour, led in zip(("red", "green", "blue"), output.leds):
        if led.in_use_by is not None:
            print(f"Output {number} gives up its {colour} channel")

# PWM on the port's four data lines, DC, MOSI, SCK and CS in the order they sit along the connector, so
# the ripple follows them. BL comes first along it and stays a plain line, claiming no channel
leds = [PWM(pin, freq=FREQUENCY, duty_u16=0) for pin in mighty.spce_b.pins_along[1:]]

pacer = Pacer(INTERVAL)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        seconds = pacer.elapsed / 1000

        # Each LED a quarter of a fade behind the one before, so the brightness ripples along them
        for index, led in enumerate(leds):
            phase = seconds / PERIOD - index / len(leds)
            level = 0.5 - 0.5 * math.cos(2 * math.pi * phase)
            led.duty_u16(int(level * 65535))

        pacer.hold()

# Turn the LEDs off, hand their pins back and turn off all the outputs
finally:
    for led in leds:
        led.deinit()

    mighty.shutdown()
