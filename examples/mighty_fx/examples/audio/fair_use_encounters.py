import time

from machine import Pin
from mighty_fx import MightyFX
from pimoroni import Analog

from picofx.colour import BLACK, BLUE, CYAN, GREEN, RED, YELLOW

"""
Play an evocative musical melody with accompanying lights on MightyFX.
Any resemblance to music you might have heard elsewhere is purely coincidental.

Every output shows a colour, so each tone lights one output in a colour of its own,
where a board with mono outputs needs a separate one to carry the colour.

Press "Boot" to exit the program.
"""

# Constants
TONES = (588, 658, 524, 262, 384, 0)            # The tones to play in order (0 means silence)
VOLUME = (0.7, 0.5, 0.7, 1.0, 0.9, 0)           # The volume of each tone to play (tune to your speaker)
DURATIONS = (0.6, 0.6, 0.6, 0.6, 0.6 * 4, 2.0)  # The duration of each tone (in seconds)
OUTPUTS = (2, 3, 1, 6, 4, 0)                    # Which output to light with each tone (0 means none)
COLOURS = (CYAN, BLUE, GREEN, RED, YELLOW, BLACK)   # Which colour to light that output in

USE_SENSOR = False              # Whether to use an analog sensor to control the speed of the melody
MAX_SPEED = 20                  # The maximum speed multiplier that the melody will play at
SAMPLES = 5                     # The number of measurements to take of the analog sensor, to reduce noise

# Variables
mighty = MightyFX()             # Create a new MightyFX object to interact with the board
index = 0                       # The index of the tone to play

if USE_SENSOR:
    # Create a new Analog object for reading the sensor connector if the sensor is attached
    sensor = Analog(Pin(mighty.SENSOR_PIN))


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        tone = TONES[index]
        output = OUTPUTS[index]

        speed = 1.0
        if USE_SENSOR:
            # Read the voltage output by the sensor and convert it to a speed
            speed = (sensor.read_voltage(SAMPLES) * (MAX_SPEED - 1) / 3.3) + 1

            # Print out the speed value to a sensible number of decimal places
            print("Speed =", round(speed, 2))

        # Play the next tone
        if tone:
            mighty.wav.play_tone(tone, VOLUME[index])

        # Light just the output for the next tone, in that tone's colour
        mighty.clear()
        if output:
            mighty.outputs[output - 1].set_rgb(*COLOURS[index])

        # Wait for the tone's duration before stopping
        time.sleep(DURATIONS[index] / speed)
        mighty.wav.stop()

        # Pause between each tone
        time.sleep(0.1 / speed)

        # Move on to the next tone and light
        index += 1
        index %= len(TONES)

# Turn off all the outputs and audio
finally:
    mighty.shutdown()
