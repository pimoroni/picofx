from tiny_fx import TinyFX

from picofx.colour import GREEN

"""
Play a WAV file saved locally to the Tiny FX

The RGB output says which state the board is in: a quarter white while it waits, and
green while a file plays. The board takes a moment to start, and a press before the
white appears is not seen, so the light is what says the button is live.

Press Boot to power up, and press Boot to power down
"""

# Constants
WAV_FILE = "My_File.wav"
WAV_ROOT = "/"
PLAYING_COLOUR = GREEN          # Bright enough to read across a room, and not a warning colour
READY_COLOUR = (64, 64, 64)     # A quarter white, dim enough that playing stands out against it

# Variables
tiny = TinyFX(wav_root=WAV_ROOT)    # Create a new TinyFX object and tell it where the wav file is located


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    tiny.rgb.set_rgb(*READY_COLOUR)     # The button is live from here

    # Loop forever
    while True:
        # Has the boot button been tapped? Caught by interrupt, so a tap during
        # the pause a file takes to start counts rather than being read over
        if tiny.boot_taps():
            # Is nothing playing?
            if not tiny.wav.is_playing():
                tiny.wav.play_wav(WAV_FILE)     # Play the file
                tiny.rgb.set_rgb(*PLAYING_COLOUR)   # Light the RGB output, so silence is not mistaken for a fault
                print("Playing the WAV file")
            else:
                tiny.wav.stop()                 # Stop the file that is currently playing
                print("Stopping playback")

        # Has the file stopped playing?
        if not tiny.wav.is_playing():
            tiny.rgb.set_rgb(*READY_COLOUR)     # Back to waiting

# Turn off all the outputs and audio
finally:
    tiny.shutdown()
