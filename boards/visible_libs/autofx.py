# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# Reads the effects file a user edits, and turns it into entries a board can play.
# The format is one entry per set of channels:
#
#   out1-6 level=0.5: pulse_wave speed=0.6
#   out3.g: blink speed=1.0 duty=0.3
#
# Channel settings sit left of the colon, effect settings right of it. An entry runs
# until the next selector, so settings may be laid out over several lines.
#
# Nothing here knows which channels a board has. It reports names; the loader resolves
# them. Nothing raises either: a line that cannot be read is reported and skipped, so
# one bad edit costs its own entry and not the whole file.

import io
import os
import sys
import time

from picofx import RGBLED, ColourPlayer, MonoPlayer
from picofx.colour import (BLACK, BLUE, COOL, CYAN, GREEN, MAGENTA, RED, WARM, WHITE, YELLOW,
                           HSVFX, HueStepFX, RainbowFX, RainbowWaveFX, RGBBlinkFX, RGBFX)
from picofx.mono import (BinaryCounterFX, BlinkFX, BlinkWaveFX, FlashFX, FlashSequenceFX,
                         FlickerFX, NoneFX, PulseFX, PulseWaveFX, RandomFX, StaticFX,
                         TrafficLightFX)

# The drive a connected computer sees. Making it writable long enough to leave a
# report belongs to whatever manages that volume, not here.
MOUNT_DIR = "/fx"
CONFIG_PATH = MOUNT_DIR + "/effects.txt"
ERRORS_PATH = MOUNT_DIR + "/errors.txt"

COLOURS = {
    "red": RED, "yellow": YELLOW, "green": GREEN, "cyan": CYAN, "blue": BLUE,
    "magenta": MAGENTA, "warm": WARM, "white": WHITE, "cool": COOL, "black": BLACK,
}

COMPONENTS = ("r", "g", "b")

# The one name on the left that is not a channel. Its entry carries settings about
# the board rather than an effect, so it is the only one with no effect name.
BOARD = "board"


# Each effect, the kind of channel it drives, and how a channel gets its callable:
# None means one effect serves every channel, "pos" means the effect is called with
# the channel's position in the group, and a tuple names a method per channel.
EFFECTS = {
    "none": (NoneFX, "mono", None),
    "static": (StaticFX, "mono", None),
    "blink": (BlinkFX, "mono", None),
    "blink_wave": (BlinkWaveFX, "mono", "pos"),
    "flash": (FlashFX, "mono", None),
    "flash_sequence": (FlashSequenceFX, "mono", "pos"),
    "flicker": (FlickerFX, "mono", None),
    "pulse": (PulseFX, "mono", None),
    "pulse_wave": (PulseWaveFX, "mono", "pos"),
    "random": (RandomFX, "mono", None),
    "binary_counter": (BinaryCounterFX, "mono", "pos"),
    "traffic_light": (TrafficLightFX, "mono", ("red", "amber", "green")),
    "rgb": (RGBFX, "colour", None),
    "hsv": (HSVFX, "colour", None),
    "rainbow": (RainbowFX, "colour", None),
    "rainbow_wave": (RainbowWaveFX, "colour", "pos"),
    "hue_step": (HueStepFX, "colour", None),
    "rgb_blink": (RGBBlinkFX, "colour", None),
}


class Channel:
    """One channel an entry names, with whatever settings were attached to it."""
    def __init__(self, name):
        self.name = name
        self.level = None
        self.colour = None

    def __repr__(self):
        return "Channel({}, level={}, colour={})".format(self.name, self.level, self.colour)


class Entry:
    """One selector and the effect it plays."""
    def __init__(self, line):
        self.line = line
        self.channels = []
        self.effect = None
        self.settings = {}

    def __repr__(self):
        return "Entry(line={}, {}, {}, {})".format(
            self.line, [c.name for c in self.channels], self.effect, self.settings)


def __split_quoted(text):
    """Whitespace-separated tokens, with quoted runs kept whole and their quotes removed."""
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
        elif char in " \t":
            if token:
                tokens.append(token)
                token = ""
        else:
            token += char
    if token:
        tokens.append(token)
    return tokens


def __unquoted(text, char):
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


def __strip_comment(line):
    """Everything before an unquoted #."""
    quote = None
    for index, char in enumerate(line):
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "#":
            return line[:index]
    return line


def __number(text):
    """A float from a plain number or a percentage, or None if it is neither."""
    text = text.strip()
    scale = 1.0
    if text.endswith("%"):
        text = text[:-1]
        scale = 0.01
    try:
        return float(text) * scale
    except ValueError:
        return None


def __colour(text):
    """An (r, g, b) tuple from a name or six-digit hex, or None."""
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
    """An effect setting's value: a number, a boolean, or the text as given."""
    lowered = text.lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    number = __number(text)
    return text if number is None else number


def __expand(token, prefix, line, problems):
    """The channel names one selector item covers, and the prefix later items inherit."""
    item = token.lower()

    suffix = ""
    if "." in item:
        item, _, suffix = item.partition(".")
        if suffix != "*" and suffix not in COMPONENTS:
            problems.append("line {}: '{}' is not a component, expected r, g, b or *".format(line, suffix))
            return [], prefix

    # A bare number carries the prefix the first item established
    digits = item
    while digits and not digits[0].isdigit():
        digits = digits[1:]
    if len(digits) < len(item):
        prefix = item[:len(item) - len(digits)]
    elif not prefix:
        problems.append("line {}: '{}' has no channel name before its number".format(line, token))
        return [], prefix

    first, dash, last = digits.partition("-")
    try:
        first = int(first)
        last = int(last) if dash else first
    except ValueError:
        # Not numbered at all, so the whole item is the name, as `rgb` is
        return [prefix + digits + ("." + suffix if suffix and suffix != "*" else "")], prefix

    step = 1 if last >= first else -1
    components = COMPONENTS if suffix == "*" else ((suffix,) if suffix else (None,))

    names = []
    for number in range(first, last + step, step):
        for component in components:
            names.append("{}{}{}".format(prefix, number, "." + component if component else ""))
    return names, prefix


def __apply_channel_setting(channels, key, raw, line, problems):
    """Set level or colour on the channels an item covered, one value or a list."""
    values = raw.split(",")
    if len(values) > 1 and len(values) != len(channels):
        problems.append("line {}: {} has {} values for {} channels".format(
            line, key, len(values), len(channels)))

    for index, channel in enumerate(channels):
        raw_value = values[index] if index < len(values) else (values[0] if len(values) == 1 else None)
        if raw_value is None:
            continue

        if key == "level":
            number = __number(raw_value)
            if number is None:
                problems.append("line {}: level '{}' is not a number".format(line, raw_value))
            else:
                channel.level = min(1.0, max(0.0, number))
        else:
            colour = __colour(raw_value)
            if colour is None:
                problems.append("line {}: colour '{}' is not a name or six-digit hex".format(
                    line, raw_value))
            else:
                channel.colour = colour


def __parse_selector(text, line, problems):
    """The left of the colon: channel items, each carrying its own settings."""
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
            if key not in ("level", "colour"):
                problems.append("line {}: '{}' is not a channel setting, expected level or colour".format(
                    line, key))
            elif not recent:
                problems.append("line {}: {} comes before any channel".format(line, key))
            else:
                __apply_channel_setting(recent, key, raw, line, problems)
            continue

        recent = []
        for item in token.split(","):
            if not item:
                continue
            names, prefix = __expand(item, prefix, line, problems)
            for name in names:
                channel = Channel(name)
                channels.append(channel)
                recent.append(channel)

    return channels


def __parse_effect(tokens, line, problems, needs_effect=True):
    """The right of the colon: an effect name then its settings."""
    effect = None
    settings = {}

    for token in tokens:
        if "=" in token:
            key, _, raw = token.partition("=")
            key = key.strip().lower()

            # An effect that takes a colour of its own wants tuples, and a list of
            # them where it blinks through several
            if key in ("colour", "color"):
                wanted = [__colour(part) for part in raw.split(",")]
                if None in wanted:
                    problems.append("line {}: '{}' is not a colour name or six-digit hex".format(
                        line, raw))
                else:
                    settings["colour"] = wanted[0] if len(wanted) == 1 else wanted
                continue

            settings[key] = __value(raw)
        elif effect is None:
            effect = token.lower()
        else:
            problems.append("line {}: '{}' is not a setting, expected name=value".format(line, token))

    if effect is None and needs_effect:
        problems.append("line {}: no effect named".format(line))

    return effect, settings


def parse(text):
    """Read the effects file. Returns (entries, problems); it never raises."""
    entries = []
    problems = []
    pending = None
    pending_tokens = []
    seen = {}

    def close():
        if pending is None:
            return

        # A board entry carries settings and no effect, and may be written more than
        # once, so it is not checked for the repeats a channel would be
        is_board = len(pending.channels) == 1 and pending.channels[0].name == BOARD
        pending.effect, pending.settings = __parse_effect(
            pending_tokens, pending.line, problems, not is_board)

        if not is_board:
            for channel in pending.channels:
                if channel.name in seen:
                    problems.append("line {}: {} was already set on line {}".format(
                        pending.line, channel.name, seen[channel.name]))
                else:
                    seen[channel.name] = pending.line

        entries.append(pending)

    for number, raw_line in enumerate(text.split("\n")):
        line = __strip_comment(raw_line).strip()
        if not line:
            continue

        colon = __unquoted(line, ":")
        if colon >= 0:
            close()
            selector = line[:colon]
            remainder = line[colon + 1:]

            # One colon divides the outputs from the effect. A second is someone
            # reading it as a separator between every part, so say what the shape is
            # rather than complaining about whatever the stray colon stuck itself to
            if __unquoted(remainder, ":") >= 0:
                problems.append(
                    "line {}: this has more than one ':'. Settings for the outputs go "
                    "before it and the effect after, as in "
                    "'out4 colour=warm: blink'".format(number + 1))
                pending = None
                pending_tokens = []
                continue

            pending = Entry(number + 1)
            pending.channels = __parse_selector(selector, number + 1, problems)
            pending_tokens = __split_quoted(remainder)
        elif pending is not None:
            pending_tokens.extend(__split_quoted(line))
        else:
            problems.append("line {}: '{}' comes before any channel".format(number + 1, line))

    close()
    return entries, problems


def report(problems, path):
    """
    Write the problems where the user is already looking, or clear the file when
    there are none, so its presence is the message. Needs the volume writable, and
    says so on the console if it is not.
    """
    if not problems:
        try:
            os.remove(path)
        except OSError:
            pass                # Nothing to clear, or nowhere to clear it from
        return False

    for problem in problems:
        print(problem)

    try:
        with open(path, "w") as handle:
            handle.write("Some of the effects file could not be read.\n")
            handle.write("Everything else is running. Fix these and eject again.\n\n")
            for problem in problems:
                handle.write(problem + "\n")
    except OSError:
        print("could not write", path)

    return True


def indicate(fx, times=3, period_ms=150):
    """
    Flash every output together, red where an output can show colour. Nothing an
    effect does starts like this, so it reads as a signal rather than as the show.
    """
    for _ in range(times):
        for output in fx.outputs:
            if isinstance(output, RGBLED):
                output.set_rgb(255, 0, 0)
            else:
                output.brightness(1.0)
        time.sleep_ms(period_ms)

        for output in fx.outputs:
            if isinstance(output, RGBLED):
                output.set_rgb(0, 0, 0)
            else:
                output.brightness(0.0)
        time.sleep_ms(period_ms)


def __play(fx, volume, path, errors, playing):
    """Stop what is playing, read the file again, and play what it now says."""
    for player in playing:
        player.stop()
    fx.clear()

    try:
        with open(path) as handle:
            text = handle.read()
        players, settings, problems = load(text, fx)

        # A program never returns, so nothing would be left to watch the button.
        # The drive has to go up or there would be no way to change either setting
        if settings.get("program") and settings.get("drive") == "manual":
            problems.append(
                "the drive is shown anyway, since a program is named and hiding it "
                "would leave no way to change one back")
    except OSError:
        # Normally impossible, since the drive rebuilds a missing file. It means the
        # drive is damaged or absent, which is worth showing rather than sitting dark
        players, settings, problems = [], {}, ["could not read " + path]

    if volume is None:
        wrote = report(problems, errors)
    else:
        # The volume is read-only outside this window, which is also where the
        # README is healed
        with volume.writable():
            wrote = report(problems, errors)

    if wrote:
        indicate(fx)

    # A paired player is ticked by its partner, so only the head starts a timer
    if players:
        players[0].start()

    return players, settings, problems


def __run_program(name, problems):
    """
    Run a program the file named instead of the effects. Returns only when it could
    not be run or stopped by itself, so the effects can carry on.
    """
    for candidate in (name, MOUNT_DIR + "/" + name):
        try:
            with open(candidate) as handle:
                source = handle.read()
        except OSError:
            continue
        try:
            # Compiled against its own name, so a traceback says which file and
            # which line rather than naming a string
            exec(compile(source, name, "exec"), {"__name__": "__main__"})
        # Anything at all, since this is a user's own program and it must not be
        # able to take the board down with it
        except Exception as e:      # noqa: BLE001
            # The traceback, since a line number is what makes a program fixable by
            # someone with no way to see a console. Frames from this file are the
            # machinery that ran it and are not the user's to read
            trace = io.StringIO()
            sys.print_exception(e, trace)
            lines = [line for line in trace.getvalue().rstrip().split("\n")
                     if "autofx.py" not in line]
            problems.append("the program {} stopped:\n{}".format(name, "\n".join(lines)))
        return

    problems.append("there is no program called " + name)


def run(fx, volume=None, path=CONFIG_PATH, errors=ERRORS_PATH, interval_ms=20):
    """
    Play the effects file. Without a volume this reads it once and returns the
    players and problems.

    With one, the drive is shown at boot and the button is watched from then on: a
    double press shows or hides it, and hiding or ejecting re-reads the file and
    plays what it now says. An eject does not show the drive again, since a user
    who ejected is done with it. This does not return.

    A board entry can name a program to run instead, and can keep the drive hidden
    until the button asks for it.
    """
    if volume is not None:
        volume.mount()

    players, settings, problems = __play(fx, volume, path, errors, [])

    if volume is None:
        return players, problems

    # The drive goes up before any program runs, since a program that works never
    # returns. Otherwise a mistyped name would leave no way back but a reflash, so a
    # named program overrides drive=manual and __play says as much
    program = settings.get("program")
    shows = program or settings.get("drive") != "manual"

    if shows:
        volume.expose()

    if program:
        __run_program(program, problems)

        # Here because the program could not run, or because it finished by itself.
        # Either way the effects carry on, and anything it went wrong with is said
        # where the user is looking
        if volume.exposed():
            volume.withdraw()
        with volume.writable():
            wrote = report(problems, errors)
        if wrote:
            indicate(fx)
        if shows:
            volume.expose()

    # A stop from the REPL arrives as an exception, and without this the outputs
    # keep whatever they were last written and the computer keeps the drive
    try:
        while True:
            event = volume.service(fx.boot_pressed())
            if event in (volume.HIDDEN, volume.EJECTED, volume.RELOADED):
                players, settings, problems = __play(fx, volume, path, errors, players)
                if event == volume.RELOADED:
                    # A single press asks to try an edit without putting the drive
                    # away, so it goes back once the file has been read
                    volume.expose()
            time.sleep_ms(interval_ms)
    finally:
        for player in players:
            player.stop()
        if volume.exposed():
            volume.withdraw()
        fx.shutdown()


def channels(fx):
    """The board's channels as (name, led) pairs, mono first then colour."""
    mono = []
    colour = []

    for index, output in enumerate(fx.outputs):
        name = "out{}".format(index + 1)
        if isinstance(output, RGBLED):
            # Every output shows colour, and each of its components is a mono channel
            colour.append((name, output))
            for letter, led in zip(COMPONENTS, (output.led_r, output.led_g, output.led_b)):
                mono.append(("{}.{}".format(name, letter), led))
        else:
            mono.append((name, output))

    rgb = getattr(fx, "rgb", None)
    if rgb is not None:
        colour.append(("rgb", rgb))

    return mono, colour


def __build_effect(entry, count, problems):
    """The effect an entry asks for, or None if it could not be made."""
    known = EFFECTS.get(entry.effect)
    if known is None:
        problems.append("line {}: '{}' is not an effect".format(entry.line, entry.effect))
        return None, None, None

    cls, kind, how = known
    settings = dict(entry.settings)
    if how == "pos" and "length" not in settings:
        settings["length"] = count      # A wave spans the group unless told otherwise

    try:
        return cls(**settings), kind, how
    except TypeError as e:
        problems.append("line {}: {} does not take those settings, {}".format(
            entry.line, entry.effect, e))
        return None, None, None


def __callables(effect, how, count, entry, problems):
    """One callable per channel, in the order the entry wrote them."""
    if how is None:
        return [effect] * count
    if how == "pos":
        return [effect(index) for index in range(count)]

    if count > len(how):
        problems.append("line {}: {} drives {} channels, {} named".format(
            entry.line, entry.effect, len(how), count))
    return [getattr(effect, how[index])() if index < len(how) else None
            for index in range(count)]


def load(text, fx):
    """
    Read the effects file. Returns the players it describes, the settings its board
    entries carry, and any problems.
    """
    entries, problems = parse(text)
    mono, colour = channels(fx)

    # Board entries are settings rather than effects, so they are taken out here and
    # handed back for the caller to act on
    board = {}
    wanted_entries = []
    for entry in entries:
        if len(entry.channels) == 1 and entry.channels[0].name == BOARD:
            board.update(entry.settings)
        else:
            wanted_entries.append(entry)
    entries = wanted_entries

    slots = {}
    for kind, pairs in (("mono", mono), ("colour", colour)):
        for index, (name, _) in enumerate(pairs):
            slots[name] = (kind, index)

    effects = {"mono": [None] * len(mono), "colour": [None] * len(colour)}
    levels = {"mono": [1.0] * len(mono), "colour": [1.0] * len(colour)}
    colours = {"colour": [(255, 255, 255)] * len(colour)}
    claimed = {}

    for entry in entries:
        count = len(entry.channels)
        effect, kind, how = __build_effect(entry, count, problems)
        if effect is None:
            continue

        # Position is the channel's place as written, so a rejected channel does not
        # shift the phase of the ones after it
        wanted = []
        for position, channel in enumerate(entry.channels):
            slot = slots.get(channel.name)
            if slot is None:
                problems.append("line {}: this board has no {}".format(entry.line, channel.name))
            elif kind == "colour" and slot[0] != "colour":
                # A mono channel cannot show a colour, but a colour channel can play a
                # mono effect: the player draws it in the channel's own tint
                problems.append("line {}: {} needs a colour channel, {} is mono".format(
                    entry.line, entry.effect, channel.name))
            else:
                wanted.append((channel, slot[0], slot[1], position))

        if not wanted:
            continue

        for channel, where, _, _ in wanted:
            # A colour output and its own components drive the same hardware, so both
            # claim the components and any overlap collides whichever came first
            if where == "colour" and "." not in channel.name:
                parts = ["{}.{}".format(channel.name, letter) for letter in COMPONENTS]
            else:
                parts = [channel.name]

            # Once per channel, and only where a different channel holds the
            # hardware. The same channel named twice is already reported as a repeat,
            # and a colour output covers three parts, so this would say it three times
            clash = None
            for part in parts:
                held = claimed.get(part)
                if held is not None and held[0] != entry.line and held[1] != channel.name:
                    clash = held
                    break

            if clash is not None:
                problems.append("line {}: {} shares its hardware with {}, set on line {}".format(
                    entry.line, channel.name, clash[1], clash[0]))

            for part in parts:
                claimed[part] = (entry.line, channel.name)

        # The channel decides which player it belongs to, not the effect: a colour
        # channel playing a mono effect shows it in that channel's tint
        given = __callables(effect, how, count, entry, problems)
        for channel, where, index, position in wanted:
            effects[where][index] = given[position]
            if channel.level is not None:
                levels[where][index] = channel.level
            if channel.colour is not None and where == "colour":
                colours[where][index] = channel.colour

    players = []
    if any(item is not None for item in effects["mono"]):
        player = MonoPlayer([led for _, led in mono])
        player.effects = effects["mono"]
        player.levels = levels["mono"]
        players.append(player)

    if any(item is not None for item in effects["colour"]):
        player = ColourPlayer([led for _, led in colour])
        player.effects = effects["colour"]
        player.levels = levels["colour"]
        player.colours = colours["colour"]
        players.append(player)

    # One timer drives both, so the two stay in step
    if len(players) == 2:
        players[0].pair(players[1])

    return players, board, problems
