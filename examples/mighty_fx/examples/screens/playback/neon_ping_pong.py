# Plays an animation held as one image file per frame, back and forth.
#
# A GIF carries its frames and their delays in one file, which is convenient and caps it at 256 colours. A
# folder of images has neither limit and no delays either, so the player is told a rate. Frames are ordered by
# the numbers in their names, and an export numbering past nine without padding still plays in order.
#
# Three frames make an animation here because it turns around rather than repeating: ping_pong plays them
# forward then back, so three files give six steps of movement and the arm flexes and releases. hold adds a
# dwell where it turns, which is what stops the far end reading as a bounce.
#
# The arm has two ends and genuinely stops at each, so nothing belongs at the turn. An animation drawn to loop
# does want something there, which is what first_as_last is for.
#
# Every frame decodes into the heap at construction, so a sequence costs its whole length in memory before it
# plays a step. Three truecolour frames of this size are about 900KB; a long sequence wants exporting half
# size and indexed, then drawn back with pixel_double.

from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280

# Constants
FRAMES = "/examples/assets/rosie"   # The folder of frames, beside this example
ROTATION = 90                    # Quarter turn, to suit how the screen is mounted
FPS = 8                          # The rate to play at, a folder of images declaring none
HOLD = 0.4                       # Seconds to dwell where it turns around, at each end

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# ping_pong walks the frames forward then back, so the animation never jumps from its last
# frame to its first. hold takes one value for both ends, or two for the far end and the start
player = SequencePlayer(FRAMES, fps=FPS, ping_pong=True, hold=HOLD)
print(f"{player.frames} frames, played back and forth at {FPS}fps")

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The screen refreshes faster than the animation changes, so only send a new frame
        if player.has_advanced():
            screen.update(player.image, rotation=ROTATION)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
