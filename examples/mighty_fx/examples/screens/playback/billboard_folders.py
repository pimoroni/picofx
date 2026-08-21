import time

from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280

"""
Show several folders of posters, the boot button turning to the next poster or moving on to the
next folder.

A player holds one sequence, so several sequences are several players, each with its own length,
clock and settings. Here the settings make the point: the portrait folder is sent as it is and
the landscape one gets a quarter turn, so changing folder changes how a poster is placed.

The button's three actions are judged on release, a press being impossible to tell from a hold
until it ends, and an example that takes the button has to give a way out. Turning to the next
poster is a reposition and not an advance: advance() refuses a player that has a rate, where
to_frame() moves a clocked one and lets its clock carry on.

Press "Boot" for the next poster, hold it to change folder, and hold it two seconds to exit.
"""

# Constants: a folder, the rotation its posters want, and how long each is up for
FOLDERS = (("/examples/assets/billboards/portrait", 0, 3.0),
           ("/examples/assets/billboards/landscape", 90, 2.0))
FOLDER_MS = 700                 # Held at least this long, the button changes folder
QUIT_MS = 2000                  # Held at least this long, it ends the example instead

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

players = [SequencePlayer(folder, fps=1 / dwell) for folder, _rotation, dwell in FOLDERS]
for (folder, rotation, dwell), player in zip(FOLDERS, players):
    print(f"{player.frames} posters in {folder.split('/')[-1]}, turned {rotation}, {dwell}s each")

print(f"press for the next poster, hold {FOLDER_MS}ms to change folder, {QUIT_MS}ms to finish")

chosen = 0
pressed_since = None
leaving = False

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not leaving:
        player = players[chosen]
        if player.has_advanced():
            screen.update(player.image, rotation=FOLDERS[chosen][1])

        if mighty.boot_pressed():
            if pressed_since is None:
                pressed_since = time.ticks_ms()

        elif pressed_since is not None:
            held = time.ticks_diff(time.ticks_ms(), pressed_since)
            pressed_since = None
            if held >= QUIT_MS:
                leaving = True
            elif held >= FOLDER_MS:
                chosen = (chosen + 1) % len(players)
                screen.update(players[chosen].image, rotation=FOLDERS[chosen][1])
            else:
                player.to_frame((player.frame + 1) % player.frames)
                screen.update(player.image, rotation=FOLDERS[chosen][1])

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
