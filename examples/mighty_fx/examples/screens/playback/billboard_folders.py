# Several folders of posters, with the boot button turning to the next poster or moving on to the next folder.
#
# A player holds one sequence, so several sequences are several players, and each carries its own length, its
# own clock and its own settings. Here the settings are what make the point: the portrait folder is sent as it
# is and the landscape one gets a quarter turn, so changing folder changes how the poster has to be placed as
# well as which posters they are.
#
# The boot button does three things by how long it is held: a press turns to the next poster, a hold changes
# folder, and a longer hold ends the example. That third one matters. Every other example here ends when boot is
# pressed, and one that takes the button for itself has to give a way out or there is none but the reset pin.
#
# All three are judged when the button is released, a press being impossible to tell from a hold until it ends.
#
# Turning to the next poster is a reposition and not an advance. advance() drives a player that was built with
# fps=False and refuses one that has a rate, since a rate is what would be driving it; to_frame() moves a
# clocked player and lets its clock carry on from there.
#
# Both folders are held at once, which is about a megabyte for these fourteen palettised posters. Reading a
# folder only when it is chosen would cost a second of stall at every change instead.

import time

from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280

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
