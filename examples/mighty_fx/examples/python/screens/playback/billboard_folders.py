import time

from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280

"""
Show several folders of posters, with Boot moving to the next poster or the next folder.

A player holds one sequence, so several folders are several players with their own settings. The
landscape folder takes a quarter turn and the portrait one none.

The button is judged on release, as a press cannot be told from a hold until it ends. The next
poster comes from to_frame(), since advance() refuses a player with a rate.

Press "Boot" for the next poster, hold it to change folder, and hold it two seconds to exit.
"""

# Constants, each a folder with the rotation its posters want and how long each is up
FOLDERS = (("/examples/assets/billboards/portrait", 0, 3.0),
           ("/examples/assets/billboards/landscape", 90, 2.0))
FOLDER_MS = 700                 # Held at least this long, the button changes folder
QUIT_MS = 2000                  # Held at least this long, it ends the example instead

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

try:
    players = [SequencePlayer(folder, fps=1 / dwell) for folder, _rotation, dwell in FOLDERS]
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{FOLDERS[0][0]}' or '{FOLDERS[1][0]}' is missing! Check both are on the board") from None

for (folder, rotation, dwell), player in zip(FOLDERS, players):
    print(f"{player.frames} posters in {folder.split('/')[-1]}, turned {rotation}, {dwell}s each")

print(f"press for the next poster, hold {FOLDER_MS}ms to change folder, {QUIT_MS}ms to finish")

chosen = 0                      # Which folder is showing
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
            # Released, so judge the press by how long it was held
            held = time.ticks_diff(time.ticks_ms(), pressed_since)
            pressed_since = None
            if held >= QUIT_MS:
                leaving = True
            # to_frame() makes the next has_advanced() report the frame, so the loop sends it
            elif held >= FOLDER_MS:
                chosen = (chosen + 1) % len(players)
                players[chosen].to_frame(players[chosen].frame)
            else:
                player.to_frame((player.frame + 1) % player.frames)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
