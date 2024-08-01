import time
from tiny_fx import TinyFX
from picofx.colour import WHITE

"""
Plays a simple boop, boop, boop, beeep countdown sound effect when
you press Boot on TinyFx. Great for counting down to a race start.

Plug a red LED into port 1 and a green LED into port 2.
"""

# Constants
TONES = (440, 440, 440, 880, 0)         # The tones to play in order (0 means silence)
DURATIONS = (0.5, 0.5, 0.5, 1.5, 2.0)   # The duration of each tone (in seconds)
OUTPUTS = (1, 1, 1, 2, 0)               # Which output to light with each tone

# Variables
tiny = TinyFX()                 # Create a new TinyFX object to interact with the board

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    # Loop forever
    while True:
        tiny.rgb.set_rgb(*WHITE)    # Show that the program is ready

        # Wait for the Boot button to be pressed
        while not tiny.boot_pressed():
            pass
        tiny.clear()                # Show that the program is running

        # Loop through all the tones
        for i in range(len(TONES)):
            tone = TONES[i]
            duration = DURATIONS[i]
            output = OUTPUTS[i]

            # Play the next tone
            if tone:
                tiny.wav.play_tone(tone, 1.0, tiny.wav.TONE_SQUARE)

            # Turn on just the output for the next tone
            tiny.clear()
            if output:
                tiny.outputs[output - 1].on()

            # Wait for the tone's duration before stopping
            time.sleep(duration)
            tiny.wav.stop()

            # Pause between each tone if not silence
            if tone:
                time.sleep(0.1)

# Turn off all the outputs and audio
finally:
    tiny.shutdown()
