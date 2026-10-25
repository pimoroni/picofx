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

# The one name on the left that is not a channel, its entry holding board settings
BOARD = "board"

# The player kinds that write the board's own outputs. A strip's player reaches none of
# them, so a file playing only strips leaves the outputs as they were
OUTPUT_KINDS = ("mono", "colour")


# Each effect as its class, the kind of channel it drives, its CALLED and its TAKES, read
# from picofx's own lists, so an effect added or changed there is offered here as it is.
# A class with no NAME is not offered.
EFFECTS = {}
for _kind, _registry in (("mono", MONO_EFFECTS), ("colour", COLOUR_EFFECTS)):
    for _effect in _registry:
        _name = getattr(_effect, "NAME", None)
        if _name is not None:
            EFFECTS[_name] = (_effect, _kind, _effect.CALLED, _effect.TAKES)

# Each screen effect and the settings it takes, kept apart from EFFECTS since a screen shows
# images where an output lights. "gif" plays an animated GIF and "sequence" a folder of
# images in the order their names number them, each at its own delays unless fps names one.
# "image" holds one still, and "graphics" runs a Python file's draw(canvas, elapsed) after
# running its module body once. Each looks on the drive first, then the board.
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

# The one selector that plays sound, "wav" streaming a file once or with loop=true for good
AUDIO = "audio"
AUDIO_EFFECTS = {
    "wav": ("file", "loop"),
}

# What each effect setting's value must be, stated once since a name means the same thing
# wherever it appears. "count" is a whole number of 1 or more, since each divides or repeats
# something, where "whole" may be zero or negative. "angle" is a fraction that takes degrees
# as well, and "span" a distance across the outputs that may be zero, since nothing divides
# by it. "colour" is a name or hex the parser turns into a tuple, and "name" a file name
# kept as written. CHANNEL_KINDS below adds "quarter", a quarter turn for a mounted screen.
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

# What a board entry takes, and the values a setting is limited to, None taking any. A
# program is a file name, answered when it is looked for. A screen's size and a strip's
# length are facts about the hardware the board cannot discover, set once in the board
# entry where an entry's settings vary per scene. So each screen port the board declares is
# a setting too, taking a panel size or the hub, and each strip, taking a number.
BOARD_SETTINGS = {"drive": ("manual",), "reload": ("manual", "auto"),
                  "program": None, "args": None}

# What follows a strip's length, as 'stripL=60|rgb' or 'stripApa=144|50%', kept among the
# board settings under the strip's name and one of these, which no file can write
ORDER = " order"
BRIGHTNESS = " brightness"

# What each left-side setting's value must be. level and backlight answer alike, both being
# how bright something is. colour, background and offset have shapes of their own and are
# read where they are applied
CHANNEL_KINDS = {"level": "fraction", "fade": "seconds", "ease": "seconds",
                 "backlight": "fraction", "rotation": "quarter", "mirror": "boolean",
                 "pixel_double": "boolean"}

# The two ways a channel may follow its effect, one setting written two ways. 'fade' crosses
# at a steady rate and 'ease' settles into place as a filament does
CURVES = ("fade", "ease")

# How a picture repeats on one side of a screen, and the spellings someone reaching
# for the plain true and false of every other setting would write
TILING = ("off", "repeat", "mirror")
TILING_ALSO = {"true": "repeat", "yes": "repeat", "on": "repeat",
               "false": "off", "no": "off", "1": "repeat", "0": "off"}

# Which left-side settings belong to an output and which to a screen, for saying so
OUTPUT_SETTINGS = ("level", "colour", "fade", "ease")
SCREEN_SETTINGS = ("backlight", "rotation", "mirror", "offset", "background",
                   "pixel_double", "tile")
