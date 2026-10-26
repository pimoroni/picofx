# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# The hand-written files a fresh board writes for itself, one constant per file. fx_drive
# rebuilds EFFECTS, README and SECRETS on the FX drive, SECRETS only on a board with a wireless
# module, and boot.py rebuilds MAIN in the filesystem root. Nothing ships main.py or secrets.py
# in the image, so these are the only copies.

# In single quotes, as the program it holds has a docstring
MAIN = '''\
from plasma_fx import PlasmaFX

# Light the board's LED first, so the board shows it is on during the slow imports below
PlasmaFX.wake()

import autofx
import fx_drive

"""
Play the effects described by effects.txt on the FX drive.

Plug the board into a computer and the drive appears. Edit effects.txt, eject the
drive, and the new effects start straight away. Press "Boot" once to try an edit
without ejecting the drive, or twice to hide the drive and twice again to bring it back.

Replace this file with your own program if you would rather write code. Deleting
it brings this one back, and an empty one leaves the board dark.
"""

autofx.run(PlasmaFX, volume=fx_drive)
'''

# What a fresh board plays
EFFECTS = """\
rgb: rainbow speed=0.39
"""

README = """\
Plasma 2350
===========
Edit effects.txt to change what the lights do and save it, and the board plays
the change a few seconds later. One line per strip, or for the board's own LED:

  board: stripDat=60
  stripDat: rainbow_wave speed=0.3
  rgb: rainbow speed=0.3

If a save does not seem to take, press "Boot" once or eject this drive, since a
computer does not always write the file out straight away. Press "Boot" twice to
hide the drive, and twice again to bring it back.

Deleting effects.txt restores the default; emptying it leaves the board dark.

When something is wrong, the board's LED flashes:

  white, once         the computer was still writing, so the press did nothing.
                      Try again in a moment
  blue, twice         something in effects.txt could not be read, or a drawing
                      failed. errors.txt says which line. For a drawing it says
                      so once "Boot" is pressed or this drive is ejected
  red, three times    there was no room to write errors.txt. This drive is full
                      or damaged, so free some space or let a computer repair it

While the computer is copying to this drive, the board's LED glows a dim white
with a brighter blink in place of the effects, which come back a moment after it
finishes. While the board starts up or loads a save, its LED blinks slowly
between dim and bright white until the effects begin.

This README is rebuilt by the board, so edits to it will not stick.
"""

# Empty, for the user to fill in. Written only where the drive has none, so their edits stay
SECRETS = """\
# Your WiFi network's name and password, for the programs that go online
WIFI_SSID = ""
WIFI_PASSWORD = ""

# Your time zone, for the programs that show the time, such as "uk" or "eastern"
TIME_ZONE = ""
"""
