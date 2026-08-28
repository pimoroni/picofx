from mighty_fx import MightyFX, SPCE
from picovector import color
from playback import GIFPlayer
from screens import Reserve, Screen280

"""
Recolour a whole animation as it plays, by rewriting the one colour table its frames share.

A GIF's frames are indices into a table of colours, and every frame of a sheet reads the same
table, so writing an entry changes that colour in all of them at once. Here the scan sweeps
up in green, and each pass comes back in the colour of what it found.

Each entry is rewritten at its own brightness, read once before anything changes: the art is
drawn as one hue at many levels, so keeping those levels is what keeps the glow and the
anti-aliasing along every line. A flat colour written over the lot would lose both.

The pass changes colour on the frame the sweep turns around on, which the file holds for half
a second, so the change is seen while the picture is still rather than during the sweep.

Press "Boot" to exit the program.
"""

# Constants
GIF_PATH = "/examples/assets/medscan.gif"   # The GIF to play, beside this example
ROTATION = 90                    # Quarter turn, to suit how the screen is mounted

# What each pass comes back as, taken in turn. The first is near enough what the file was drawn
# in, so a run starts looking as its artist left it
REPORTS = (color.rgb(0, 255, 64), color.rgb(255, 196, 40),
           color.rgb(255, 64, 48), color.rgb(64, 200, 255))

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it. The
# reserve is what keeps a source larger than the panel ahead of the wire
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES)

# The scan has two ends, a whole body and a whole skeleton, so it turns around rather than
# jumping from one to the other
player = GIFPlayer(GIF_PATH, ping_pong=True)

# Any frame's palette reaches the table they all share, so this is the whole animation's colours
palette = player.sheet.sprite(0).palette

# How bright each entry was drawn, out of 255, read before the first rewrite. An entry is one
# level of one hue, so its brightest channel is its level
LEVELS = [max(palette[index].r, palette[index].g, palette[index].b)
          for index in range(player.sheet.sprite(0).palette_size)]

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

            screen.update(player.image, rotation=ROTATION)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
