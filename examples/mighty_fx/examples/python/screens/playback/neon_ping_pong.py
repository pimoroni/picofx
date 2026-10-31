from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280

"""
Play an animation held as one image file per frame, back and forth.

A GIF carries its frames and their delays in one file, and caps itself at 256 colours. A
folder of images has neither limit and no delays either, so the player is told a rate, and
frames are ordered by the numbers in their names rather than by the text.

ping_pong plays them forward then back, so three files give six steps. hold dwells at each turn.

Every frame decodes when the player is made. Truecolour takes four times an indexed frame's memory.

Press "Boot" to exit the program.
"""

# Constants
FRAMES = "/examples/assets/rosie"   # The folder of frames
ROTATION = 90                    # Quarter turn, to suit how the screen is mounted
FPS = 8                          # The rate to play at, a folder of images declaring none
HOLD = 0.4                       # Seconds to dwell where it turns around, at each end

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a, rotation=ROTATION)

# hold takes one value for both ends, or two for the far end and then back at the start
try:
    player = SequencePlayer(FRAMES, fps=FPS, ping_pong=True, hold=HOLD)
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{FRAMES}' is missing! Check it is on the board") from None

print(f"{player.frames} frames, played back and forth at {FPS}fps")

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The screen refreshes faster than the animation changes, so only send a new frame
        if player.has_advanced():
            screen.update(player.image)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
