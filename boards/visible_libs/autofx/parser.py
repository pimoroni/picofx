# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# The parser, reading the effects file a user edits into entries a board can play, one
# entry per set of outputs, such as
#
#   out1-6 level=0.5: pulse_wave speed=0.6
#   out3.g: blink speed=1.0 duty=0.3
#   screenA: gif file="anim.gif"
#
# A [Heading: 30s] begins a scene that shows for its time. Scenes take turns, and entries
# before the first heading are always on.
#
# Output settings sit left of the colon and effect settings right of it. An entry runs
# until the next selector, so its settings may be laid over several lines. Everything a
# user reads says output where the code says channel, a channel being a slot in a player
# and an output the connector a channel drives.
#
# It knows nothing of the board beyond the example its messages give. It reports names,
# which the loader resolves, and never raises. A line it cannot read is reported and
# skipped, so one bad edit costs its own entry and not the whole file.

from .vocabulary import (BOARD, CHANNEL_KINDS, COLOURS, COMPONENTS, CURVES, HUB, HUB_POSITIONS,
                         OUTPUT_SETTINGS, SCREEN_SETTINGS, TILING, TILING_ALSO)
from .hardware import BOARD_EXAMPLE

# An angle takes everything a fraction does and degrees besides, so its message is
# built from the same words and the two cannot drift apart on what they share
__FRACTION_WANTED = "expected a value from 0 to 1, such as 0.5 or 50%"
__ANGLE_WANTED = __FRACTION_WANTED + ", or an angle from 0deg to 360deg"


class Channel:
    """One channel an entry names, with whatever settings were attached to it."""

    # Every setting that may sit left of the colon, so a channel copied when a bare
    # strip name expands cannot quietly lose one
    SETTINGS = ("level", "colour", "fade", "ease", "rotation", "backlight", "mirror",
                "offset", "background", "pixel_double", "tile")

    def __init__(self, name):
        self.name = name
        self.level = None
        self.colour = None
        self.fade = None
        self.ease = None
        # A screen's own, sitting left of the colon with level and colour, for how it
        # is mounted and lit and how its content is placed
        self.rotation = None
        self.backlight = None
        self.mirror = None
        self.offset = None
        self.background = None
        self.pixel_double = None
        self.tile = None

    def like(self, name):
        """
        The same channel under another name, which is how a bare strip name becomes the
        run of LEDs it stands for.
        """
        made = Channel(name)
        for setting in self.SETTINGS:
            setattr(made, setting, getattr(self, setting))
        return made

    def __repr__(self):
        return "Channel({}, level={}, colour={})".format(self.name, self.level, self.colour)


class Entry:
    """One selector and the effect it plays."""
    def __init__(self, line):
        self.line = line
        self.channels = []
        self.effect = None
        self.settings = {}
        # Where each setting was written, since an entry may run over several lines
        # and a problem belongs to the line the reader has to go and edit
        self.lines = {}
        # The scene this entry belongs to, or None for one before any heading, which
        # is always on
        self.scene = None
        # A heading is an entry of its own, holding the scene's name, hold and restart,
        # and whether its mistake was answered already. None for any other entry
        self.heading = None

    def __repr__(self):
        return "Entry(line={}, {}, {}, {})".format(
            self.line, [c.name for c in self.channels], self.effect, self.settings)


def __split_quoted(text):
    # Whitespace-separated tokens, with quoted runs kept whole and their quotes removed
    tokens = []
    token = ""
    quote = None
    for char in text:
        if quote:
            if char == quote:
                quote = None
            else:
                token += char
        elif char in "\"'":
            quote = char
        # The last of these is a non-breaking space, which arrives from a web page
        # and looks like any other space
        elif char in " \t\xa0":
            if token:
                tokens.append(token)
                token = ""
        else:
            token += char
    if token:
        tokens.append(token)
    return tokens


def unquoted(text, char):
    """Where the first unquoted char sits, or -1. Quoted values may contain it."""
    quote = None
    for index, this in enumerate(text):
        if quote:
            if this == quote:
                quote = None
        elif this in "\"'":
            quote = this
        elif this == char:
            return index
    return -1


def __is_number(text):
    # A run of digits with at most one leading dash, which int() reads as written
    return (text[1:] if text[:1] == "-" else text).isdigit()


def __drive_letter(text, index):
    # Whether the colon at index belongs to a drive letter, as a path pasted from a
    # computer carries. Such a path cannot name anything on a board, but it is one
    # value rather than a second colon, so it is read and answered as a value
    letter = text[index - 1:index]
    stands_alone = letter.isalpha() and not text[index - 2:index - 1].isalpha()
    return stands_alone and text[index + 1:index + 2] in ("\\", "/")


def __unclosed_quote(text):
    # Whether a quote is opened and never closed, which would swallow the colon
    quote = None
    for char in text:
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
    return quote is not None


def __glue(text):
    # Spaces around a range dash, an equals or a pipe removed, so 'out1 - 7',
    # 'level = 50%' and 'ease = 0.05 | 0.3' read as written without them. Commas are
    # left alone, since a space after one is what separates 'level=0.5, 2 level=0.8'
    # into two outputs rather than two values
    out = []
    quote = None

    for char in text:
        if quote:
            out.append(char)
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
            out.append(char)
        elif char in "-=|":
            while out and out[-1] in " \t":
                out.pop()
            out.append(char)
        elif char in " \t" and out and out[-1] in "-=|":
            continue
        else:
            out.append(char)

    return "".join(out)


def read_number(text):
    """A float from a plain number or a percentage, or None if it is neither."""
    text = text.strip()
    scale = 1.0
    if text.endswith("%"):
        text = text[:-1]
        scale = 0.01

    # MicroPython's float() reads '_' and '.' as zero and takes 'inf' and 'nan',
    # none of which anyone means as a number, so a digit has to be there
    if not any(char.isdigit() for char in text):
        return None

    try:
        return float(text) * scale
    except ValueError:
        return None


def __colour(text):
    # An (r, g, b) tuple from a name or six-digit hex, or None
    name = text.strip().lower()
    if name in COLOURS:
        return COLOURS[name]
    if len(name) == 6:
        try:
            value = int(name, 16)
        except ValueError:
            return None
        return (value >> 16, (value >> 8) & 0xff, value & 0xff)
    return None


def __value(text):
    # An effect setting's value as a number, a boolean or the text as given
    lowered = text.lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    number = read_number(text)
    return text if number is None else number


def __scene_time(word):
    # The seconds a heading's time names, written in seconds or minutes, or None for no time
    unit = word[-1:].lower()
    if unit not in ("s", "m"):
        return None
    number = read_number(word[:-1])
    if number is None or unit == "s":
        return number
    return number * 60


def __is_scene_setting(word):
    # Whether a word would be a setting if it sat after the heading's colon
    return word.lower() == "restart" or __scene_time(word) is not None


def value_shown(value):
    """A setting's value as the user would recognise it, quoted where it is text."""
    if isinstance(value, str):
        return "'{}'".format(value)
    if isinstance(value, bool):
        return "true" if value else "false"

    text = str(value)
    return text[:-2] if text.endswith(".0") else text


def value_fault(kind, value):
    """
    What is wrong with a value for a setting of this kind, or None if nothing is.
    Serves both sides of the colon, so a level and a duty answer the same way.
    """
    if kind == "boolean":
        # 1 and 0 are how plenty of people write these, so they are taken as well
        if isinstance(value, bool) or (isinstance(value, float) and value in (0.0, 1.0)):
            return None
        return "expected true or false"

    if kind == "angle":
        # Degrees in range have already become a fraction, so anything still
        # carrying the suffix is out of range. Both notations are named because
        # someone writing 360 has the second one in mind and needs the suffix
        if isinstance(value, float) and 0.0 <= value <= 1.0:
            return None
        return __ANGLE_WANTED

    if kind == "name":
        # Anything numeric is not a file name, however it was written
        if isinstance(value, str):
            return None
        return "expected a file name, such as anim.gif"

    if kind == "quarter":
        if isinstance(value, float) and value in (0.0, 90.0, 180.0, 270.0):
            return None
        return "expected 0, 90, 180 or 270"

    # Anything the parser could not read as a number it left as the text given
    if isinstance(value, bool) or not isinstance(value, float):
        return "expected a number"

    if kind == "fraction" and not 0.0 <= value <= 1.0:
        # "a value from" so the ends cannot read as the only two allowed, and the
        # example so a decimal reads as permitted rather than required
        return __FRACTION_WANTED
    if kind == "seconds" and value < 0.0:
        return "expected a number of seconds, which cannot be negative"
    if kind == "span" and value <= 0.0:
        # An extent of nothing is divided by, so this one has to be caught here
        return "expected a number of outputs above 0, such as 1"
    if kind == "byte" and not 0.0 <= value <= 255.0:
        return "expected 0 to 255"
    if kind == "count" and (value % 1 != 0 or value < 1.0):
        return "expected a whole number of 1 or more"
    if kind == "whole" and value % 1 != 0:
        return "expected a whole number"
    return None


def __expand_hub(spec, token, line, problems):
    # The hub positions one selector item covers, lettered as the silk letters them
    first, dash, last = spec.partition("-")
    if first not in HUB_POSITIONS or len(first) != 1 or \
            (dash and (last not in HUB_POSITIONS or len(last) != 1)):
        problems.append("line {}: '{}' is not a Screen Hub position, which run hubA to "
                        "hub{}".format(line, token, HUB_POSITIONS[-1].upper()))
        return []

    start = HUB_POSITIONS.index(first)
    end = HUB_POSITIONS.index(last) if dash else start
    step = 1 if end >= start else -1
    return [HUB + HUB_POSITIONS[at] for at in range(start, end + step, step)]


def expand(token, prefix, line, problems):
    """The channel names one selector item covers, and the prefix later items inherit."""
    item = token.lower()

    # A hub's positions are letters, so they are read apart from the numbered outputs.
    # A bare letter or letter range after the first item carries the hub on, as a bare
    # number does
    bare = len(item) in (1, 3) and item[0].isalpha() and item[-1].isalpha() and \
        (len(item) == 1 or item[1] == "-")
    if item.startswith(HUB) or (prefix == HUB and bare):
        spec = item[len(HUB):] if item.startswith(HUB) else item
        return __expand_hub(spec, token, line, problems), HUB

    suffix = ""
    if "." in item:
        item, _, suffix = item.partition(".")
        if suffix != "*" and suffix not in COMPONENTS:
            problems.append("line {}: '{}' is not one of r, g, b or *".format(line, suffix))
            return [], prefix

    # A bare number carries the prefix the first item established
    digits = item
    while digits and not digits[0].isdigit():
        digits = digits[1:]
    if len(digits) < len(item):
        prefix = item[:len(item) - len(digits)]
    elif not prefix:
        # Nothing established a name, so the correction carries whatever else was
        # written. A bare number keeps its number and a bare component keeps that. A
        # board that numbers no outputs takes its own LED's name in place of the number
        named = "out" + (digits or "1") if BOARD_EXAMPLE[0].startswith("out") \
            else BOARD_EXAMPLE[0]
        correction = named + ("." + suffix if suffix else "")
        problems.append("line {}: '{}' has no output name before its number. Correct "
                        "it to '{}'".format(line, token, correction))
        return [], prefix

    first, dash, last = digits.partition("-")

    # MicroPython's int() takes underscores anywhere in a number where CPython's
    # does not, so 'out1_' would be an output on a board and a name on a host. The
    # digits are read here instead, and the two answer alike
    if not first.isdigit() or (dash and not __is_number(last)):
        # Not numbered at all, so the whole item is the name, as `rgb` is
        name = prefix + digits
        # The board's own RGB output has components as a numbered output does, and no other
        # name has any, so a star after one is dropped
        if suffix == "*" and name == "rgb":
            return ["{}.{}".format(name, component) for component in COMPONENTS], prefix
        return [name + ("." + suffix if suffix and suffix != "*" else "")], prefix

    first = int(first)
    last = int(last) if dash else first

    # A doubled dash is the only way the end parses negative, since the start is
    # whatever was left after the leading non-digits. Left alone it would count down
    # past zero and report every output it passed through
    if last < 0:
        correction = "{}{}-{}{}".format(prefix, first, -last, "." + suffix if suffix else "")
        problems.append("line {}: '{}' is not a range of outputs. Correct it to "
                        "'{}'".format(line, token, correction))
        return [], prefix

    step = 1 if last >= first else -1
    components = COMPONENTS if suffix == "*" else ((suffix,) if suffix else (None,))

    # Check if the range counts down
    if step < 0:
        # Its components count down too, so 'out7-1.*' runs b, g, r. MicroPython slices
        # a tuple with no step but 1, so reversed() turns it round
        components = tuple(reversed(components))

    names = []
    for number in range(first, last + step, step):
        for component in components:
            names.append("{}{}{}".format(prefix, number, "." + component if component else ""))
    return names, prefix


def __apply_channel_setting(channels, key, raw, line, problems):
    # Set a left-side setting on the channels an item covered, one value or a list

    # An offset is one value in two parts, so it takes the pipe that divides a value
    # rather than the comma that divides one value per output. A * centres that side,
    # which is what leaving the whole setting out does to both
    if key == "offset":
        if "," in raw:
            problems.append("line {}: offset is one value in two parts, so it takes a "
                            "'|'. Correct it to 'offset={}'".format(
                                line, raw.replace(",", "|")))
            return

        parts = [part.strip() for part in raw.split("|")]
        pair = []
        good = len(parts) == 2
        for part in parts if good else ():
            if part == "*":
                pair.append(None)
                continue
            number = read_number(part)
            if number is None:
                good = False
                break
            pair.append(int(number))
        if not good:
            problems.append("line {}: offset is '{}', expected x|y such as "
                            "offset=10|20 or *|20".format(line, raw))
        else:
            for channel in channels:
                channel.offset = tuple(pair)
        return

    # Tiling is one value in two parts as an offset is, a side each, and one part
    # given covers both. The picture repeats from wherever the offset put it, so a
    # panel is filled by a source smaller than it is
    if key == "tile":
        parts = [part.strip().lower() for part in raw.split("|")]
        if len(parts) == 1:
            parts = parts * 2

        words = [TILING_ALSO.get(part, part) for part in parts]
        if len(words) != 2 or any(word not in TILING for word in words):
            problems.append("line {}: tile is '{}', expected {} such as tile=repeat "
                            "for both sides or tile=repeat|off for one".format(
                                line, raw, " or ".join(TILING)))
        else:
            for channel in channels:
                channel.tile = tuple(words)
        return

    values = raw.split(",")
    if len(values) > 1 and len(values) != len(channels):
        problems.append("line {}: {} was given {} values for {} outputs".format(
            line, key, len(values), len(channels)))

    for index, channel in enumerate(channels):
        raw_value = values[index] if index < len(values) else (values[0] if len(values) == 1 else None)
        if raw_value is None:
            continue

        if key in ("colour", "background"):
            colour = __colour(raw_value)
            if colour is None:
                problems.append("line {}: {} '{}' is not a name or six-digit hex".format(
                    line, key, raw_value))
            else:
                setattr(channel, key, colour)
            continue

        # Either curve is one value that may be written in two parts, since a light
        # may come up and go out at its own rate. Each output may still have its own,
        # the comma dividing those as it divides any other setting's
        if key in CURVES:
            other = CURVES[0] if key == CURVES[1] else CURVES[1]
            if getattr(channel, other) is not None:
                problems.append("line {}: an output follows its effect one way, so it "
                                "takes '{}' or '{}' and not both".format(line, key, other))
                continue

            parts = raw_value.split("|")
            seconds = [read_number(part) for part in parts]
            fault = None
            if len(parts) > 2:
                fault = "expected the seconds it takes, in one part or two"
            else:
                for part, value in zip(parts, seconds):
                    fault = value_fault("seconds", part if value is None else value)
                    if fault is not None:
                        break

            if fault is not None:
                problems.append("line {}: {} is '{}', {}, such as {}=0.5 or "
                                "{}=0.05|0.3 for a rise and a fall".format(
                                    line, key, raw_value, fault, key, key))
            else:
                setattr(channel, key, seconds[0] if len(seconds) == 1 else tuple(seconds))
            continue

        # Reported rather than clamped, so 200% is not quietly taken as full and
        # -1 is not quietly taken as off. The channel keeps its default meanwhile
        kind = CHANNEL_KINDS[key]
        value = __value(raw_value)
        fault = value_fault(kind, value)
        if fault is not None:
            problems.append("line {}: {} is {}, {}".format(line, key, value_shown(value), fault))
        elif kind == "quarter":
            setattr(channel, key, int(value))
        elif kind == "boolean":
            setattr(channel, key, bool(value))
        else:
            setattr(channel, key, value)


def __parse_selector(text, line, problems):
    # The left of the colon, as channel items each carrying its own settings
    channels = []
    recent = []
    prefix = ""

    for token in __split_quoted(text):
        if "=" in token:
            key, _, raw = token.partition("=")
            key = key.strip().lower().rstrip(",")
            raw = raw.rstrip(",")
            if key == "color":
                key = "colour"
            elif key == "bg":
                key = "background"
            if key not in ("colour", "background", "offset", "tile") and key not in CHANNEL_KINDS:
                problems.append(
                    "line {}: '{}' is not a setting here, expected an output's {} or a "
                    "screen's {}".format(line, key, ", ".join(OUTPUT_SETTINGS),
                                         ", ".join(SCREEN_SETTINGS)))
            elif not recent:
                problems.append("line {}: {} comes before any output".format(line, key))
            else:
                __apply_channel_setting(recent, key, raw, line, problems)
            continue

        recent = []
        for item in token.split(","):
            if not item:
                continue
            names, prefix = expand(item, prefix, line, problems)
            for name in names:
                channel = Channel(name)
                channels.append(channel)
                recent.append(channel)

    return channels


def __parse_effect(tokens, line, problems, needs_effect=True):
    # The right of the colon, as an effect name then its settings. Each token carries the
    # line it was written on, since an entry may run over several
    effect = None
    settings = {}
    lines = {}

    for token, at in tokens:
        if "=" in token:
            key, _, raw = token.partition("=")
            key = key.strip().lower()
            lines[key] = at

            # An effect that takes a colour of its own wants tuples, and a list of
            # them where it blinks through several. Those are the parts of one
            # setting rather than one value per output, so they take the pipe
            if key in ("colour", "color"):
                wanted = [__colour(part) for part in raw.split("|")]

                # A comma is only the mistake where every part it divides is a
                # colour. Where they are not, something else is wrong with the
                # value, and a comment that ate its tail is the usual something
                if None in wanted and "," in raw and \
                        all(__colour(part) is not None for part in raw.split(",")):
                    problems.append(
                        "line {}: the colours an effect blinks through are one value in "
                        "several parts, so they take '|'. Correct it to '{}={}'".format(
                            at, key, raw.replace(",", "|")))
                elif None in wanted:
                    problems.append("line {}: '{}' is not a colour name or six-digit hex".format(
                        at, raw))
                else:
                    settings["colour"] = wanted[0] if len(wanted) == 1 else wanted
                continue

            # A hold is the dwell where something turns around, and each end may have
            # its own. Those are the two parts of one setting, so they take the pipe
            if key == "hold":
                parts = raw.split("|")
                if len(parts) > 2:
                    problems.append("line {}: hold is the wait at each end, so it takes "
                                    "one part or two, such as hold=0.5 or "
                                    "hold=0.8|0.2".format(at))
                else:
                    wanted = [__value(part) for part in parts]
                    settings[key] = wanted[0] if len(wanted) == 1 else tuple(wanted)
                continue

            # A board entry's values are names and file names, so they are kept as
            # written. Read as an effect setting would be, 'drive=yes' becomes a
            # boolean and the reader is answered about a word they did not type
            settings[key] = __value(raw) if needs_effect else raw
        elif effect is None:
            effect = token.lower()
        else:
            problems.append("line {}: '{}' is not a setting, expected name=value".format(at, token))

    if effect is None and needs_effect:
        # Settings without an effect is a different mistake from an empty right
        # side, and is what a misspelt 'board' looks like
        if settings:
            problems.append("line {}: settings are given but no effect is named to "
                            "take them".format(line))
        else:
            problems.append("line {}: no effect is named after the ':'".format(line))

    return effect, settings, lines


def parse(text):
    """Read the effects file. Returns (entries, problems), and never raises."""
    entries = []
    problems = []
    pending = None
    pending_tokens = []
    scene = None
    seen = {}

    def close():
        if pending is None:
            return

        # A board entry carries settings and no effect, and may be written more than
        # once, so it is not checked for the repeats a channel would be
        is_board = len(pending.channels) == 1 and pending.channels[0].name == BOARD
        pending.effect, pending.settings, pending.lines = __parse_effect(
            pending_tokens, pending.line, problems, not is_board)

        # Per scene, since the same output in two scenes is not a repeat
        if not is_board:
            for channel in pending.channels:
                key = (pending.scene, channel.name)
                if key in seen:
                    problems.append("line {}: {} was already set on line {}".format(
                        pending.line, channel.name, seen[key]))
                else:
                    seen[key] = pending.line

        entries.append(pending)

    # A byte order mark is what Notepad puts at the front of a UTF-8 file. It is
    # invisible, so it can only ever be reported as a character nobody can see
    text = text.lstrip("\ufeff")

    explained = False
    jammed = set()

    for number, raw_line in enumerate(text.split("\n")):
        comment = unquoted(raw_line, "#")
        cut = raw_line if comment < 0 else raw_line[:comment]
        written = cut.strip()           # Quoted back as typed, since gluing moves it
        line = __glue(written)

        # A comment written against the text before it, rather than after a space,
        # has taken part of a value with it. One written after a space is a comment
        # and saying so on an unrelated problem would be noise
        if len(cut) < len(raw_line) and cut[-1:] not in ("", " ", "\t"):
            jammed.add(number + 1)

        if not line:
            continue

        # A heading begins a scene, and everything before the first one is always on.
        # Read from what was written, since a name is text and the gluing that serves
        # an entry's ranges and values has nothing to do here
        if written.startswith("["):
            close()
            pending = None
            pending_tokens = []

            if not written.endswith("]"):
                problems.append("line {}: '{}' has no ']' to close it".format(
                    number + 1, written))
                continue

            # A colon divides the name from its settings, as it divides an entry's
            # outputs from its effect, so a name may hold anything including a word
            # that would otherwise be a setting
            name, colon, rest = written[1:-1].partition(":")
            name = name.strip()
            hold = None
            restart = False
            advised = False

            for word in rest.split():
                seconds = __scene_time(word)
                if word.lower() == "restart":
                    restart = True
                elif seconds is None:
                    problems.append("line {}: a scene has no setting '{}', it takes a "
                                    "time such as 30s or 10m, or restart".format(number + 1, word))
                elif seconds > 0:
                    hold = seconds
                else:
                    problems.append("line {}: a scene's time is how long it shows, so "
                                    "it cannot be {}".format(number + 1, word))

            # Settings written where the name goes are kept as the name, since
            # guessing which words were meant as settings is what the colon settles.
            # Saying so is what stops '[Lava 8s]' quietly becoming a scene of that
            # name that never moves on
            if not colon:
                words = name.split()
                taken = 0
                while taken < len(words) - 1 and __is_scene_setting(words[-1 - taken]):
                    taken += 1
                if taken:
                    problems.append(
                        "line {}: '{}' needs a ':' before its settings. Correct it to "
                        "'[{}: {}]'".format(number + 1, written,
                                            " ".join(words[:-taken]),
                                            " ".join(words[-taken:])))
                    advised = True

            if not name:
                problems.append("line {}: this scene has no name inside the "
                                "'[ ]'".format(number + 1))
                continue

            heading = Entry(number + 1)
            heading.heading = {"name": name, "hold": hold, "restart": restart,
                               "advised": advised}
            entries.append(heading)
            scene = name.lower()
            continue

        # An unclosed quote takes the rest of the line into itself, colon and all,
        # so the answer would otherwise be that an entry has no ':' when it plainly does
        if __unclosed_quote(line):
            problems.append("line {}: this has a quote that is never closed".format(number + 1))
            pending = None
            pending_tokens = []
            continue

        # A comment can eat a value, which is what a hex colour pasted with its '#'
        # does. Ending in '=' is what tells that from an ordinary trailing comment,
        # and it has to come first, since after another entry the line reads as one of
        # its continuations and the answer would be about an empty colour
        if len(cut) < len(raw_line) and line.endswith("="):
            problems.append(
                "line {}: '{}' has nothing after the '='. A '#' starts a comment, so "
                "the rest of the line was ignored".format(number + 1, written))
            continue

        colon = unquoted(line, ":")
        if colon >= 0:
            close()
            pending = None
            pending_tokens = []
            selector = line[:colon]
            remainder = line[colon + 1:]

            # One colon divides the outputs from the effect. A second is someone
            # reading it as a separator between every part, so say what the shape is
            # rather than complaining about whatever the stray colon stuck itself to
            second = unquoted(remainder, ":")
            if second >= 0 and not __drive_letter(remainder, second):
                problems.append(
                    "line {}: this has more than one ':'. Settings for the outputs go "
                    "before it and the effect after, such as "
                    "'{} colour=warm: blink'".format(number + 1, BOARD_EXAMPLE[0]))
                continue

            if not selector:
                problems.append(
                    "line {}: no outputs are named before the ':'".format(number + 1))
                continue

            pending = Entry(number + 1)
            pending.scene = scene
            pending.channels = __parse_selector(selector, number + 1, problems)
            pending_tokens = [(token, number + 1) for token in __split_quoted(remainder)]
        elif pending is not None:
            pending_tokens.extend((token, number + 1) for token in __split_quoted(line))
        elif len(cut) < len(raw_line):
            # A comment takes the colon with it, which is what a hex colour pasted
            # with its '#' does, so name that rather than the shape of an entry
            problems.append(
                "line {}: '{}' has no ':'. A '#' starts a comment, so the rest of "
                "the line was ignored".format(number + 1, written))
        elif explained:
            # The shape is said once. A file that is not an effects file at all would
            # otherwise repeat the whole of it on every line
            problems.append("line {}: '{}' has no ':'".format(number + 1, written))
        else:
            # The commonest mistake there is, so this says what an entry looks like
            # instead of naming the state the reader has landed in
            problems.append(
                "line {}: '{}' has no ':'. The outputs go before it and the effect "
                "after, such as '{} colour=warm: blink'".format(number + 1, written,
                                                                BOARD_EXAMPLE[0]))
            explained = True

    close()

    # Where the comment took a value's tail and what remained failed on its own
    # terms, nothing else names the cause, as 'colour=red,#00ff00' answers about 'red,'
    if jammed:
        named = []
        for problem in problems:
            if __about_line(problem) in jammed and "starts a comment" not in problem:
                problem += ". A '#' starts a comment, so the rest of the line was ignored"
            named.append(problem)
        problems = named

    return entries, problems


def __about_line(problem):
    # The line a problem is about. Those about the board as a whole come first
    if problem.startswith("line "):
        number = problem[5:].split(":", 1)[0]
        if number.isdigit():
            return int(number)
    return -1


def in_line_order(problems):
    """
    In the order a reader meets them in the file, since they are found in the order
    the work happens, everything the parser saw and then everything the loader did.
    """
    # The line is read once per problem, since MicroPython recomputes a sort key on
    # every comparison, and the position keeps one line's own order
    ordered =[(__about_line(problem), position, problem)
               for position, problem in enumerate(problems)]
    ordered.sort()
    return [problem for _, _, problem in ordered]
