# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# The vocabulary of an effects file, each name it may use and the values that name takes,
# and the paths autofx reads the file from and writes its problems to

from picofx.colour import (BLACK, BLUE, COOL, COLOUR_EFFECTS, CYAN, GREEN, MAGENTA, ORANGE, PINK,
                           PURPLE, RED, WARM, WHITE, YELLOW)
from picofx.mono import MONO_EFFECTS

# On a board with an FX drive the first two are fx_drive's MOUNT_POINT and FILE_PATH, kept
# here too since autofx also runs without a drive, where they are run()'s defaults.
# errors.txt is autofx's own
MOUNT_DIR = "/fx"
CONFIG_PATH = MOUNT_DIR + "/effects.txt"
ERRORS_PATH = MOUNT_DIR + "/errors.txt"

COLOURS = {
    "red": RED, "orange": ORANGE, "yellow": YELLOW, "green": GREEN, "cyan": CYAN,
    "blue": BLUE, "purple": PURPLE, "magenta": MAGENTA, "pink": PINK, "warm": WARM,
    "white": WHITE, "cool": COOL, "black": BLACK,
}

COMPONENTS = ("r", "g", "b")

# The one name on the left that is not a channel. Its entry carries settings about
# the board rather than an effect, so it is the only one with no effect name.
BOARD = "board"

# The player kinds that write the board's own outputs. A strip has a player of its
# own and reaches none of them, so a file playing only there leaves the outputs to
# whatever last wrote them
OUTPUT_KINDS = ("mono", "colour")


# Each effect, the kind of channel it drives, how a channel gets its callable, and
# the settings it takes, read from picofx's own lists rather than named again here.
# An effect declares the last two, so one added to picofx is offered by this file
# without it being edited, and one whose settings change cannot go stale here.
# CALLED is None where one effect serves every channel, "position" where it is called
# with the channel's place in the group, and a tuple where it names a method per
# channel. A class with no NAME is not offered.
EFFECTS = {}
for _kind, _registry in (("mono", MONO_EFFECTS), ("colour", COLOUR_EFFECTS)):
    for _effect in _registry:
        _name = getattr(_effect, "NAME", None)
        if _name is not None:
            EFFECTS[_name] = (_effect, _kind, _effect.CALLED, _effect.TAKES)

# Each screen effect and the settings it takes. A screen shows images where an output
# lights, so these never mix with EFFECTS. "gif" plays an animated GIF at the delays
# the file declares unless fps names one; "image" holds one still; "sequence" plays a
# folder of image files in the order their names number them, at the delay each name
# declares unless fps names one; "graphics" runs a Python file's draw(canvas, elapsed),
# the module body running once as its setup. All of them look on the drive first,
# then the board.
SCREEN_EFFECTS = {
    "gif": ("file", "fps", "interval", "loop", "ping_pong", "first_as_last", "hold"),
    "graphics": ("file", "fps", "interval", "width", "height"),
    "image": ("file",),
    "sequence": ("folder", "fps", "interval", "loop", "ping_pong", "first_as_last", "hold"),
}

# A Screen Hub's positions as its silk letters them, each named in a file as hubA to hubF.
# A board entry gives a connector the hub with screenA=hub or screenB=hub, its selects
# taking the other
HUB = "hub"
HUB_POSITIONS = "abcdef"

# The panel sizes a screen or a hub position is declared as, a size being unreadable
# from the panel itself
SCREEN_SIZES = ("2.8", "1.54")

# The one selector that plays sound. "wav" streams a file for as long as it lasts,
# or for good with loop=true. The file is found at load, while the board is sure to
# hold the drive, and read from the flash from then on, so it plays on after a
# computer takes the volume, where opening it later would find no drive at all.
AUDIO = "audio"
AUDIO_EFFECTS = {
    "wav": ("file", "loop"),
}

# What a setting's value must be. A name means the same thing wherever it appears, so
# its kind is stated once here. "count" is a whole number of 1 or more, each one
# dividing or repeating something, where "whole" may be zero or negative. "angle" is a
# fraction that takes degrees as well. "span" is a distance
# across the outputs, which nothing divides by at zero. "colour" is read by
# the parser, which turns it into tuples. "name" is a file name kept as written.
# "quarter" serves the left of the colon, a quarter turn for how a screen is mounted.
SETTINGS = {
    "speed": "number",
    "phase": "fraction",
    "duty": "fraction",
    "window": "fraction",
    "length": "count",
    "flashes": "count",
    "steps": "count",
    "extent": "span",
    "brightness": "fraction",
    "brightness_min": "fraction",
    "brightness_max": "fraction",
    "dimness": "fraction",
    "bright_min": "seconds",
    "bright_max": "seconds",
    "dim_min": "seconds",
    "dim_max": "seconds",
    "interval": "seconds",
    "hold": "seconds",
    "count": "whole",
    "step": "whole",
    "red_interval": "seconds",
    "red_amber_interval": "seconds",
    "flashing_interval": "seconds",
    "green_interval": "seconds",
    "amber_interval": "seconds",
    "red": "byte",
    "green": "byte",
    "blue": "byte",
    "hue": "angle",
    "sat": "fraction",
    "val": "fraction",
    "colour": "colour",
    "file": "name",
    "folder": "name",
    "fps": "number",
    "loop": "boolean",
    "ping_pong": "boolean",
    "first_as_last": "boolean",
    "width": "count",
    "height": "count",
}

# Settings written as a pair, the smaller named first
PAIRED_SETTINGS = (("bright_min", "bright_max"), ("dim_min", "dim_max"),
                   ("brightness_min", "brightness_max"))

# What a board entry takes, and the values a setting is limited to. A program is a
# file name, so it is answered when it is looked for rather than here. A screen's
# size is a fact about the hardware, set once here where an entry's settings vary
# per scene, and a strip's length is the same: it is the one channel count the board
# cannot discover for itself. Each screen port the board declares is a setting too, taking
# a panel size or, where the board can carry one, the hub, and so is each strip, its value
# a number rather than one of a set of words.
BOARD_SETTINGS = {"drive": ("manual",), "reload": ("manual", "auto"),
                  "program": None, "args": None}

# What follows a strip's length, as 'stripL=60|rgb' or 'stripApa=144|50%', kept among the
# board settings under the strip's name and one of these, which no file can write
ORDER = " order"
BRIGHTNESS = " brightness"

# What each left-side setting's value must be. level and backlight answer alike,
# both being how bright something is; colour, background and offset have shapes of
# their own and are read where they are applied
CHANNEL_KINDS = {"level": "fraction", "fade": "seconds", "ease": "seconds",
                 "backlight": "fraction", "rotation": "quarter", "mirror": "boolean",
                 "pixel_double": "boolean"}

# The two ways a channel may follow its effect, which are one setting written two ways:
# 'fade' crosses at a steady rate, 'ease' settles into place as a filament does
CURVES = ("fade", "ease")

# How a picture repeats on one side of a screen, and the spellings someone reaching
# for the plain true and false of every other setting would write
TILING = ("off", "repeat", "mirror")
TILING_ALSO = {"true": "repeat", "yes": "repeat", "on": "repeat",
               "false": "off", "no": "off", "1": "repeat", "0": "off"}

# Which of those belong to an output and which to a screen, for saying so
OUTPUT_SETTINGS = ("level", "colour", "fade", "ease")
SCREEN_SETTINGS = ("backlight", "rotation", "mirror", "offset", "background",
                   "pixel_double", "tile")
