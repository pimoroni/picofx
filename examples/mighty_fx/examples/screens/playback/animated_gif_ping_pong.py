# Plays an animated GIF forward then back, dwelling at each turn.
#
# ping_pong walks the frames forward then back, so an animation with two ends, such as an arm flexing, never
# jumps from its last frame to its first. An animation drawn to loop has no such ends, its last frame leading
# back into its first, so first_as_last plays that first frame again at the far end: the coin then spins a
# whole turn each way, where without it the turn comes a frame early and lands mid-spin.
#
# hold is the wait where it turns around, one value for both ends or two, the far end and then back at the
# start. Both ends are the same picture here, the coin face, so one value keeps the two pauses even: it spins,
# rests face on, unwinds, and rests face on again. Those dwells come out of the reported rate, so
# measured_fps() against target_fps() still compares the frames themselves rather than the pauses between them.

from mighty_fx import MightyFX, SPCE
from playback import GIFPlayer
from screens import Screen280

# Constants
GIF_PATH = "/examples/assets/pirate_coin.gif"   # The GIF to play, beside this example
ROTATION = 90                    # Quarter turn, to suit how the screen is mounted
HOLD = 1.0                       # Seconds to dwell at each end, both being the coin face

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# ping_pong needs somewhere to turn around, so it only applies to a player that repeats, and
# first_as_last needs a turn to put its extra frame at, so a plain forward loop refuses it
player = GIFPlayer(GIF_PATH, ping_pong=True, first_as_last=True, hold=HOLD)

# The ground the file was authored over, read from its own corner, so the panel matches it
ground = player.image.get(0, 0)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The screen refreshes faster than the GIF changes, so only send a new frame
        if player.has_advanced():
            screen.update(player.image, rotation=ROTATION, bg_color=ground)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
