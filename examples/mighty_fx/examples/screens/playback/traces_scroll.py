# Scrolls an animation endlessly across the panel, from a source no bigger than the panel itself.
#
# The pattern is drawn to tile, so the column after its last is its first. That is what lets it scroll for ever:
# the window is taken as two pieces, the far end of the tile and then its start, and where those meet is where
# the tile already met itself.
#
# The driver's own offset= would do this in one step and cost nothing, but it cannot wrap: a window past the end
# of a source shows the background instead of starting again. Giving it a source two tiles wide fixes that and
# costs a second copy of the art, which is what this avoids. Two blits into a canvas cost about 11ms, and a
# canvas is truecolour where a tile is indexed, so a frame lands in 67ms rather than 44ms. That buys back 163KB
# of flash and 600KB of heap.
#
# Nothing here waits for the player: the field moves every frame even when the animation has not, so there is no
# has_advanced() to ask. The animation runs on the player's clock and the scroll on the loop's, which is why the
# pattern can live at 8fps while the field glides two or three pixels a frame.

import time

from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280
from picovector import rect

# Constants
FRAMES = "/examples/assets/traces"   # The folder of frames, shared with the wall example
ROTATION = 90                    # Quarter turn, to suit how the screen is mounted
FPS = 8                          # The rate the pattern itself animates at
ACROSS_MS = 8000                 # How long the field takes to travel one tile

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# The canvas is a whole panel, which at a quarter turn is exactly one tile
canvas = screen.canvas(screen.height, screen.width)

player = SequencePlayer(FRAMES, fps=FPS)
PERIOD = player.image.width      # The tile's repeat, and so where the scroll comes back on itself
print(f"{player.frames} frames of {PERIOD}px, travelling one tile every {ACROSS_MS}ms")

started = time.ticks_ms()

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        elapsed = time.ticks_diff(time.ticks_ms(), started)
        at = (elapsed * PERIOD // ACROSS_MS) % PERIOD
        rest = PERIOD - at

        # The tile from where the field has reached, then as much of its start as is left over
        canvas.blit(player.image, rect(at, 0, rest, canvas.height), rect(0, 0, rest, canvas.height))
        if at:
            canvas.blit(player.image, rect(0, 0, at, canvas.height), rect(rest, 0, at, canvas.height))

        screen.update(canvas, rotation=ROTATION)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
