from mighty_fx import MightyFX, SPCE
from playback import GIFPlayer
from screens import Screen280

"""
Play an animated GIF on a screen, at the frame delays the file was authored with.

The coin was drawn for this panel, its colours already sitting on the 16 levels a channel
resolves. A photograph exported straight to a GIF has colours between those levels and
bands into patches instead.

It is square, so the panel shows a background around it. The coin's rim is almost black
and would meet a dark ground invisibly, so it sits on a middle grey, and the panel is
given the same grey by reading the file's own corner. Naming a different GIF above
therefore still lands on its own ground.

Press "Boot" to exit the program.
"""

# Constants
GIF_PATH = "/examples/assets/pirate_coin.gif"   # The GIF to play, beside this example

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it.
# rotation is how the panel is mounted, which every frame then takes without naming it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a, rotation=90)

# A GIF carries a delay for each frame but no clock, so a player is what walks them. The
# default plays at the file's own delays; fps=12 would name a rate instead
player = GIFPlayer(GIF_PATH)

# A decoded frame is palettised, and get() resolves that and hands back a colour
ground = player.image.get(0, 0)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The screen refreshes faster than the GIF changes, so only send a new frame
        if player.has_advanced():
            screen.update(player.image, bg_color=ground)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
