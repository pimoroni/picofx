import math

from mighty_fx import MightyFX, SPCE
from picovector import tween
from playback import SequencePlayer
from screens import Screen280

"""
Scroll an animation endlessly across the panel, from a single tile of it, turning between
the two axes.

The pattern is drawn to tile both ways, so the column after its last is its first and so is
the row. tile= has the driver read it that way: a window past the tile's end shows its start
again, so the offset can grow for ever and the tile goes straight to the panel, with no
canvas, blits or wrap-around bookkeeping.

The field runs along one axis, eases round onto the other, and back. A turn travels the same
whole number of pixels on both axes, and each run is shortened by two of them, so the axis a
turn leaves comes to rest a whole tile on, exactly where it started.

Nothing here waits for the player: the field moves every frame even when the animation has
not, so there is no has_advanced() to ask. The animation runs on the player's clock and
the scroll on the frame count, which is why the pattern can live at 8fps while the field
glides a couple of pixels a frame.

Press "Boot" to exit the program.

Section: Animation
"""

# Constants
FRAMES = "/examples/assets/traces"   # The folder of frames, shared with the wall example
ROTATION = 90                    # Quarter turn, to suit how the screen is mounted
FPS = 8                          # The rate the pattern itself animates at
STEP = 2                         # Pixels the field travels each frame
TURN = 50                        # Frames a change of direction takes

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

player = SequencePlayer(FRAMES, fps=FPS)
WIDE = player.image.width        # The tile, and so how far the field travels across before it repeats
TALL = player.image.height       # And down

# The steps the axis being left takes through a turn, falling from STEP to nothing as the
# heading eases round a quarter, scaled to total an even number of pixels since a run moves
# STEP at a time. The ease is symmetric, so the axis being joined takes the same in reverse
heading = tween(0.0, math.pi / 2, easing=tween.SINE_INOUT)
slowing = [STEP * math.cos(heading.at((frame + 0.5) / TURN)) for frame in range(TURN)]
TURNED = 2 * round(sum(slowing) / 2)                 # Pixels a turn travels on each axis
reached = [round(TURNED * sum(slowing[:frame + 1]) / sum(slowing)) for frame in range(TURN)]
leaving = [now - before for before, now in zip([0] + reached, reached)]
joining = leaving[::-1]
print(f"{player.frames} frames of {WIDE}x{TALL}, {STEP}px a frame, {TURNED}px a turn")


def moves():
    """A generator of each frame's step, across and down: a run, a turn, a run on the other axis, and a turn back."""
    # The vertical steps are negative, so a turn's diagonal runs the way the pulses travel
    while True:
        # A run and the turns either side of it make a whole tile
        for _ in range((WIDE - 2 * TURNED) // STEP):
            yield STEP, 0
        for left, joined in zip(leaving, joining):
            yield left, -joined
        for _ in range((TALL - 2 * TURNED) // STEP):
            yield 0, -STEP
        for left, joined in zip(leaving, joining):
            yield joined, -left


# Start a turn's width in, so the first run ends where a turn needs it to
across, down = TURNED, 0
steps = moves()

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The tile fills the panel wherever the field has reached, the read wrapping on both axes
        screen.update(player.image, rotation=ROTATION,
                      offset=(-across, -down), tile=(True, True))
        step_across, step_down = next(steps)
        across += step_across
        down += step_down

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
