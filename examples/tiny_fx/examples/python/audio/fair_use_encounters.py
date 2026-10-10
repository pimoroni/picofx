import time

from sensor import ANALOG
from tiny_fx import TinyFX

from picofx.colour import BLACK, BLUE, CYAN, GREEN, RED, YELLOW

"""
Play an evocative musical melody with accompanying lights on TinyFX.
Any resemblance to music you might have heard elsewhere is purely coincidental.

Press "Boot" to exit the program.
"""

# Constants
TONES = (588, 658, 524, 262, 384, 0)            # The tones to play in order (0 means silence)
VOLUME = (0.7, 0.5, 0.7, 1.0, 0.9, 0)           # The volume of each tone to play (tune to your speaker)
DURATIONS = (0.6, 0.6, 0.6, 0.6, 0.6 * 4, 2.0)  # The duration of each tone (in seconds)
OUTPUTS = (2, 3, 1, 6, 4, 0)                    # Which output to light with each tone
RGBS = (CYAN, BLUE, GREEN, RED, YELLOW, BLACK)  # Which R, G, B colours to show for each tone

USE_SENSOR = False              # Whether to use an analog sensor to control the speed of the melody
MAX_SPEED = 20                  # The maximum speed multiplier that the melody will play at
SAMPLES = 5                     # The number of measurements to take of the analog sensor, to reduce noise

# Variables
tiny = TinyFX(sensor=ANALOG if USE_SENSOR else None)    # Create a new TinyFX object, with the sensor only where one is wired
index = 0                       # The index of the tone to play

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not tiny.boot_pressed():
        tone = TONES[index]
        output = OUTPUTS[index]

        speed = 1.0
        if USE_SENSOR:
            # Read the voltage output by the sensor and convert it to a speed
            speed = (tiny.sensor.read_voltage(SAMPLES) * (MAX_SPEED - 1) / 3.3) + 1

            # Print out the speed value to a sensible number of decimal places
            print("Speed =", round(speed, 2))

        # Play the next tone
        if tone:
            tiny.wav.play_tone(tone, VOLUME[index])

        # Turn on just the output for the next tone
        tiny.clear()
        if output:
            tiny.outputs[output - 1].on()

        # Set the RGB output to a colour for the tone
        tiny.rgb.set_rgb(*RGBS[index])

        # Wait for the tone's duration before stopping
        time.sleep(DURATIONS[index] / speed)
        tiny.wav.stop()

        # Pause between each tone
        time.sleep(0.1 / speed)

        # Move on to the next tone and light
        index += 1
        index %= len(TONES)

# Turn off all the outputs and audio
finally:
    tiny.shutdown()
