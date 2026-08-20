# Shows a different poster on every panel a hub can reach, all changing on one clock.
#
# A hub shares one SP/CE port, and one port is one stream, so panels showing different pictures are sent one
# after another. Measured on three: 68ms to broadcast one poster to all of them, 181ms to send a different
# poster to each, so six would be about 360ms. The change therefore ripples across the wall rather than landing
# at once, which against a three second dwell reads as a row of boards flipping.
#
# traces_wall.py is the other half of this: the same picture on every panel, which the hub sends once and every
# panel latches together. Between them they are what a hub is, and the choice a wall has to make.
#
# There is no ScreenGroup here. A group exists to hold panels in phase so they can be sent together, and no two
# panels are ever sent together in this example. Building one would cost two seconds of calibration at startup
# and half a second on the first change, for nothing.
#
# One player feeds every panel. image_at() reads any frame without moving the player, so panel n takes the
# poster n along the folder and the folder is held once.

import time

from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280

# Constants
POSTERS = "/examples/assets/billboards/portrait"   # Shared with the billboard showcases
ROTATION = 0                     # Portrait, which is the shape these posters are
DWELL = 3.0                      # Seconds a poster is up for

# SP/CE B gives up its five pins as the chip selects for the panels on SP/CE A, so
# the board hands back six ports and every panel is brought up and cleared together
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.HUB_LINES)

# A port is handed out per chip select the hub reaches, whether or not a panel is on the
# end of it. One that is not there refuses to be created, so build them all and keep
# whichever answered: a hub does not have to be full to be used
panels = []
for port in mighty.hub.ports:
    try:
        panels.append(Screen280(port))
    except ValueError:
        pass

if not panels:
    # Give the connectors back before saying so. A hub drives its chip selects high,
    # and one of those is the backlight pin of whatever is plugged into that connector
    mighty.shutdown()
    raise RuntimeError("No panels answered! Check the hub is plugged into SP/CE A, with its panels on the hub rather than on the board")

player = SequencePlayer(POSTERS, fps=1 / DWELL)
print(f"{len(panels)} of {len(mighty.hub.ports)} hub positions answered,"
      f" {player.frames} posters, {DWELL}s each")

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        if player.has_advanced():
            marked = time.ticks_ms()
            for index, panel in enumerate(panels):
                panel.update(player.image_at((player.frame + index) % player.frames), rotation=ROTATION)

            print(f"the change rippled across {len(panels)} panels in"
                  f" {time.ticks_diff(time.ticks_ms(), marked)}ms")

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
