from mighty_fx import MightyFX, SPCE
from picovector import color
from playback import GIFPlayer
from screens import Reserve, Screen280

"""
Recolour a whole animation as it plays, by rewriting the one colour table its frames share.

A GIF's frames are indices into a table of colours, and every frame of a sheet reads the same
table, so writing an entry changes that colour in all of them at once. Here the scan sweeps
up in green, and each pass comes back in the colour of what it found.

Each entry keeps its own brightness as read once at the start, which keeps the glow and
antialiasing a flat colour would lose.

Press "Boot" to exit the program.

Section: Billboards and panels
"""

# Constants
GIF_PATH = "/examples/assets/medscan.gif"   # The GIF to play
ROTATION = 90                    # Quarter turn, to suit how the screen is mounted

# What each pass comes back as, the first near what the file was drawn in
REPORTS = (color.rgb(0, 255, 64), color.rgb(255, 196, 40),
           color.rgb(255, 64, 48), color.rgb(64, 200, 255))

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it with the
# reserve a source larger than the panel needs
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES, rotation=ROTATION)

# The scan runs body to skeleton, so it plays back and forth
try:
    player = GIFPlayer(GIF_PATH, ping_pong=True)
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{GIF_PATH}' is missing! Check it is on the board") from None

# The frames share one colour table, so this is the whole animation's colours
palette = player.palette

# How bright each entry was drawn, out of 255, read before the first rewrite. An entry is one
# level of one hue, so its brightest channel is its level
LEVELS = [max(palette[index].r, palette[index].g, palette[index].b)
          for index in range(player.palette_size)]

# The frames a pass turns around on
ENDS = (0, player.frames - 1)


def report(tint):
    """Write one colour over the whole animation, each entry at the brightness it was drawn."""
    for index, level in enumerate(LEVELS):
        palette[index] = color.mix(color.black, tint, level)


print(f"{player.frames} frames sharing {len(LEVELS)} colours, recoloured on frames {ENDS}")

pass_number = 0
report(REPORTS[0])

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The screen refreshes faster than the GIF changes, so only send a new frame
        if player.has_advanced():
            # Recoloured before the frame is sent, so the held end frame is already the new
            # colour and the sweep that follows stays in it
            if player.frame in ENDS:
                pass_number += 1
                report(REPORTS[pass_number % len(REPORTS)])

            screen.update(player.image)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
