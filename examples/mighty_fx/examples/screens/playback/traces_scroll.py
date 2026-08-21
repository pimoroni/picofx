from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280

"""
Scroll an animation endlessly across the panel, from a single tile of it.

The pattern is drawn to tile, so the column after its last is its first. tile= has the
driver read it that way: a window past the tile's end shows its start again, so the offset
can grow for ever and the tile goes straight to the panel, with no canvas, blits or
wrap-around bookkeeping.

Nothing here waits for the player: the field moves every frame even when the animation has
not, so there is no has_advanced() to ask. The animation runs on the player's clock and
the scroll on the frame count, which is why the pattern can live at 8fps while the field
glides a couple of pixels a frame.

Press "Boot" to exit the program.
"""

# Constants
FRAMES = "/examples/assets/traces"   # The folder of frames, shared with the wall example
ROTATION = 90                    # Quarter turn, to suit how the screen is mounted
FPS = 8                          # The rate the pattern itself animates at
STEP = 2                         # Pixels the field travels each frame

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

player = SequencePlayer(FRAMES, fps=FPS)
PERIOD = player.image.width      # The tile, and so how far the field travels before it repeats
print(f"{player.frames} frames of {PERIOD}px, {STEP}px a frame")

frames = 0

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The tile fills the panel wherever the field has reached, the read wrapping at its own width
        screen.update(player.image, rotation=ROTATION, tile=(True, False),
                      offset=(-frames * STEP, None))
        frames += 1

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
