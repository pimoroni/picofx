from mighty_fx import MightyFX

"""
Play a WAV file saved locally to the Mighty FX

Press Boot to power up, and press Boot to power down
"""

# Constants
WAV_FILE = "My_File.wav"
WAV_ROOT = "/"

# Variables
mighty = MightyFX(wav_root=WAV_ROOT)    # Create a new MightyFX object and tell with where the wav file is located
last_button_state = False               # The last states of the boot button


# Function to check if the boot button has been newly pressed
def boot_newly_pressed():
    global last_button_state
    button_state = mighty.boot_pressed()
    button_pressed = button_state and not last_button_state
    last_button_state = button_state

    return button_pressed


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    # Loop forever
    while True:
        # Has the boot button been pressed?
        if boot_newly_pressed():
            # Is nothing playing?
            if not mighty.wav.is_playing():
                mighty.wav.play_wav(WAV_FILE)   # Play the file
                mighty.enable_servo_strip()     # Turn on the servo/strip LED
                print("Playing the WAV file")
            else:
                mighty.wav.stop()               # Stop the file that is currently playing
                print("Stopping playback")

        # Has either file stopped playing?
        if not mighty.wav.is_playing():
            mighty.disable_servo_strips()       # Turn off the servo/strip LED

# Turn off all the outputs and audio
finally:
    mighty.shutdown()
