# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# The hand-written files a fresh board writes for itself, one constant per file. Every
# board folder has its own version of this module. EFFECTS, README and SECRETS go on the
# FX drive and are rebuilt by fx_drive, SECRETS only on a board with a wireless module.
# MAIN goes to the filesystem root and is rebuilt by boot.py.
#
# These are the only copies. Nothing ships main.py or secrets.py in the image, so a board
# writes its own on first boot and there is no second version to drift from.
#
# The drive's generated files, the manual and the picker's pages, are in fx_manual.py and
# fx_editor.py instead, built by tools/build_manual.py and tools/build_editor.py

# In single quotes, as the program it holds opens with a docstring
MAIN = '''\
from plasma_fx import PlasmaFX

# Light the board's LED first, since importing the effects machinery below takes a
# few seconds and this says the board is alive meanwhile
PlasmaFX.wake()

import autofx
import fx_drive

"""
Play the effects described by effects.txt on the FX drive.

Plug the board into a computer and the drive appears. Edit effects.txt, eject the
drive, and the new effects start straight away. Press "Boot" once to try an edit
without putting the drive away, or twice to hide it and bring it back.

Replace this file with your own program if you would rather write code. Deleting
it brings this one back, and an empty one leaves the board quiet.
"""

autofx.run(PlasmaFX, volume=fx_drive)
'''

# Exactly what the picker writes for its Rainbow look on the board's LED, so a fresh
# board's file opens in the picker as that look. Change it with the picker's own output,
# or the picker reads it as a file written by hand
EFFECTS = """\
# Written by the FX picker. Everything here can be edited by hand;
# MANUAL.html on this drive explains every line.

rgb: rainbow speed=0.39
"""

README = """\
Plasma 2350
===========
Edit effects.txt to change what the lights do and save it, and the board plays
the change a few seconds later. One line per strip, or for the board's own LED:

  board: stripDat=60
  stripDat: rainbow_wave speed=0.3

MANUAL.html on this drive has the rest, and opens in a browser: every effect and
what it takes, the screen, running a program, and showing scenes in turn.

If a save does not seem to take, press "Boot" once or eject this drive, since a
computer does not always write the file out straight away. Press "Boot" twice to
hide the drive, and twice again to bring it back.

Deleting effects.txt restores the default; emptying it leaves the board dark.

When something is wrong the board's LED says so, and the more flashes the worse
it is:

  white, once         the computer was still writing, so the press did nothing.
                      Try again in a moment
  blue, twice         something in effects.txt could not be read, or a drawing
                      failed. errors.txt says which line, a drawing's once
                      "Boot" is pressed or this drive ejected
  red, three times    there was no room to write errors.txt. This drive is full
                      or damaged, so free some space or let a computer repair it

While the computer is copying to this drive the effects stand aside, the board's
LED glowing a dim white with a brighter blink, and come back a moment after it
finishes.

This README is rebuilt by the board, so edits to it will not stick.
"""

# Empty, for the user to fill in. Written only where the drive has none, so their edits stay
SECRETS = """\
# Your WiFi network's name and password, for the programs that go online
WIFI_SSID = ""
WIFI_PASSWORD = ""
"""
