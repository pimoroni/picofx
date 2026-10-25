# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# The checks between the parser and what is built. A board entry and a hub are held to what
# the board declares and an entry's settings to their kinds. A file an entry names is looked
# for on the drive and then on the board.

import os

from .vocabulary import (BOARD_SETTINGS, BRIGHTNESS, HUB, MOUNT_DIR, ORDER, PAIRED_SETTINGS,
                         SCREEN_SIZES, SETTINGS)
from .hardware import (BOARD_BRIGHTNESS, BOARD_HUB, BOARD_STRIPS, hub_example, hub_port, hub_shown,
                       screen_kinds, screen_port, screen_shown, strip_shown)
from .parser import expand, read_number, unquoted, value_fault, value_shown


def __degrees(text):
    # A fraction of a turn from 0 to 360 written with 'deg', or None if it is not
    if not isinstance(text, str) or not text.lower().endswith("deg"):
        return None

    number = read_number(text[:-3])
    if number is None or not 0.0 <= number <= 360.0:
        return None
    return number / 360.0


def candidates(name):
    """Where a file the effects file names may be, the drive's copy first."""
    # A path is taken as written, since a doubled separator would otherwise fold and
    # '/prog.py' would quietly find the drive's copy. A plain name looks on the drive
    # first, that being the one the reader can see and edit
    if name.startswith("/"):
        return (name,)

    # The drive's examples folder is also mounted at /examples, so a name inside it would
    # otherwise be found twice and reported as on both filesystems
    if name.split("/")[0] == "examples":
        return (MOUNT_DIR + "/" + name,)

    return (MOUNT_DIR + "/" + name, name)


def find_file(name, line, problems):
    """
    The file or folder an entry names, or None if there is none to play. The drive's
    copy wins where the board has one too, as it does for a program.
    """
    found = []
    for candidate in candidates(name):
        try:
            os.stat(candidate)
            found.append(candidate)
        except OSError:
            continue

    if not found:
        problems.append("line {}: there is no {} on the drive or the board".format(line, name))
        return None

    if len(found) > 1:
        problems.append("line {}: {} is on the drive and on the board's own filesystem, "
                        "so the drive's copy is the one that plays".format(line, name))

    return found[0]


def check_board(entry, has_strips, problems, lines):
    """
    The board settings the entry carries, with anything it cannot use dropped. A
    board entry names no effect, so nothing else would ever look at these, and a typo
    in 'drive' or 'program' would leave a board acting as though the line were absent.

    The line each setting kept was written on goes into `lines`, for the checks that
    compare settings across board entries.
    """
    settings = {}
    written = {}

    for key, value in entry.settings.items():
        at = entry.lines.get(key, entry.line)

        # A hub position's size, one or several positions named as an entry names them
        if key.startswith(HUB):
            places = []
            prefix = ""
            for part in key.split(","):
                named, prefix = expand(part, prefix, at, problems)
                places.extend(named)
            text = value if isinstance(value, str) else value_shown(value)
            if text not in SCREEN_SIZES:
                problems.append("line {}: the board's {} is {}, it takes {}".format(
                    at, hub_shown(places) if places else key, value_shown(value),
                    ", ".join(SCREEN_SIZES)))
                continue
            for place in places:
                settings[place] = text
                written[place] = at
            continue

        kinds = [kind for kind, _prop, _shown in BOARD_STRIPS]
        screens = screen_kinds()
        if key not in BOARD_SETTINGS and key not in kinds and key not in screens:
            if not has_strips and key.startswith("strip"):
                problems.append("line {}: this board has no strip connectors, so it "
                                "has no {}".format(at, strip_shown(key)))
                continue
            if not screens and key.startswith("screen"):
                problems.append("line {}: this board has no screen connectors, so it "
                                "has no {}".format(at, screen_shown(key)))
                continue
            problems.append("line {}: the board has no setting '{}', it takes {}".format(
                at, key, ", ".join(sorted(list(BOARD_SETTINGS) + kinds + screens))))
            continue

        # Whatever it was written as, since a setting limited to named values is
        # compared against them and a program is a file name
        text = value if isinstance(value, str) else value_shown(value)

        # A program's arguments are divided by the pipe that divides any value into
        # parts, and each one reaches the program as it was written. Read here so they
        # skip the path check below, which a time or a Windows path would otherwise trip
        if key == "args":
            settings[key] = tuple(part.strip() for part in text.split("|") if part.strip())
            continue

        # A count is a number where every other board setting is a word or a file
        # name, and this entry keeps its values as written, so it is read here
        if key in kinds:
            length, _divider, order = text.partition("|")
            number = read_number(length)
            fault = ("expected a number" if number is None
                     else value_fault("count", number))
            if fault is not None:
                problems.append("line {}: the board's {} is {}, {}".format(
                    at, strip_shown(key), value_shown(length), fault))
                continue

            # A strip with a brightness of its own takes it as written, or the board's own
            # where none is. A wrong one still leaves the strip its length, so it plays at
            # the board's own
            if key in BOARD_BRIGHTNESS:
                after = order.strip()
                shown = strip_shown(key)
                brightness = read_number(after) if after else None
                if after.isalpha():
                    problems.append("line {}: the board's {} takes its colours in one order, "
                                    "so what follows its length is its brightness, such as "
                                    "'{}={}|50%'".format(at, shown, shown, int(number)))
                    brightness = None
                elif after and (brightness is None or
                                value_fault("fraction", brightness) is not None):
                    problems.append("line {}: the board's {} has its brightness as {}, so "
                                    "give it from 0% to 100%, such as '{}={}|50%'".format(
                                        at, shown, value_shown(after), shown, int(number)))
                    brightness = None
                settings[key] = int(number)
                settings[key + BRIGHTNESS] = brightness
                continue

            # The strip takes its colours in the order written, or the board's own order
            # where none is, so a later board entry without one takes it back to that.
            # A wrong order still leaves the strip its length, so it plays in the board's own
            order = order.strip().lower()
            if order and sorted(order) != ["b", "g", "r"]:
                problems.append("line {}: the board's {} has its colours in the order {}, "
                                "so give the letters r, g and b in the order the strip "
                                "takes them, such as '{}={}|rgb'".format(
                                    at, strip_shown(key), value_shown(order),
                                    strip_shown(key), int(number)))
                order = ""
            settings[key] = int(number)
            settings[key + ORDER] = order or None
            continue

        if key in screens:
            allowed = SCREEN_SIZES + (HUB,) if BOARD_HUB[0] else SCREEN_SIZES
        else:
            allowed = BOARD_SETTINGS[key]
        if allowed is not None:
            if text.lower() not in allowed:
                problems.append("line {}: the board's {} is {}, it takes {}".format(
                    at, key, value_shown(value), ", ".join(allowed)))
                continue
            text = text.lower()          # So the caller compares against one spelling

        elif "\\" in text or unquoted(text, ":") >= 0:
            base = text.replace("\\", "/").rsplit("/", 1)[-1]
            problems.append("line {}: '{}' is a path on your computer. Correct it to "
                            "'{}'".format(at, text, base))
            continue

        settings[key] = text

    # A later board entry setting the same thing takes over its line, as it takes its value
    for key in settings:
        written.setdefault(key, entry.lines.get(key, entry.line))
    lines.update(written)
    return settings


# Where a hub and a screen were both played on, which of them was refused, kept among the
# board settings under a name no file can write so their entries are not answered twice
REFUSED = " refused"


def check_hub(board, lines, entries, problems):
    """
    Settle what the board entries say about a hub against what the entries play on. A
    hub nothing plays on is dropped, as a strip is, and a screen declared on the connector
    the hub's selects take is dropped where nothing plays on it. Where both are played on,
    either could be the mistake, so neither plays.
    """
    hub = hub_port(board)
    places = sorted(key for key in board if key.startswith(HUB))
    named = {channel.name for entry in entries for channel in entry.channels}

    if hub is None:
        if places and not BOARD_HUB[0]:
            problems.append("line {}: this board cannot carry a Screen Hub, so it has no "
                            "{}".format(lines[places[0]], hub_shown(places)))
        elif places:
            problems.append("line {}: the board entry gives {} a size, but no connector has "
                            "the hub. Write it like {}".format(
                                lines[places[0]], hub_shown(places), hub_example()))
        for place in places:
            board.pop(place)
        return

    # Drop a hub no entry shows anything on, so its connectors stay free
    if not any(name.startswith(HUB) for name in named):
        for setting in places + [hub]:
            board.pop(setting)
        return

    # The hub takes one connector for its panels and the other for their selects
    for name in screen_kinds():
        if name == hub or board.get(name) is None:
            continue
        port_name = screen_port(name)[1]

        if board[name] == HUB:
            problems.append("line {}: the board entry gives both connectors the hub, which "
                            "takes one for its panels and SP/CE {} for their selects".format(
                                lines[name], port_name))
            board.pop(name)
        elif name in named:
            # Nothing says which of the two is wired, so neither is driven
            problems.append("line {}: the hub takes both connectors, so {} and the hub "
                            "cannot both play. Keep one".format(
                                lines[name], screen_shown(name)))
            for setting in places + [hub, name]:
                board.pop(setting)
            board[REFUSED] = (HUB, name)
        else:
            problems.append("line {}: SP/CE {} carries the hub's selects, so {} has no "
                            "screen of its own".format(lines[name], port_name,
                                                       screen_shown(name)))
            board.pop(name)


def check_settings(entry, taken, problems):
    """
    The settings the effect takes, with anything it cannot use dropped so it runs on
    its own defaults. Everything reaching an effect from here is of the kind it wants,
    which is what keeps a bad value out of the timer callback.
    """
    settings = {}

    for key, value in entry.settings.items():
        # An entry may run over several lines, so a setting answers on its own
        at = entry.lines.get(key, entry.line)

        if key not in taken:
            problems.append("line {}: {} has no setting '{}', it takes {}".format(
                at, entry.effect, key, ", ".join(taken) if taken else "no settings"))
            continue

        # An effect names its own settings, so one added to picofx may name a setting
        # this file has no reading for. The effect still runs, on its own value for it
        kind = SETTINGS.get(key)
        if kind is None:
            problems.append("line {}: {}'s '{}' cannot be set from a file, so it was "
                            "left as it is".format(at, entry.effect, key))
            continue
        if kind == "colour":
            settings[key] = value       # Already read into tuples, and reported if bad
            continue

        # A setting written in two parts is one value with an end each, so both are
        # held to the same kind and the pair is reported as it was written
        if isinstance(value, tuple):
            fault = None
            for part in value:
                fault = value_fault(kind, part)
                if fault is not None:
                    break
            if fault is not None:
                problems.append("line {}: {}'s {} is '{}', {}".format(
                    at, entry.effect, key,
                    "|".join(value_shown(part) for part in value), fault))
            else:
                settings[key] = value
            continue

        # A hue is the one setting a user copies from elsewhere, and colour pickers give it
        # in degrees, so degrees are taken too and turned into the fraction the effect wants
        if kind == "angle":
            turn = __degrees(value)
            if turn is not None:
                value = turn

        fault = value_fault(kind, value)
        if fault is not None:
            problems.append("line {}: {}'s {} is {}, {}".format(
                at, entry.effect, key, value_shown(value), fault))
            continue

        # Each effect gets the type it was written for. A count is an integer, which several
        # require, and a boolean is one however the user spelt it
        if kind in ("count", "whole", "quarter"):
            settings[key] = int(value)
        elif kind == "boolean":
            settings[key] = bool(value)
        else:
            settings[key] = value

    for smaller, larger in PAIRED_SETTINGS:
        if smaller in settings and larger in settings and settings[smaller] > settings[larger]:
            problems.append("line {}: {}'s {} is above its {}".format(
                entry.line, entry.effect, smaller, larger))

    return settings
