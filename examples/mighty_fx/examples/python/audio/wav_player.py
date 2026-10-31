from mighty_fx import MightyFX

from picofx.colour import GREEN

"""
Play a WAV file saved locally to Mighty FX.

Output 4 is a quarter white while the board waits and green while a file plays. A press
before the white appears is not seen, so the light says when the button is live.

Press "Boot" to play the file, and again to stop it.
"""

# Constants
WAV_FILE = "My_File.wav"
WAV_ROOT = "/"
PLAYING_COLOUR = GREEN                  # Bright enough to read across a room, and not a warning colour
READY_COLOUR = (64, 64, 64)             # A quarter white, dim enough that playing stands out against it

# Variables
mighty = MightyFX(wav_root=WAV_ROOT)    # Create a new MightyFX object and tell it where the wav file is located


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    mighty.four.set_rgb(*READY_COLOUR)  # The button is live from here

    # Loop forever
    while True:
        # Has the boot button been tapped? Caught by interrupt, so a tap while a file starts still counts
        if mighty.boot_taps():
            # Is nothing playing?
            if not mighty.wav.is_playing():
                mighty.wav.play_wav(WAV_FILE)   # Play the file
                mighty.four.set_rgb(*PLAYING_COLOUR)  # Light output 4, so silence is not mistaken for a fault
                print("Playing the WAV file")
            else:
                mighty.wav.stop()               # Stop the file that is currently playing
                print("Stopping playback")

        # Has the file stopped playing?
        if not mighty.wav.is_playing():
            mighty.four.set_rgb(*READY_COLOUR)  # Back to waiting

# Turn off all the outputs and audio
finally:
    mighty.shutdown()
