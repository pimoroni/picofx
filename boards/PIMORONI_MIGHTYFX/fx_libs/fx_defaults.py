# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# The hand-written files a fresh board writes for itself, one constant per file. Every
# board folder has its own version of this module. EFFECTS, README and SECRETS go on the
# FX drive and are rebuilt by fx_drive, SECRETS only on a board with a wireless module.
# MAIN goes to the filesystem root and is rebuilt by boot.py.
#
# A drive build ships no main.py or secrets.py, so these are its only copies. The builds
# without the drive ship the examples' secrets.py, which holds the same settings as SECRETS.
#
# Kept apart from fx_drive so a change of wording shows on its own in a diff. Only a
# literal triple quote needs escaping inside these.
#
# The drive's generated files, the manual and the picker's pages, are in fx_manual.py and
# fx_editor.py instead, built by tools/build_manual.py and tools/build_editor.py

# In single quotes, as the program it holds opens with a docstring
MAIN = '''\
from mighty_fx import MightyFX

# Light the outputs first, so the board shows it is on during the slow imports below
MightyFX.wake()

import autofx
import fx_drive

"""
Play the effects described by effects.txt on the FX drive.

Plug the board into a computer and the drive appears. Edit effects.txt, eject the
drive, and the new effects start straight away. Press "Boot" once to try an edit
without putting the drive away, or twice to hide the drive and twice again to bring it back.

Replace this file with your own program if you would rather write code. Deleting
it brings this one back, and an empty one leaves the board quiet.
"""

autofx.run(MightyFX, volume=fx_drive)
'''

# Exactly what the picker writes for its Rainbow look on the outputs, so a fresh board's
# file opens in the picker as that look. Change it with the picker's own output, or the
# picker reads it as a file written by hand
EFFECTS = """\
# Written by the FX picker. Everything here can be edited by hand;
# MANUAL.html on this drive explains every line.

out1-7: rainbow_wave speed=-0.39 length=9
"""

README = """\
Mighty FX
=========
Open PICKER.html on this drive in Chrome or Edge to choose what the lights,
screens and sound play. Press "Open FX drive" and choose this drive, pick a look
from the cards, then press "Save to board". The board plays it a few seconds
later.

MANUAL.html on this drive shows you around the picker and everything else the
board can do, and opens in any browser.

If a save does not seem to take, press "Boot" once or eject this drive, since a
computer does not always finish writing to a drive straight away. Press "Boot"
twice to hide the drive, and twice again to bring it back.

When something is wrong, the lights flash:

  white, once         the computer was still writing, so the press did nothing.
                      Try again in a moment
  blue, twice         something saved could not be read, or a drawing failed.
                      "Check board" in the picker shows what. For a drawing it
                      says so once "Boot" is pressed or this drive is ejected
  red, three times    there was no room to write errors.txt. This drive is full
                      or damaged, so free some space or let a computer repair it

While the computer is copying to this drive, a dim white light travels along the
outputs in place of the effects, which come back a moment after it finishes.

The picker saves to effects.txt, which can also be edited by hand. EDITOR.html
helps with that, and the manual describes every line. Deleting effects.txt
restores the default, and emptying it leaves the board dark.

This README is rebuilt by the board, so edits to it will not stick.
"""

# Empty, for the user to fill in. Written only where the drive has none, so their edits stay
SECRETS = """\
# Your WiFi network's name and password, for the programs that go online
WIFI_SSID = ""
WIFI_PASSWORD = ""
"""
