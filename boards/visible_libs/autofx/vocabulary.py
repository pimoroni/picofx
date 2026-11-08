# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# The vocabulary of an effects file, each name it may use and the values that name takes,
# and the paths autofx reads the file from and writes its problems to

from picofx.colour import (BLACK, BLUE, COOL, COLOUR_EFFECTS, CYAN, GREEN, MAGENTA, ORANGE, PINK,
                           PURPLE, RED, WARM, WHITE, YELLOW)
from picofx.mono import MONO_EFFECTS

# On a board with an FX drive the first two are fx_drive's MOUNT_POINT and FILE_PATH, kept
# here too since autofx also runs without a drive. The last two are run()'s defaults, and
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

# The name on the left whose entry holds board settings in place of a channel's effect
BOARD = "board"

# The two names on the left for what the sensor connector's triggers do, each holding settings
# as the board entry does, a trigger's name then what it does. remote: is for the Aye Arr
# Remote's buttons, named as aye_arr's PimoroniRemote names them, and motion: for a PIR Stick
REMOTE = "remote"
MOTION = "motion"
TRIGGERS = {
    REMOTE: ("anticlock", "up", "clockwise", "left", "ok_stop", "right", "return_undo", "down",
             "menu_action", "1_red", "2_green", "3_blue", "4_cyan", "5_magenta", "6_yellow",
             "7_warm", "8_white", "9_cool", "record", "0_rainbow", "play_pause"),
    MOTION: ("starts", "stops"),
}

# What sensor= on the board line names for each trigger entry, so each answers only its own
TRIGGER_SENSOR = {REMOTE: "ir", MOTION: "pir"}

# The buttons that do the same in every scene, standby and wake, and pausing the effects, so
# a file cannot give them anything else
TRIGGERS_FIXED = ("ok_stop", "play_pause")

# What a trigger can do besides going to a scene, which is written as scene and its name
TRIGGER_STEPS = ("nothing", "next", "previous", "first", "restart")

# A motion trigger's delay, written after the trigger on its line. after= is the seconds it
# waits, and the opposite edge coming first cancels it unless cancel=no
TRIGGER_TIMING = ("after", "cancel")

# Where the board settings keep what Always on gives the triggers, under a name no file can
# write, as ORDER and BRIGHTNESS are
ALWAYS_TRIGGERS = " triggers"


# Each effect as its class, the kind of channel it drives, its CALLED and its TAKES, read
# from picofx's own lists, so an effect added or changed there is offered here as it is.
# A class with no NAME is not offered.
EFFECTS = {}
for _kind, _registry in (("mono", MONO_EFFECTS), ("colour", COLOUR_EFFECTS)):
    for _effect in _registry:
        _name = getattr(_effect, "NAME", None)
        if _name is not None:
            EFFECTS[_name] = (_effect, _kind, _effect.CALLED, _effect.TAKES)

# Each screen effect and the settings it takes. "gif" plays an animated GIF, "sequence" a
# folder of numbered images, "image" one still and "drawing" a Python file's draw(). Each
# looks on the drive first, then the board. "none" shows only the background, so a scene
# can take a screen from the always-on entries.
SCREEN_EFFECTS = {
    "drawing": ("file", "fps", "interval", "width", "height"),
    "gif": ("file", "fps", "interval", "loop", "ping_pong", "first_as_last", "hold"),
    "image": ("file",),
    "none": (),
    "sequence": ("folder", "fps", "interval", "loop", "ping_pong", "first_as_last", "hold"),
}

# A Screen Hub's positions as its silk letters them, each named in a file as hubA to hubF.
# A board entry gives a connector the hub, such as screenA=hub, and its selects take the other
HUB = "hub"
HUB_POSITIONS = "abcdef"

# The panel sizes a screen or hub position is declared as, since a panel cannot report it
SCREEN_SIZES = ("2.8", "1.54")

# The one selector that plays sound, "wav" streaming a file once or with loop=true for good,
# at full volume unless volume= names a fraction of it. "none" plays nothing, which lets a
# scene silence the always-on sound
AUDIO = "audio"
AUDIO_EFFECTS = {
    "none": (),
    "wav": ("file", "loop", "volume"),
}

# The drive folder each effect's file is looked for in before the top of the drive, so a file
# is named without its folder in either place
FOLDERS = {"gif": "pictures", "image": "pictures", "sequence": "pictures", "drawing": "drawings",
           "wav": "sounds"}

# What each effect setting's value must be, stated once since a name means the same thing
# wherever it appears. "count" is a whole number of 1 or more, since each divides or repeats
# something, where "whole" may be zero or negative. "angle" is a fraction that takes degrees
# as well, and "span" a distance across the outputs above zero, since an effect divides by
# it. "colour" is a name or hex the parser turns into a tuple, and "name" a file name
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
    "volume": "fraction",
    "ping_pong": "boolean",
    "first_as_last": "boolean",
    "width": "count",
    "height": "count",
}

# Pairs of settings that bound a range, the smaller named first
PAIRED_SETTINGS = (("bright_min", "bright_max"), ("dim_min", "dim_max"),
                   ("brightness_min", "brightness_max"))

# What a board entry takes, and the values a setting is limited to, or None for any. A
# screen's size and a strip's length are set once here, since the board cannot discover
# them, so each screen port and each strip is a setting too
BOARD_SETTINGS = {"drive": ("manual",), "reload": ("manual", "auto"),
                  "program": None, "args": None, "sensor": ("ir", "pir")}

# What follows a strip's length, a colour order such as '60|rgb' or a brightness such as
# '144|50%' for a strip that has one, kept among the board settings under the strip's name
# and one of these, which no file can write
ORDER = " order"
BRIGHTNESS = " brightness"

# What each left-side setting's value must be. level and backlight answer alike, since
# both say how bright something is. colour, background, offset and tile have shapes of
# their own and are read where they are applied
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
