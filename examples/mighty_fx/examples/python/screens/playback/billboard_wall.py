import time

from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280

"""
Show a different poster on every panel a hub can reach, all changing on one clock.

A hub shares one SP/CE port, so panels with different pictures are sent one after another and the
change ripples across the wall. There is no ScreenGroup, which sends one frame to every panel.

One player feeds every panel. image_at() reads any frame without moving the player, so panel n
takes the poster n along the folder and the folder is held once.

Press "Boot" to exit the program.
"""

# Constants
POSTERS = "/examples/assets/billboards/portrait"   # Shared with the billboard showcases
ROTATION = 0                     # Portrait, which is the shape these posters are
DWELL = 3.0                      # Seconds a poster is up for

# Create a MightyFX object driving a screen hub, which takes SP/CE port B for extra chip selects
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.HUB_SELECTS)

# Build a screen on every hub port and keep those that answer, as a hub need not be full.
# reveal_together holds the shared backlight until each panel has its poster
panels = []
for port in mighty.hub.ports:
    try:
        panels.append(Screen280(port, reveal_together=True, rotation=ROTATION))
    except ValueError:
        pass

if not panels:
    # Release the hub first, as one of its chip selects is a panel's backlight pin
    mighty.shutdown()
    raise RuntimeError("No panels answered! Check the hub is plugged into SP/CE A, with its panels on the hub rather than on the board")

try:
    player = SequencePlayer(POSTERS, fps=1 / DWELL)
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{POSTERS}' is missing! Check it is on the board") from None

print(f"{len(panels)} of {len(mighty.hub.ports)} hub positions answered,"
      f" {player.frames} posters, {DWELL}s each")

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        if player.has_advanced():
            marked = time.ticks_ms()
            for index, panel in enumerate(panels):
                panel.update(player.image_at((player.frame + index) % player.frames))

            print(f"the change rippled across {len(panels)} panels in"
                  f" {time.ticks_diff(time.ticks_ms(), marked)}ms")

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
