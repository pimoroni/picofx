import time

from mighty_fx import MightyFX

from picofx.colour import GREEN, RED

"""
Plays a simple boop, boop, boop, beeep countdown sound effect when
you press Boot on MightyFx. Great for counting down to a race start.

Every output shows a colour, so the countdown lights output 1 red and the start
lights output 2 green without either needing an LED of that colour in it.
"""

# Constants
TONES = (440, 440, 440, 880, 0)         # The tones to play in order (0 means silence)
DURATIONS = (0.5, 0.5, 0.5, 1.5, 2.0)   # The duration of each tone (in seconds)
OUTPUTS = (1, 1, 1, 2, 0)               # Which output to light with each tone (0 means none)
COLOURS = (RED, RED, RED, GREEN, RED)   # Which colour to light that output in

# Variables
mighty = MightyFX()             # Create a new MightyFX object to interact with the board

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    # Loop forever
    while True:
        # Show that the program is ready
        for output in mighty.outputs:
            output.on()

        # Wait for the Boot button to be pressed
        while not mighty.boot_pressed():
            pass
        mighty.clear()              # Show that the program is running

        # Loop through all the tones
        for i in range(len(TONES)):
            tone = TONES[i]
            duration = DURATIONS[i]
            output = OUTPUTS[i]

            # Play the next tone
            if tone:
                mighty.wav.play_tone(tone, 1.0, mighty.wav.TONE_SQUARE)

            # Light just the output for the next tone, in that tone's colour
            mighty.clear()
            if output:
                mighty.outputs[output - 1].set_rgb(*COLOURS[i])

            # Wait for the tone's duration before stopping
            time.sleep(duration)
            mighty.wav.stop()

            # Pause between each tone if not silence
            if tone:
                time.sleep(0.1)

# Turn off all the outputs and audio
finally:
    mighty.shutdown()
