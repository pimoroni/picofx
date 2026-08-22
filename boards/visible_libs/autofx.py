# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# Reads the effects file a user edits, and turns it into entries a board can play.
# The format is one entry per set of outputs:
#
#   out1-6 level=0.5: pulse_wave speed=0.6
#   out3.g: blink speed=1.0 duty=0.3
#   screenA: gif file="anim.gif"
#
# A [Heading: 30s] begins a scene that shows for its time; scenes take turns, and
# entries before the first heading are always on.
#
# Output settings sit left of the colon, effect settings right of it. An entry runs
# until the next selector, so settings may be laid out over several lines. Everything
# a user reads says output, where the code says channel: a channel is a slot in a
# player, and an output is the connector a channel drives.
#
# Nothing in the parser knows which channels a board has. It reports names; the loader
# resolves them. Nothing raises either: a line that cannot be read is reported and
# skipped, so one bad edit costs its own entry and not the whole file.

import io
import os
import sys
import time

from picofx import RGBLED, ColourPlayer, MonoPlayer, StripPlayer, ease, fade
from picofx.colour import (BLACK, BLUE, COOL, COLOUR_EFFECTS, CYAN, GREEN, MAGENTA, RED,
                           WARM, WHITE, YELLOW)
from picofx.mono import MONO_EFFECTS, NoneFX

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

# A strip's LEDs are named like the outputs, so 'stripL1-10' is a range of them and
# the bare name is the whole run. One kind of channel per connector, since each is a
# player of its own writing to its own strip.
STRIPS = ("stripl", "stripr")

# The channels that can show a colour, so a colour effect may play on them and a mono
# effect is drawn in the tint they hold. A strip is one of these; a mono channel is not.
CHROMATIC = ("colour",) + STRIPS

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

# The selector names that reach a screen: each SP/CE port's name, attribute and SPI
SCREEN_PORTS = {
    "screena": ("A", "spce_a", 0),
    "screenb": ("B", "spce_b", 1),
}

# The one selector that plays sound. "wav" streams a file for as long as it lasts,
# or for good with loop=true. The file is opened at load, while the board is sure
# to hold the drive, and a handle opened then plays on after a computer takes the
# volume, where opening it later would find no drive at all.
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
# cannot discover for itself.
BOARD_SETTINGS = {"drive": ("manual",), "reload": ("manual", "auto"),
                  "program": None, "args": None,
                  "screena": ("2.8", "1.54"), "screenb": ("2.8", "1.54"),
                  "stripl": None, "stripr": None}

# The board settings whose value is a number rather than one of a set of words
BOARD_COUNTS = STRIPS

# Short of full, which is uncomfortable on an indicator at arm's length and buys no
# legibility across a room
INDICATOR_LEVEL = 0.75

# One length for all of them, so the count is the only thing carrying the scale
FLASH_MS = 150

# What the outputs say where a file cannot, as (colour, level, times, period). Every
# board carries indicator LEDs shadowing its outputs, so colour reaches a user
# whatever they have wired in and is what they read first; the count reaches anyone
# whose indicators are removed. Both climb with how much trouble the reader is in,
# and red lands on the one condition with nothing else to say it, errors.txt speaking
# for the blue and the drive itself for the white. Never red against green, the pair
# most often confused by eye.
#
# White lights three channels and still reads dimmer than one channel does at the
# same level, so its own is set by eye rather than calculated.

BLOCKED = (WHITE, 0.5, 1, FLASH_MS)              # The computer was mid-write, nothing happened
PROBLEM = (BLUE, INDICATOR_LEVEL, 2, FLASH_MS)   # Written down as well, in errors.txt
UNREPORTED = (RED, INDICATOR_LEVEL, 3, FLASH_MS)  # Nowhere to write it, so this is all there is

# Shown while the computer is copying, as (colour, resting level, travelling level).
# White is the computer's colour here, a spot travelling the outputs while it works
# and one bright flash of every output where it refused a press, so the flash reads
# on top. The spot stays below BLOCKED's level for that reason, and the floor stays
# above the point an output stops being visibly lit, measured at 12 of 255.
TRANSFER = (WHITE, 0.1, 0.35)

# How long the spot spends on each output, and how long the whole thing is held on
# past the transfer. Each file a user drags is its own run of busy, and the outputs
# would otherwise stop and start between them.
TRANSFER_STEP_MS = 120
TRANSFER_HOLD_MS = 500

# What one pass of the spot costs as the drive changes hands, per output. Half the
# transfer's step: this says something happened rather than that it is still going
HANDOVER_STEP_MS = TRANSFER_STEP_MS // 2

# An angle takes everything a fraction does and degrees besides, so its message is
# built from the same words and the two cannot drift apart on what they share
__FRACTION_WANTED = "expected a value from 0 to 1, such as 0.5 or 50%"
__ANGLE_WANTED = __FRACTION_WANTED + ", or an angle from 0deg to 360deg"


class Channel:
    """One channel an entry names, with whatever settings were attached to it."""

    # Every setting that may sit left of the colon, so a channel copied when a bare
    # strip name expands cannot quietly lose one. Checked against __init__ on the host.
    SETTINGS = ("level", "colour", "fade", "ease", "rotation", "backlight", "mirror",
                "offset", "background", "pixel_double", "tile")

    def __init__(self, name):
        self.name = name
        self.level = None
        self.colour = None
        self.fade = None
        self.ease = None
        # A screen's own, sitting left of the colon with level and colour: how it is
        # mounted and lit, and how its content is placed
        self.rotation = None
        self.backlight = None
        self.mirror = None
        self.offset = None
        self.background = None
        self.pixel_double = None
        self.tile = None

    def like(self, name):
        """The same channel under another name, which is how a bare strip name
        becomes the run of LEDs it stands for."""
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
        # is always on. A heading itself is an entry whose heading carries (name,
        # seconds) and nothing else
        self.scene = None
        self.heading = None

    def __repr__(self):
        return "Entry(line={}, {}, {}, {})".format(
            self.line, [c.name for c in self.channels], self.effect, self.settings)


class Scene:
    """One named scene: its content in the form the players take, ready to switch to."""
    def __init__(self, name, line, hold, restart=False):
        self.name = name
        self.key = name.lower()
        self.line = line
        self.hold = hold            # Seconds it shows for, or None to hold forever
        self.restart = restart      # Whether its content begins again on every entry
        # Whether its heading has already been answered, so one mistake is not
        # reported twice: a heading missing its colon has no time either
        self.advised = False
        self.effects = None
        self.levels = None
        self.colours = None
        self.curves = None
        self.driven = set()         # The slots this scene fills, which a switch clears
        # What this scene's entries built, one per entry, which is what a restart
        # has to reach: a travelling effect hands the player a closure and keeps the
        # object the offset lives on
        self.sources = []

    def __repr__(self):
        return "Scene({}, line={}, hold={}, restart={})".format(
            self.name, self.line, self.hold, self.restart)


class ScreenShow:
    """One panel and the player feeding it, serviced from the caller's own loop.

    The player holds the clock, so service() may be called as often as the caller
    likes and a frame goes to the glass only when it changes.
    """
    def __init__(self, screen, player, channel, scene=None):
        import picovector

        self.screen = screen
        self.player = player
        self.scene = scene
        self.rotation = channel.rotation if channel.rotation is not None else 0
        self.mirror = bool(channel.mirror)
        self.offset = channel.offset
        self.pixel_double = bool(channel.pixel_double)
        # The words a file writes, turned into the driver's own values here, which is
        # the one place a screen is certainly present to have them
        if channel.tile is None:
            self.tile = False
        else:
            from screens import Tile
            modes = {"off": Tile.OFF, "repeat": Tile.REPEAT, "mirror": Tile.MIRROR}
            self.tile = tuple(modes[word] for word in channel.tile)
        self.background = (picovector.color.rgb(*channel.background)
                           if channel.background is not None else picovector.color.black)
        self.__backlight = channel.backlight
        self.__lit = False
        self.__redraw = False
        self.__due = False
        # Whether this show has the panel. Only a scene takes it away, so a file
        # without scenes never has to say so
        self.live = True

    def wants(self):
        """
        Whether a frame is due: the player has moved on, or the panel has been put
        aside and needs its picture back. A still moves once and never again, so
        nothing else would light it a second time.

        The answer is held until the frame is taken, since asking a player twice
        is asking it to advance twice.
        """
        if not self.__due:
            self.__due = self.player.has_advanced() or self.__redraw
        return self.__due

    def stage(self):
        """Convert the frame due, for update_pair() to stream beside another's."""
        self.__due = False
        self.__redraw = False
        self.screen.prepare(self.player.image, rotation=self.rotation,
                            mirror=self.mirror, pixel_double=self.pixel_double,
                            offset=self.offset, tile=self.tile,
                            bg_color=self.background)

    def lit(self):
        """
        Light the panel, once it holds the frame and never before: its memory still
        has whatever was last sent, so lighting first shows the picture that has
        gone. on() is for a panel an earlier reload took dark, which a fresh one
        ignores.
        """
        if self.__lit:
            return
        self.__lit = True
        if self.__backlight is not None:
            self.screen.brightness(self.__backlight)
        else:
            self.screen.backlight.on()

    def service(self):
        """This show's frame on its own, where nothing else is due beside it."""
        if not self.wants():
            return
        self.__due = False
        self.__redraw = False
        self.screen.update(self.player.image, rotation=self.rotation, mirror=self.mirror,
                           pixel_double=self.pixel_double, offset=self.offset,
                           tile=self.tile, bg_color=self.background)
        self.lit()

    def pause(self):
        self.player.pause()

    def resume(self):
        self.player.play()

    def rest(self):
        """Put aside by a scene switch: paused and dark, relighting on return."""
        self.player.pause()
        self.screen.backlight.off()
        self.__lit = False
        self.__redraw = True

    def restart(self):
        """Back to the first frame, for a scene that begins again on every entry."""
        self.player.to_first()
        self.__redraw = True


class __Still:
    """One image, standing where a player does for a screen that shows a file."""
    def __init__(self, image):
        self.image = image
        self.__shown = False

    def has_advanced(self):
        if self.__shown:
            return False
        self.__shown = True
        return True

    def pause(self):
        pass

    def play(self):
        pass

    def to_first(self):
        pass                    # One picture is always on its first frame


class __Graphics:
    """
    A drawing standing where a player does: the file's draw(canvas, elapsed) paints
    a canvas the size of the panel, at fps or as often as the screen takes a frame.

    The module body is the setup, run once here and again on a restart, from a code
    object kept so neither ever needs the drive. Its imports are held to IMPORTS,
    which catches a pasted program reaching for hardware the effects are already
    driving; it is a mistake caught, not a boundary, since builtins cannot be
    restricted on this port. A draw() that raises keeps its last frame on the glass
    and says why once, with everything around it carrying on.
    """

    # What drawing needs, and nothing that reaches the pins, the ports or the drive,
    # all of which have owners while a drawing plays beside them
    IMPORTS = ("math", "random", "time", "picovector")

    def __init__(self, name, code, canvas, ground, fps=None, paused=False):
        self.image = canvas
        self.__name = name
        self.__code = code
        self.__ground = ground
        self.__frame_ms = None if not fps else max(1, int(1000 / fps))
        self.__draw = None
        self.__stopped = False
        self.__pushed = False
        self.__seen = None
        # Elapsed accumulates in whole ms rather than running from a start tick: a
        # drawing has no cycle to reduce by, so a fixed origin would outlive the
        # ticks range on a board left running
        self.__elapsed_ms = 0
        self.__playing = not paused
        self.__last = time.ticks_ms()
        self.__begin()

    def __begin(self):
        """Run the module body and the first frame, raising as the file does."""
        import builtins

        original = builtins.__import__

        def guarded(name, *args, **kwargs):
            if name.split(".")[0] not in self.IMPORTS:
                raise ImportError("a drawing can import {}, so {} was refused".format(
                    ", ".join(self.IMPORTS), name))
            return original(name, *args, **kwargs)

        namespace = {"__name__": self.__name, "__file__": self.__name}
        builtins.__import__ = guarded
        try:
            exec(self.__code, namespace)
        finally:
            builtins.__import__ = original

        draw = namespace.get("draw")
        if not callable(draw):
            raise ValueError("it has no draw(canvas, elapsed) for the screen to call")

        # A cleared ground, so beginning again means a blank canvas for a drawing
        # that paints incrementally, and the first frame is drawn before anything
        # is sent, so a file that cannot draw is answered at load
        self.image.pen = self.__ground
        self.image.clear()
        draw(self.image, 0.0)
        self.__draw = draw
        self.__seen = 0             # The frame just drawn is the first step's

    def __tick(self):
        now = time.ticks_ms()
        self.__elapsed_ms += time.ticks_diff(now, self.__last)
        self.__last = now

    def has_advanced(self):
        if self.__stopped:
            return False
        if not self.__pushed:
            self.__pushed = True        # The frame the setup drew
            return True
        if not self.__playing:
            return False

        self.__tick()
        if self.__frame_ms is not None:
            step = self.__elapsed_ms // self.__frame_ms
            if step == self.__seen:
                return False
            self.__seen = step

        try:
            self.__draw(self.image, self.__elapsed_ms / 1000)
        except Exception as e:      # noqa: BLE001
            self.__stop(e)
            return False
        return True

    def __stop(self, error):
        """Keep the last frame and say why, once; the loop around this carries on."""
        self.__stopped = True
        trace = io.StringIO()
        sys.print_exception(error, trace)
        lines = [line for line in trace.getvalue().rstrip().split("\n")
                 if "autofx.py" not in line]
        message = ("the drawing {} stopped, so its screen keeps its last "
                   "frame:\n{}".format(self.__name, "\n".join(lines)))
        print(message)
        # Where the reader is already looking, while the board holds the volume;
        # exposed, the mount is gone and there is nowhere to write
        try:
            with open(ERRORS_PATH, "a") as handle:
                handle.write("\n" + message + "\n")
        except OSError:
            pass

    def pause(self):
        if self.__playing:
            self.__tick()
            self.__playing = False

    def play(self):
        if not self.__playing:
            self.__last = time.ticks_ms()
            self.__playing = True

    def to_first(self):
        """Begin again: the setup runs afresh on a cleared canvas, at elapsed zero."""
        self.__stopped = False
        self.__pushed = False
        self.__seen = None
        self.__elapsed_ms = 0
        self.__last = time.ticks_ms()
        try:
            self.__begin()
        except Exception as e:      # noqa: BLE001
            self.__stop(e)


class Sound:
    """
    One WAV playing beside the effects: the player it runs on, the file it reads,
    already open, and whether it starts again when it ends. The handle stays the
    board's for the whole run, so a computer taking the drive does not stop it.
    """
    def __init__(self, wav, handle, loop):
        self.wav = wav
        self.handle = handle
        self.loop = loop

    def start(self):
        try:
            self.wav.play_wav(self.handle, loop=self.loop)
        except (OSError, ValueError):
            # The file was replaced while a computer held the drive, so there is
            # nothing left to play until the next reload reopens it
            pass

    def pause(self):
        self.wav.pause()

    def resume(self):
        self.wav.resume()

    def close(self):
        self.wav.deinit()
        try:
            self.handle.close()
        except OSError:
            pass


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


def __is_number(text):
    """A run of digits with at most one leading dash, which int() reads as written."""
    return (text[1:] if text[:1] == "-" else text).isdigit()


def __drive_letter(text, index):
    """
    Whether the colon at index belongs to a drive letter, as a path pasted from a
    computer carries. Such a path cannot name anything on a board, but it is one
    value rather than a second colon, so it is read and answered as a value.
    """
    letter = text[index - 1:index]
    stands_alone = letter.isalpha() and not text[index - 2:index - 1].isalpha()
    return stands_alone and text[index + 1:index + 2] in ("\\", "/")


def __unclosed_quote(text):
    """Whether a quote is opened and never closed, which would swallow the colon."""
    quote = None
    for char in text:
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
    return quote is not None


def __glue(text):
    """
    Spaces around a range dash, an equals or a pipe removed, so 'out1 - 7',
    'level = 50%' and 'ease = 0.05 | 0.3' read as written without them. Commas are
    left alone: a space after one is what separates 'level=0.5, 2 level=0.8' into two
    outputs rather than two values.
    """
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


def __number(text):
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


def __scene_time(word):
    """The seconds a heading's setting names, or None where it names no time."""
    if not word.lower().endswith("s"):
        return None
    return __number(word[:-1])


def __is_scene_setting(word):
    """Whether a word would be a setting if it sat after the heading's colon."""
    return word.lower() == "restart" or __scene_time(word) is not None


def __degrees(text):
    """A fraction of a turn from 0 to 360 written with 'deg', or None if it is not."""
    if not isinstance(text, str) or not text.lower().endswith("deg"):
        return None

    number = __number(text[:-3])
    if number is None or not 0.0 <= number <= 360.0:
        return None
    return number / 360.0


def __shown(value):
    """A setting's value as the user would recognise it, quoted where it is text."""
    if isinstance(value, str):
        return "'{}'".format(value)
    if isinstance(value, bool):
        return "true" if value else "false"

    text = str(value)
    return text[:-2] if text.endswith(".0") else text


def __value_fault(kind, value):
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


def __expand(token, prefix, line, problems):
    """The channel names one selector item covers, and the prefix later items inherit."""
    item = token.lower()

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
        # written: a bare number keeps its number, a bare component keeps that
        correction = "out{}{}".format(digits or "1", "." + suffix if suffix else "")
        problems.append("line {}: '{}' has no output name before its number. Correct "
                        "it to '{}'".format(line, token, correction))
        return [], prefix

    first, dash, last = digits.partition("-")

    # MicroPython's int() takes underscores anywhere in a number where CPython's
    # does not, so 'out1_' would be an output on a board and a name on a host. The
    # digits are read here instead, and the two answer alike
    if not first.isdigit() or (dash and not __is_number(last)):
        # Not numbered at all, so the whole item is the name, as `rgb` is
        return [prefix + digits + ("." + suffix if suffix and suffix != "*" else "")], prefix

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

    names = []
    for number in range(first, last + step, step):
        for component in components:
            names.append("{}{}{}".format(prefix, number, "." + component if component else ""))
    return names, prefix


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


def __apply_channel_setting(channels, key, raw, line, problems):
    """Set a left-side setting on the channels an item covered, one value or a list."""
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
            number = __number(part)
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
            seconds = [__number(part) for part in parts]
            fault = None
            if len(parts) > 2:
                fault = "expected the seconds it takes, in one part or two"
            else:
                for part, value in zip(parts, seconds):
                    fault = __value_fault("seconds", part if value is None else value)
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
        fault = __value_fault(kind, value)
        if fault is not None:
            problems.append("line {}: {} is {}, {}".format(line, key, __shown(value), fault))
        elif kind == "quarter":
            setattr(channel, key, int(value))
        elif kind == "boolean":
            setattr(channel, key, bool(value))
        else:
            setattr(channel, key, value)


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
            names, prefix = __expand(item, prefix, line, problems)
            for name in names:
                channel = Channel(name)
                channels.append(channel)
                recent.append(channel)

    return channels


def __parse_effect(tokens, line, problems, needs_effect=True):
    """
    The right of the colon: an effect name then its settings. Each token carries the
    line it was written on, since an entry may run over several.
    """
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
    """Read the effects file. Returns (entries, problems); it never raises."""
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
        cut = __strip_comment(raw_line)
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
                                    "time such as 30s, or restart".format(number + 1, word))
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
        # and it has to come first: after another entry the line reads as one of its
        # continuations, and the answer would be about an empty colour
        if len(cut) < len(raw_line) and line.endswith("="):
            problems.append(
                "line {}: '{}' has nothing after the '='. A '#' starts a comment, so "
                "the rest of the line was ignored".format(number + 1, written))
            continue

        colon = __unquoted(line, ":")
        if colon >= 0:
            close()
            pending = None
            pending_tokens = []
            selector = line[:colon]
            remainder = line[colon + 1:]

            # One colon divides the outputs from the effect. A second is someone
            # reading it as a separator between every part, so say what the shape is
            # rather than complaining about whatever the stray colon stuck itself to
            second = __unquoted(remainder, ":")
            if second >= 0 and not __drive_letter(remainder, second):
                problems.append(
                    "line {}: this has more than one ':'. Settings for the outputs go "
                    "before it and the effect after, such as "
                    "'out4 colour=warm: blink'".format(number + 1))
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
                "after, such as 'out4 colour=warm: blink'".format(number + 1, written))
            explained = True

    close()

    # Where the comment took a value's tail and what remained failed on its own
    # terms, nothing else names the cause: 'colour=red,#00ff00' answers about 'red,'
    if jammed:
        named = []
        for problem in problems:
            if __about_line(problem) in jammed and "starts a comment" not in problem:
                problem += ". A '#' starts a comment, so the rest of the line was ignored"
            named.append(problem)
        problems = named

    return entries, problems


def __about_line(problem):
    """The line a problem is about. Those about the board as a whole come first."""
    if problem.startswith("line "):
        number = problem[5:].split(":", 1)[0]
        if number.isdigit():
            return int(number)
    return -1


def __in_line_order(problems):
    """
    In the order a reader meets them in the file, since they are found in the order
    the work happens: everything the parser saw, then everything the loader did.

    Reading the line once per problem rather than through a sort key, which
    MicroPython recomputes on every comparison, and the position keeps one line's own
    order.
    """
    ordered = [(__about_line(problem), position, problem)
               for position, problem in enumerate(problems)]
    ordered.sort()
    return [problem for _, _, problem in ordered]


def report(problems, path, running=True):
    """
    Write the problems where the user is already looking, or clear the file when
    there are none, so its presence is the message. Needs the volume writable.

    Returns whether they were written. A caller that cannot write them has only the
    outputs left to say anything with, which is a different signal from one whose
    reader has a file to go and read.
    """
    if not problems:
        try:
            os.remove(path)
        except OSError:
            pass                # Nothing to clear, or nowhere to clear it from
        return False

    # In file order, since the reader has the file open beside this. load() has
    # ordered its own already, but run() appends a program's troubles afterwards
    problems = __in_line_order(problems)

    for problem in problems:
        print(problem)

    try:
        with open(path, "w") as handle:
            # General, since a named program that will not run is reported here too
            # and the effects file may have read perfectly. The second line is not
            # always true: a file that fails whole leaves nothing running at all
            handle.write("These are the problems the board found.\n")
            handle.write("{}. Fix them and eject again.\n\n".format(
                "Everything else is running" if running else "Nothing is running"))
            for problem in problems:
                handle.write(problem + "\n")
    except OSError:
        # A full drive fails after the file exists, so what is left is an empty
        # errors.txt promising an account it does not carry. Nothing says less but
        # lies less too, and the caller flashes a signal of its own instead
        print("could not write", path)
        try:
            os.remove(path)
        except OSError:
            pass
        return False

    return True


def indicate(fx, pattern=PROBLEM):
    """
    Flash every output together in the pattern's colour, or plain where an output
    shows none. Nothing an effect does starts like this, so it reads as a signal
    rather than as the show.
    """
    colour, level, times, period_ms = pattern
    red, green, blue = (part * level for part in colour)

    for _ in range(times):
        for output in fx.outputs:
            if isinstance(output, RGBLED):
                output.set_rgb(red, green, blue)
            else:
                output.brightness(level)
        time.sleep_ms(period_ms)

        for output in fx.outputs:
            if isinstance(output, RGBLED):
                output.set_rgb(0, 0, 0)
            else:
                output.brightness(0.0)
        time.sleep_ms(period_ms)


def __play(fx, volume, path, errors, playing, sounding=(), maker=None):
    """
    Stop what is playing, read the file again, and play what it now says.

    Takes a board or something that makes one, and hands the board back: the file is
    what declares a strip, so on the first read there is nothing built yet. `maker`
    is passed through to load(), which rebuilds the board where its entry changed.
    """
    for player in playing:
        player.stop()

    # A sound's handle belongs to the file just set aside, so it closes here and
    # the read below opens whatever the file names now
    for sound in sounding:
        sound.close()

    # clear() covers a strip as well as the outputs, and a strip holds its last frame
    # once nothing is writing it, so a file that no longer names one leaves it dark.
    # The rail follows the players: down here with everything stopped, up again in
    # __start() once something is driving the header
    if not callable(fx):
        fx.clear()
        # The panels go out with the lights. Left lit they are the one thing still
        # showing the file that has just been set aside, and a screen an entry no
        # longer names would stay lit for good
        for screen, _size in __SCREENS.values():
            screen.backlight.off()
        rail = getattr(fx, "disable_rail", None)
        if rail is not None:
            rail()

    text = None
    players, shows, sounds, scenes, settings, problems = [], [], [], [], {}, []

    # The mount point is the board's own, where the reader sees a drive with a file
    # on it, so messages name the file rather than the path
    name = path.rsplit("/", 1)[-1]

    try:
        with open(path) as handle:
            text = handle.read()
    except UnicodeError:
        # An editor saved it as UTF-16, which Notepad offers as "Unicode". Nothing
        # of it can be read, so the encoding is the only thing worth saying
        problems.append("{} is not plain text, so none of it could be read. Save it "
                        "as UTF-8 and eject again.".format(name))
    except OSError:
        # Normally impossible, since the drive rebuilds a missing file. It means the
        # drive is damaged or absent, which is worth showing rather than sitting dark
        problems.append("could not read " + name)

    if text is not None:
        try:
            fx, players, shows, sounds, scenes, settings, problems = load(text, fx, maker)
        # A file a user typed must never be able to take the board down. Anything
        # load does not report itself costs the whole file, where its own reporting
        # costs one entry, but the drive and the button survive to be edited again
        except Exception as e:      # noqa: BLE001
            problems.append("the board failed reading the effects file: {}. The "
                            "fault is in the board, not the file.".format(repr(e)))

        # A program never returns, so nothing would be left to watch the button.
        # The drive has to go up or there would be no way to change either setting
        if settings.get("program") and settings.get("drive") == "manual":
            problems.append(
                "the drive is shown anyway, since a program is named and hiding it "
                "would leave no way to change one back")

    # Nothing declared anything, the file being unreadable or its loading having
    # failed, and the board still has to come up: it is what answers on the lights
    if callable(fx):
        fx = fx()

    # Without a volume nothing here will run the program, so the screen entries it
    # deferred are wanted now rather than never
    if volume is None:
        shows = __pending_shows(problems)

    if volume is None:
        wrote = report(problems, errors, bool(players or sounds))
    else:
        with volume.writable():
            wrote = report(problems, errors, bool(players or sounds))

    # A drive that is full, damaged or absent all end here, the report having had
    # nowhere to go, and the outputs are then the only thing left to say it with
    if problems:
        indicate(fx, PROBLEM if wrote else UNREPORTED)

    # Started by the caller, which is the only one that knows whether a program is
    # about to take the board over
    return fx, players, shows, sounds, scenes, settings, problems


# What the players are ticked at. picofx defaults to 100, which a board driving
# screens as well cannot afford: the timer runs on the same core as the frames, and
# at 100 a frame measured 214ms against 44ms with the players stopped, where 50
# costs 87ms. Effects tick by elapsed time, so the rate is smoothness alone.
PLAYER_FPS = 50


# Whether two screens will stream together. Set false where a pair was refused,
# which is a fact about how the screens were built and will not change while they
# are the screens there are
__PAIRING = True


def __service_shows(shows):
    """
    One pass of every screen that has the panel.

    Two panels on their own ports stream together in about the time one of them
    takes alone, so a frame due on each is sent as a pair. Measured at 58ms
    against 110ms for the two in turn, and 89ms against 155ms with the players
    running. Placement stays per screen, prepare() holding each frame until both
    are ready.
    """
    global __PAIRING

    due = [show for show in shows if show.live and show.wants()]

    if __PAIRING and len(due) == 2 and due[0].screen.port is not due[1].screen.port:
        from screens import update_pair
        try:
            for show in due:
                show.stage()
            update_pair(due[0].screen, due[1].screen)
            for show in due:
                show.lit()
            return
        # Screens built too differently to share a stream, which update_pair says
        # for itself. A staged frame is still waiting on each, and update() sends
        # it, so the fall-through below shows them rather than losing the frame
        except ValueError as e:
            __PAIRING = False
            print("the screens are being drawn one at a time: {}".format(e))

    for show in due:
        show.service()


def __start(players, fx):
    """
    A paired player is ticked by its partner, so only the head starts a timer.

    The strip header's rail comes up here as well, where a strip was built: the
    board leaves it down until asked, and this is when something starts driving it.
    """
    if __STRIPS:
        rail = getattr(fx, "enable_rail", None)
        if rail is not None:
            rail()
    if players:
        players[0].start(fps=PLAYER_FPS)


def __spot(fx, lit):
    """One output at the travelling level, the rest at the resting floor."""
    colour, floor, spot = TRANSFER
    for index, output in enumerate(fx.outputs):
        level = spot if index == lit else floor
        if isinstance(output, RGBLED):
            output.set_rgb(colour[0] * level, colour[1] * level, colour[2] * level)
        else:
            output.brightness(level)


def __handover(fx, to_board):
    """
    The drive changing hands, said with one pass of the spot a transfer travels.

    A double press reloads the board exactly as a single press does, so without
    this nothing on the outputs tells the two apart. Which way the spot runs says
    which way the drive went, reading the outputs as the line they are: the first
    sits by the USB connector and the last at the far end, so a pass towards the
    end is the board taking the drive and one towards the connector is the
    computer taking it. A transfer travels the first way, into the board, which
    is the only direction it can mean: the drive reports a write and never a
    read. Half the transfer's step, so the whole pass is brief.
    """
    count = len(fx.outputs)
    order = range(count) if to_board else range(count - 1, -1, -1)
    for lit in order:
        __spot(fx, lit)
        time.sleep_ms(HANDOVER_STEP_MS)


def __darken(fx):
    """Every output out, leaving a strip to the player that drives it."""
    for output in fx.outputs:
        if isinstance(output, RGBLED):
            output.set_rgb(0, 0, 0)
        else:
            output.brightness(0)


def __transfer_frame(fx, at):
    """
    One frame of the wait shown while the computer is copying: a spot travelling the
    outputs over a resting floor, so a transfer reads as something happening rather
    than as the board having stopped.

    Driven from the caller's own loop rather than a player, since the players are
    stopped for the duration, and stepped from the clock so a frame the transfer
    delays does not slow the travel down.

    Nothing is sent to a strip meanwhile. A frame reaches one as a single timed
    run of bits, and a flash write holds the interrupts off long enough to break
    one apart, which lands as the wrong colours or as a run that overruns the
    LEDs declared into one nothing addresses afterwards. Every frame sent is
    another that can be torn, so the strips are left holding what they have.
    """
    __spot(fx, (at // TRANSFER_STEP_MS) % len(fx.outputs))


def __read_program(name, problems):
    """
    The source of a program the file named, or None if there is none to read.

    Read before the drive is shown, since exposing it unmounts the mount point and a
    program kept on the drive could not be opened once the computer has it.
    """
    # A path is taken as written, since a doubled separator would otherwise fold and
    # '/prog.py' would quietly find the drive's copy. A plain name looks on the drive
    # first, that being the one the reader can see and edit
    wanted = (name,) if name.startswith("/") else (MOUNT_DIR + "/" + name, name)

    found = []
    for candidate in wanted:
        try:
            with open(candidate) as handle:
                found.append(handle.read())
        except OSError:
            continue

    if not found:
        # What is running is said here rather than in the report's heading, which
        # speaks for the file as a whole and is right about it either way
        problems.append("there is no program called {}, so the effects are running "
                        "instead".format(name))
        return None

    # The drive's copy is the one that runs, being the one the reader can see and
    # edit. A copy elsewhere taking its place is a trap: edits to the visible file
    # would do nothing and nothing would say why
    if len(found) > 1:
        problems.append("{} is on the drive and on the board's own filesystem, so "
                        "the drive's copy is the one that runs".format(name))

    return found[0]


def __run_program(name, source, args, problems):
    """Run what was read, and say so if it stops rather than letting it take the board."""
    # The file's arguments arrive the way a program receives them anywhere, so the same
    # file runs unchanged from an editor, where sys.argv is empty and a program falls
    # back to its own constants. sys is built in and its argv cannot be rebound, so the
    # list is filled in place; it outlives the program, so it is emptied afterwards or a
    # reload would inherit the last one's arguments. The name sits at [0] as it does
    # everywhere, which is why a program reads argv[1:] and never argv[0]: no editor
    # supplies one.
    sys.argv[:] = [name] + list(args)

    try:
        # Compiled against its own name, so a traceback says which file and which
        # line rather than naming a string
        exec(compile(source, name, "exec"), {"__name__": "__main__", "__file__": name})
    # Anything at all, since this is a user's own program and it must not be able to
    # take the board down with it
    except Exception as e:      # noqa: BLE001
        # The traceback, since a line number is what makes a program fixable by
        # someone with no way to see a console. Frames from this file are the
        # machinery that ran it and are not the user's to read
        trace = io.StringIO()
        sys.print_exception(e, trace)
        lines = [line for line in trace.getvalue().rstrip().split("\n")
                 if "autofx.py" not in line]
        problems.append("the program {} stopped, so the effects are running "
                        "instead:\n{}".format(name, "\n".join(lines)))
    finally:
        sys.argv.clear()


def run(fx, volume=None, path=CONFIG_PATH, errors=ERRORS_PATH, interval_ms=20):
    """
    Play the effects file. Without a volume this reads it once and returns the board,
    players, shows, sounds, scenes and problems, leaving the servicing and the
    rotation to the caller. Scenes take turns on their own times, and everything
    before the first heading stays on throughout.

    `fx` is a board or something that makes one, a board class being the usual thing,
    since a strip's length is declared at construction and the file is what names it.

    With one, the drive is shown at boot and the button is watched from then on: a
    double press shows or hides it, a single press re-reads the file and puts the
    drive back, and hiding or ejecting re-reads it and leaves it away, since a user
    who ejected is done with it. This does not return.

    The effects stand aside while the computer is copying, and the outputs answer for
    themselves where there is no file to answer in: a problem written down, a problem
    with nowhere to write it, and a press refused mid-write.

    A board entry can name a program to run instead, and can keep the drive hidden
    until the button asks for it. A screen entry is serviced from this loop, so
    without a volume the caller services the shows it is returned.
    """
    # What rebuilds the board where a reload's board entry changes the hardware.
    # A caller handing in a built board keeps it for the whole run
    maker = fx if callable(fx) else None

    if volume is not None:
        volume.mount()

    fx, players, shows, sounds, scenes, settings, problems = __play(
        fx, volume, path, errors, [], (), maker)

    scene_at = 0
    scene_deadline = None

    def begin_scenes():
        """Enter the first scene and set its clock, for a boot and every reload."""
        nonlocal scene_at, scene_deadline
        scene_at = 0
        scene_deadline = None
        if scenes:
            __apply_scene(players, shows, scenes[0])
            if scenes[0].hold:
                scene_deadline = time.ticks_add(time.ticks_ms(), int(scenes[0].hold * 1000))

    if volume is None:
        begin_scenes()
        __start(players, fx)
        for sound in sounds:
            sound.start()
        return fx, players, shows, sounds, scenes, problems

    # A save landing on effects.txt answers as a single press does, where the file
    # asks for that; the older volumes some harnesses hand in have no watch
    watcher = getattr(volume, "watch", None)
    if watcher is not None:
        watcher(settings.get("reload") == "auto")

    # The drive goes up before any program runs, since a program that works never
    # returns. Otherwise a mistyped name would leave no way back but a reflash, so a
    # named program overrides drive=manual and __play says as much
    program = settings.get("program")
    drive_up = program or settings.get("drive") != "manual"

    # A program runs instead of the effects, as the file's own setting says, so they
    # are never started rather than started and stopped: reading the program and
    # showing the drive both take long enough for a flash of them to be seen
    if not program:
        begin_scenes()
        __start(players, fx)
        for sound in sounds:
            sound.start()

    # Read while the board still holds the drive, since exposing it takes the mount
    # point away and a program kept there would have nothing left to open
    source = __read_program(program, problems) if program else None

    if drive_up:
        volume.expose()

    if program:
        if source is not None:
            __run_program(program, source, settings.get("args", ()), problems)

        # The board is the effects' again, so the screen entries put off for the
        # program are built now, before the report, so anything wrong with them is in it
        shows = __pending_shows(problems)

        # Here because the program could not be found or run, or because it finished
        # by itself. Either way the effects take the board back, and anything that
        # went wrong is said where the user is looking
        if volume.exposed():
            volume.withdraw()
        with volume.writable():
            wrote = report(problems, errors, bool(players))
        if problems:
            indicate(fx, PROBLEM if wrote else UNREPORTED)
        begin_scenes()
        __start(players, fx)            # Never started above, whether the program ran or not
        for sound in sounds:
            sound.start()
        if drive_up:
            volume.expose()

    paused = False
    idle_since = None

    # A quick tap can start and end inside one screen's service, which a level read
    # between frames never sees. A board catching presses by interrupt is asked for
    # those instead; the rest are polled, and sampled around each screen as well
    pressed = False
    pending = volume.IDLE

    def watch():
        """
        The button and the drive, looked at between the screens as well as at the
        top of the loop. One pass of the screens can outlast the double press
        window, and an event held back until the next pass reads as the button
        being slow. The first event stands until the loop has taken it.

        The board is asked for its tap each time rather than once: a rebuild hands
        back a new board whose interrupt replaces the old one's, so a method held
        from before would never hear another press.
        """
        nonlocal pending, pressed
        if pending != volume.IDLE:
            return pending

        taps = getattr(fx, "boot_taps", None)
        if taps is None:
            pending = volume.service(pressed or fx.boot_pressed())
            pressed = False
            return pending

        waiting = taps()
        if not waiting:
            pending = volume.service(False)
            return pending

        # The drive reads presses as edges, so every press is offered with the
        # release that ends it. Without that release the next press is still the
        # last one being held, and a double press spread over two passes of this
        # loop reads as a single one
        for _ in range(waiting):
            for held in (True, False):
                event = volume.service(held)
                if event != volume.IDLE:
                    pending = event
        return pending

    # A stop from the REPL arrives as an exception, and without this the outputs
    # keep whatever they were last written and the computer keeps the drive
    try:
        while True:
            event = watch()
            pending = volume.IDLE

            if event == volume.SHOWN:
                # Nothing else happens here: the drive has gone to the computer and
                # the effects carry on. They stand aside for the pass, as they do
                # for a transfer, and take the outputs back after it
                for player in players:
                    player.stop()
                __handover(fx, False)
                __start(players, fx)

            if event in (volume.HIDDEN, volume.EJECTED, volume.RELOADED):
                if event == volume.HIDDEN:
                    # Before the reload, which darkens everything and would swallow it
                    for player in players:
                        player.stop()
                    __handover(fx, True)
                fx, players, shows, sounds, scenes, settings, problems = __play(
                    fx, volume, path, errors, players, sounds, maker)
                paused = False
                idle_since = None
                if watcher is not None:
                    watcher(settings.get("reload") == "auto")
                if event == volume.RELOADED:
                    # A single press asks to try an edit without putting the drive
                    # away, so it goes back once the file has been read. Showing it
                    # waits out the window the computer needs to see the drive
                    # leave, and nothing starts until it has: the lights run from a
                    # timer and the screens from this loop, so starting first would
                    # leave one playing through the wait and the other held still
                    volume.expose()
                begin_scenes()
                __start(players, fx)
                for sound in sounds:
                    sound.start()
                # A frame each as the lights start, so the panels come back with them
                __service_shows(shows)

            # The rotation, standing aside with everything else while a transfer runs
            if scene_deadline is not None and not paused and \
                    time.ticks_diff(time.ticks_ms(), scene_deadline) >= 0:
                scene_at = (scene_at + 1) % len(scenes)
                scene = scenes[scene_at]
                __apply_scene(players, shows, scene)
                scene_deadline = (time.ticks_add(time.ticks_ms(), int(scene.hold * 1000))
                                  if scene.hold else None)

            # A transfer costs a running effect most of a tenth of a second in one
            # hitch, so the effects stand aside for it and something of the board's
            # own travels the outputs instead of the show lurching through
            if volume.busy():
                idle_since = None
                if not paused:
                    for player in players:
                        player.stop()
                    for show in shows:
                        show.pause()
                    # A transfer's stalls are longer than the sound's own buffer, so
                    # it holds silence for the copy instead of crackling through it
                    for sound in sounds:
                        sound.pause()
                    paused = True
            elif paused:
                if idle_since is None:
                    idle_since = time.ticks_ms()
                elif time.ticks_diff(time.ticks_ms(), idle_since) >= TRANSFER_HOLD_MS:
                    __start(players, fx)
                    # A player paints over the wait as it starts, and only the ones
                    # writing the outputs do: a file playing on a strip alone, or on
                    # nothing but its screens, would leave the travelling spot lit
                    if not any(player.kind in OUTPUT_KINDS for player in players):
                        __darken(fx)
                    for show in shows:
                        if show.live:
                            show.resume()
                    for sound in sounds:
                        sound.resume()
                    paused = False

            if paused:
                __transfer_frame(fx, time.ticks_ms())
            else:
                for show in shows:
                    if show.live:
                        show.service()
                    # A frame can cost longer than the double press window, so the
                    # button is answered between them rather than after them all
                    if watch() != volume.IDLE:
                        break

            if event == volume.BUSY:
                # A press the computer's writing blocked otherwise looks exactly like
                # one that did nothing. The effects are already standing aside, so
                # every output flashing reads on top of the one that is travelling,
                # and the next frame paints over it
                indicate(fx, BLOCKED)

            time.sleep_ms(interval_ms)
    finally:
        for player in players:
            player.stop()
        for sound in sounds:
            sound.close()
        # shutdown() releases the screen ports and the header's rail, so neither
        # record of what is running may outlive them, and anything a program put off
        # is never going to be built now
        __SCREENS.clear()
        __STRIPS.clear()
        __PENDING_SHOWS.clear()
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


def __has_strips(fx):
    """Whether this board has the header's strip connectors at all.

    Asked of the class, so no board need exist yet and no property is evaluated:
    MicroPython's dir() and getattr() both run a property's getter, and one that
    answers by raising would read as an absent connector.
    """
    return hasattr(fx if isinstance(fx, type) else type(fx), "strip_l")


def __board(fx, settings, problems):
    """
    The board to play on: whatever the caller handed in, or one built here from what
    the file declared.

    A board that will not take the file's declarations still has to come up, since it
    is what says so on the lights and what watches the button, so it is built plain
    and the reason is reported.
    """
    if not callable(fx):
        return fx

    declared = {}
    for kind in STRIPS:
        count = settings.get(kind)
        if count:
            declared["strip_" + kind[-1]] = count

    if not declared:
        return fx()

    try:
        return fx(**declared)
    except Exception as e:      # noqa: BLE001
        problems.append("the board could not be set up as the file asks: {}".format(e))
        return fx()


# The strips already running, as (strip, count) per connector. A board is built once,
# a reload keeping the one it has, so this is what a changed length is answered against
__STRIPS = {}


def strips(fx, lengths, problems):
    """
    The strips the file asked for, as (kind, strip, count), and the kinds a board
    would not set up.

    A board declares its strips as it is built and hands each back as strip_l or
    strip_r, something taking set_rgb(index, red, green, blue). Those two names are
    the only place this module knows anything about the header, so a board naming its
    connectors differently changes them and nothing else.
    """
    built = []
    failed = set()

    for kind in STRIPS:
        count = lengths.get(kind)
        if not count:
            continue

        running = __STRIPS.get(kind)
        if running is not None:
            strip, leds = running
            if count != leds:
                problems.append("{} is already running with {} LEDs, so its new length "
                                "needs the board turning off and on".format(
                                    __strip_shown(kind), leds))
            lengths[kind] = leds
            built.append((kind, strip, leds))
            continue

        try:
            strip = getattr(fx, "strip_" + kind[-1])
        # Reached where the board refused the length or offers no such connector,
        # which the board's own message may already have said. Said again here so an
        # entry naming the strip is answered rather than left with no slots
        except Exception as e:      # noqa: BLE001
            failed.add(kind)
            lengths.pop(kind, None)
            problems.append("{} could not be set up: {}".format(__strip_shown(kind), e))
            continue

        __STRIPS[kind] = (strip, count)
        built.append((kind, strip, count))

    return built, failed


# How long a presence probe watches a tearing-effect line for. Two periods of a
# 60Hz panel and a little over, which is all it takes to see any edge at all
PRESENCE_PROBE_MS = 40


def __screen_gone(screen):
    """
    Whether a panel that was brought up has stopped answering.

    One unplugged and put back has lost the TEON its bringup set, so it asserts
    nothing. Nothing is sent to find out: a screen owning its line keeps TE on
    from bringup, so any edge at all is the panel still being there. One with no
    signal to read cannot be told about either way, so it counts as present.
    """
    if not screen.v_sync:
        return False
    try:
        return screen.display.te_probe(PRESENCE_PROBE_MS)[2] == 0
    except Exception:      # noqa: BLE001
        return False


def __hardware_changed(fx, declared):
    """
    Whether the board entry no longer matches what is running: a strip added,
    dropped or resized, a screen's size changed, or a panel swapped for another,
    which has to come up again to be talked to. Asked of a running board on a
    reload, so what is running is this module's own record of what it built.
    """
    for kind in STRIPS:
        asked = declared.get(kind)
        running = __STRIPS.get(kind)
        if asked and running is None and __has_strips(fx):
            return True
        if running is not None and asked != running[1]:
            return True
    for name in SCREEN_PORTS:
        asked = declared.get(name)
        known = __SCREENS.get(name)
        if known is None:
            continue
        if asked is not None and asked != known[1]:
            return True
        if __screen_gone(known[0]):
            return True
    return False


def __strip_of(name):
    """The strip a channel name belongs to, or None where it names something else."""
    for kind in STRIPS:
        if name == kind or (name.startswith(kind) and not name[len(kind)].isalpha()):
            return kind
    return None


def __strip_shown(kind):
    """The strip as the reader writes it, the connector letter back in capitals."""
    return kind[:-1] + kind[-1].upper()


def __resolve_strips(entries, lengths, has_strips, problems, said=()):
    """
    Expand a bare strip name into the run of LEDs it stands for, and answer a file
    naming a strip the board entry gave no length. Done as the file is loaded rather
    than as its selectors are parsed, since the board entry carrying the length is
    read in this pass.

    Anything already said for is passed in, a strip the board would not set up having
    been reported where that was found.
    """
    said = set(said)

    for entry in entries:
        resolved = []

        for channel in entry.channels:
            kind = __strip_of(channel.name)
            if kind is None:
                resolved.append(channel)
                continue

            shown = __strip_shown(kind)
            count = lengths.get(kind)

            if not count:
                # Once per strip: a range names its LEDs one by one, and whatever is
                # wrong is wrong for all of them at once
                if kind not in said:
                    said.add(kind)
                    if not has_strips:
                        problems.append("line {}: this board has no strip connectors, "
                                        "so it has no {}".format(entry.line, shown))
                    else:
                        problems.append("line {}: {} needs its length before it can "
                                        "play. Write it like 'board: {}=60'".format(
                                            entry.line, shown, shown))
                continue

            tail = channel.name[len(kind):]

            if "." in tail:
                problems.append(
                    "line {}: each LED on a strip shows one colour, so write it like "
                    "'{}{}'".format(entry.line, shown, tail.partition(".")[0]))
                continue

            if not tail:
                resolved.extend(channel.like("{}{}".format(kind, number))
                                for number in range(1, count + 1))
                continue

            if int(tail) > count:
                problems.append("line {}: {} has {} LEDs, so there is no {}{}".format(
                    entry.line, shown, count, shown, tail))
                continue

            resolved.append(channel)

        entry.channels = resolved


# The screens already built, kept across reloads: construction resets a panel, so a
# reload that still names one repaints it instead of blanking it first
__SCREENS = {}


def __screen_shown(name):
    """The selector as the reader wrote it, the port letter back in capitals."""
    return "screen" + name[6:].upper()


def __find_image(name, line, problems):
    """
    The file or folder a screen entry names, or None if there is none to play. The
    drive's copy wins, as a program's does, and for the same reason: it is the one
    the reader can see and edit.
    """
    wanted = (name,) if name.startswith("/") else (MOUNT_DIR + "/" + name, name)

    found = []
    for candidate in wanted:
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


def __read_drawing(path, target, at, problems):
    """
    A graphics file compiled against its own name, or None with the reason said.
    Compiled while the entries are read, so a file that will not parse is answered
    at load, and kept as a code object so a restart never goes back to the drive.
    """
    try:
        with open(path) as handle:
            source = handle.read()
    except OSError:
        problems.append("line {}: {} could not be read".format(at, target))
        return None

    try:
        return compile(source, target, "exec")
    except SyntaxError as e:
        problems.append("line {}: {} is not Python the board can read: {}".format(
            at, target, e))
        return None


def __make_drawing(code, target, at, channel, screen, settings, fps, asleep, problems):
    """The player for a graphics entry: its canvas, its ground, and the file begun."""
    import picovector

    # The canvas fills the panel as the entry mounts it, so the drawing works in the
    # orientation the reader sees, and pixel_double halves it as it doubles a picture.
    # A width or height the entry states is used as written, whatever else is set
    width, height = screen.width, screen.height
    if (channel.rotation or 0) in (90, 270):
        width, height = height, width
    if channel.pixel_double:
        width, height = width // 2, height // 2
    width = settings.get("width") or width
    height = settings.get("height") or height

    ground = (picovector.color.rgb(*channel.background)
              if channel.background is not None else picovector.color.black)

    try:
        return __Graphics(target, code, picovector.image(width, height), ground,
                          fps=fps, paused=asleep)
    except MemoryError:
        problems.append("line {}: there is no memory left for {}'s canvas, so free "
                        "some or halve it with pixel_double".format(at, target))
    # The traceback, since this is the user's own code and a line number is what
    # makes it fixable; frames from this file are the machinery that ran it
    except Exception as e:      # noqa: BLE001
        trace = io.StringIO()
        sys.print_exception(e, trace)
        lines = [line for line in trace.getvalue().rstrip().split("\n")
                 if "autofx.py" not in line]
        problems.append("line {}: {} could not start:\n{}".format(
            at, target, "\n".join(lines)))
    return None


def __screen_on(fx, name, line, problems, size):
    """
    The panel a selector name reaches, built once and kept: construction resets the
    glass, so a screen is only ever constructed the first time it is asked for, at
    the board entry's size for it or 2.8 unsaid, size being unreadable from a panel.
    """
    known = __SCREENS.get(name)
    if known is not None:
        screen, built_size = known
        if size is not None and size != built_size:
            problems.append("{} is already running as a {} screen, so its new size "
                            "needs the board turning off and on".format(
                                __screen_shown(name), built_size))
        return screen

    from spce import SPCE, SPCEPort

    port_name, attr, spi = SCREEN_PORTS[name]
    port = getattr(fx, attr)
    shown = __screen_shown(name)

    if port.mode is None:
        # The port was never declared, so it becomes a screen port here: the same
        # construction a program would make, made because the file asked for it
        pins = getattr(type(fx), "SPCE_{}_PINS".format(port_name))
        port = SPCEPort(port_name, SPCE.SCREEN, spi, pins)
        setattr(fx, attr, port)
    elif port.mode != SPCE.SCREEN:
        problems.append("line {}: SP/CE {} is set up for something else, so {} cannot "
                        "show anything".format(line, port_name, shown))
        return None

    if size is None:
        size = "2.8"

    # Read here rather than at the top of the file, which also runs on a board with no
    # screens module to import
    from screens import SCREEN_TYPES

    try:
        screen = SCREEN_TYPES[size](port)
    except Exception as e:      # noqa: BLE001
        problems.append("line {}: {} could not start: {}".format(line, shown, e))
        return None

    __SCREENS[name] = (screen, size)
    return screen


# The screen entries a named program deferred, as one (entries, fx, board) or nothing
__PENDING_SHOWS = []


def __pending_shows(problems):
    """The shows a program put off, built now it has given the board back."""
    if not __PENDING_SHOWS:
        return []

    entries, fx, board = __PENDING_SHOWS.pop()

    # The entries were checked when the file was read, so anything wrong with them is
    # already reported and would otherwise be said twice. What is new here is whatever
    # only building can find, a panel that will not start or content that will not play
    found = []
    shows = __build_shows(entries, fx, board, found)
    problems.extend(problem for problem in found if problem not in problems)
    return shows


def __build_shows(entries, fx, board, problems, build=True):
    """
    A show per screen entry: the panel it names and the player feeding it.

    Without `build` the entries are checked and nothing is made, which is what a file
    naming a program wants: its screen entries are answered when it is read, and the
    panels and players wait until the program gives the board back.
    """
    shows = []
    built = set()

    for entry in entries:
        channel = entry.channels[0]
        name = channel.name

        if len(entry.channels) > 1:
            problems.append("line {}: name one screen per entry".format(entry.line))
            continue

        if name not in SCREEN_PORTS or getattr(fx, SCREEN_PORTS[name][1], None) is None:
            offered = [__screen_shown(known) for known in sorted(SCREEN_PORTS)
                       if getattr(fx, SCREEN_PORTS[known][1], None) is not None]
            if offered:
                problems.append("line {}: this board has no {}, it has {}".format(
                    entry.line, __screen_shown(name), " and ".join(offered)))
            else:
                problems.append("line {}: this board has no screens".format(entry.line))
            continue

        # Named twice in one scene is already reported as a repeat, so the later
        # entry only skips; the same screen in two scenes takes turns
        if (entry.scene, name) in built:
            continue

        if entry.effect not in SCREEN_EFFECTS:
            if entry.effect in EFFECTS:
                problems.append("line {}: {} lights the outputs, a screen plays {}".format(
                    entry.line, entry.effect, ", ".join(sorted(SCREEN_EFFECTS))))
            elif entry.effect is not None:
                problems.append("line {}: '{}' is not something a screen plays, "
                                "expected {}".format(entry.line, entry.effect,
                                                     ", ".join(sorted(SCREEN_EFFECTS))))
            continue

        if channel.colour is not None:
            problems.append("line {}: a screen has no colour setting, so it was "
                            "ignored".format(entry.line))

        # The word is right on an output and this is not one, so the correction
        # carries the value across
        if channel.level is not None:
            problems.append("line {}: a screen has no level. Correct it to "
                            "'backlight={}'".format(entry.line, __shown(channel.level)))

        for setting in CURVES:
            if getattr(channel, setting) is not None:
                problems.append("line {}: {} is for the outputs, so it was ignored".format(
                    entry.line, setting))

        settings = __check_settings(entry, SCREEN_EFFECTS[entry.effect], problems)

        # A sequence names a folder where the others name a file, and neither works
        # without one
        wanted = "folder" if "folder" in SCREEN_EFFECTS[entry.effect] else "file"
        target = settings.get(wanted)
        if target is None:
            # A source that was refused, or written under the other key, has been
            # reported already, and one mistake gets one message
            if "file" not in entry.settings and "folder" not in entry.settings:
                if wanted == "folder":
                    example = "folder=/frames"
                elif entry.effect == "graphics":
                    example = "file=clock.py"
                else:
                    example = "file=anim.gif"
                problems.append("line {}: {} needs a {} to play, such as {}".format(
                    entry.line, entry.effect, wanted, example))
            continue

        at = entry.lines.get(wanted, entry.line)
        path = __find_image(target, at, problems)
        if path is None:
            continue

        # A drawing is read and compiled while the entries are checked, so a file
        # that will not parse is answered whether or not anything is built
        code = None
        if entry.effect == "graphics":
            code = __read_drawing(path, target, at, problems)
            if code is None:
                continue

        # Everything above is the entry being read, which a check wants; everything
        # below resets a panel or decodes content, which only a build does
        if not build:
            continue

        screen = __screen_on(fx, name, entry.line, problems, board.get(name))
        if screen is None:
            continue

        # fps and interval both name the pace, one the inverse of the other, so a
        # slideshow can say seconds and an animation can say a rate
        fps = settings.get("fps")
        interval = settings.get("interval")
        if interval is not None:
            if fps is not None:
                problems.append("line {}: {} was given both fps and interval, so fps "
                                "was used".format(entry.line, entry.effect))
            elif interval == 0:
                problems.append("line {}: {}'s interval is 0, expected the seconds "
                                "between frames".format(
                                    entry.lines.get("interval", entry.line), entry.effect))
            else:
                fps = 1.0 / interval

        # A scene's show waits for its scene; the first scene's is woken by the
        # first apply, so every scene starts its content from the top
        asleep = entry.scene is not None

        if entry.effect == "graphics":
            player = __make_drawing(code, target, at, channel, screen, settings,
                                    fps, asleep, problems)
            if player is None:
                continue
            built.add((entry.scene, name))
            shows.append(ScreenShow(screen, player, channel, entry.scene))
            continue

        try:
            if entry.effect == "gif":
                from playback import GIFPlayer
                player = GIFPlayer(path, fps=fps,
                                   loop=settings.get("loop", True),
                                   ping_pong=settings.get("ping_pong", False),
                                   first_as_last=settings.get("first_as_last", False),
                                   hold=settings.get("hold", 0),
                                   paused=asleep)
            elif entry.effect == "sequence":
                from playback import SequencePlayer
                player = SequencePlayer(path, fps=fps,
                                        loop=settings.get("loop", True),
                                        ping_pong=settings.get("ping_pong", False),
                                        first_as_last=settings.get("first_as_last", False),
                                        hold=settings.get("hold", 0),
                                        paused=asleep)
            else:
                import picovector
                player = __Still(picovector.image.load(path))
        except Exception as e:      # noqa: BLE001
            problems.append("line {}: {} could not be played: {}".format(at, target, e))
            continue

        built.add((entry.scene, name))
        shows.append(ScreenShow(screen, player, channel, entry.scene))

    # A screen the file no longer names keeps its last frame but goes dark, since
    # nothing is left to say anything on it. A check has built nothing, so it has
    # nothing to say about which screens are still wanted
    if build:
        names = {used for _, used in built}
        for name, (screen, _) in __SCREENS.items():
            if name not in names:
                screen.backlight.off()

    return shows


def __build_sounds(entries, fx, problems):
    """
    A sound per audio entry, of which the board plays one at a time. The file is
    opened here, while the board holds the drive, which is what lets it stream on
    after a computer takes the volume.
    """
    sounds = []
    wav = getattr(fx, "wav", None)

    for entry in entries:
        if wav is None:
            problems.append("line {}: this board has no audio".format(entry.line))
            continue

        if entry.scene is not None:
            problems.append("line {}: audio does not follow scenes yet, so its entry "
                            "sits before every heading".format(entry.line))
            continue

        if entry.effect not in AUDIO_EFFECTS:
            if entry.effect in EFFECTS or entry.effect in SCREEN_EFFECTS:
                problems.append("line {}: {} does not make a sound, audio plays "
                                "{}".format(entry.line, entry.effect,
                                            ", ".join(sorted(AUDIO_EFFECTS))))
            elif entry.effect is not None:
                problems.append("line {}: '{}' is not something audio plays, expected "
                                "{}".format(entry.line, entry.effect,
                                            ", ".join(sorted(AUDIO_EFFECTS))))
            continue

        channel = entry.channels[0]
        for setting in Channel.SETTINGS:
            if getattr(channel, setting) is not None:
                problems.append("line {}: {} says nothing about a sound, so it was "
                                "ignored".format(entry.line, setting))

        settings = __check_settings(entry, AUDIO_EFFECTS[entry.effect], problems)

        target = settings.get("file")
        if target is None:
            if "file" not in entry.settings:
                problems.append("line {}: {} needs a file to play, such as "
                                "file=sound.wav".format(entry.line, entry.effect))
            continue

        if sounds:
            problems.append("line {}: the board plays one sound at a time, so the "
                            "first audio entry is the one heard".format(entry.line))
            continue

        at = entry.lines.get("file", entry.line)
        path = __find_image(target, at, problems)
        if path is None:
            continue

        try:
            handle = open(path, "rb")
        except OSError as e:
            problems.append("line {}: {} could not be opened: {}".format(at, target, e))
            continue

        sounds.append(Sound(wav, handle, bool(settings.get("loop", False))))

    return sounds


def __check_board(entry, has_strips, problems):
    """
    The board settings the entry carries, with anything it cannot use dropped. A
    board entry names no effect, so nothing else would ever look at these: a typo in
    'drive' or 'program' would leave a board acting as though the line were absent.
    """
    settings = {}

    for key, value in entry.settings.items():
        at = entry.lines.get(key, entry.line)

        if key not in BOARD_SETTINGS:
            problems.append("line {}: the board has no setting '{}', it takes {}".format(
                at, key, ", ".join(sorted(BOARD_SETTINGS))))
            continue

        # Whatever it was written as, since a setting limited to named values is
        # compared against them and a program is a file name
        text = value if isinstance(value, str) else __shown(value)

        # A program's arguments are divided by the pipe that divides any value into
        # parts, and each one reaches the program as it was written. Read here so they
        # skip the path check below, which a time or a Windows path would otherwise trip
        if key == "args":
            settings[key] = tuple(part.strip() for part in text.split("|") if part.strip())
            continue

        # A count is a number where every other board setting is a word or a file
        # name, and this entry keeps its values as written, so it is read here
        if key in BOARD_COUNTS:
            if not has_strips:
                problems.append("line {}: this board has no strip connectors, so it "
                                "has no {}".format(at, __strip_shown(key)))
                continue

            number = __number(text)
            fault = ("expected a number" if number is None
                     else __value_fault("count", number))
            if fault is not None:
                problems.append("line {}: the board's {} is {}, {}".format(
                    at, __strip_shown(key), __shown(text), fault))
            else:
                settings[key] = int(number)
            continue

        allowed = BOARD_SETTINGS[key]
        if allowed is not None:
            if text.lower() not in allowed:
                problems.append("line {}: the board's {} is {}, it takes {}".format(
                    at, key, __shown(value), ", ".join(allowed)))
                continue
            text = text.lower()          # So the caller compares against one spelling

        elif "\\" in text or __unquoted(text, ":") >= 0:
            base = text.replace("\\", "/").rsplit("/", 1)[-1]
            problems.append("line {}: '{}' is a path on your computer. Correct it to "
                            "'{}'".format(at, text, base))
            continue

        settings[key] = text

    return settings


def __check_settings(entry, taken, problems):
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
                fault = __value_fault(kind, part)
                if fault is not None:
                    break
            if fault is not None:
                problems.append("line {}: {}'s {} is '{}', {}".format(
                    at, entry.effect, key,
                    "|".join(__shown(part) for part in value), fault))
            else:
                settings[key] = value
            continue

        # A hue is the one setting the user has an outside source for, and every
        # colour picker gives it in degrees, so those are taken and turned into the
        # fraction the effect wants
        if kind == "angle":
            turn = __degrees(value)
            if turn is not None:
                value = turn

        fault = __value_fault(kind, value)
        if fault is not None:
            problems.append("line {}: {}'s {} is {}, {}".format(
                at, entry.effect, key, __shown(value), fault))
            continue

        # Each effect gets the type it was written for: a count as an integer, which
        # several of them require, and a boolean however the user chose to spell it
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


def __build_effect(entry, count, problems):
    """The effect an entry asks for, or None if it could not be made."""
    known = EFFECTS.get(entry.effect)
    if known is None:
        # An entry that named none at all has already been reported as such, and
        # saying the missing name is not an effect only shows the reader an internal
        if entry.effect in SCREEN_EFFECTS:
            problems.append("line {}: {} plays on a screen, such as 'screenA: {} "
                            "file=anim.gif'".format(entry.line, entry.effect, entry.effect))
        elif entry.effect is not None:
            problems.append("line {}: '{}' is not an effect".format(entry.line, entry.effect))
        return None, None, None

    cls, kind, how, taken = known
    settings = __check_settings(entry, taken, problems)

    # A wave spans the group unless told otherwise. Being called with a position is
    # not the same as spreading over one: binary_counter is handed a bit, not a share
    if how == "position" and "length" in taken and "length" not in settings:
        settings["length"] = count

    try:
        return cls(**settings), kind, how
    except TypeError as e:
        problems.append("line {}: {} does not take those settings, {}".format(
            entry.line, entry.effect, e))
    # An effect may reject a value with anything it likes. Naming the types it is
    # known to use would reopen this the next time one raises something new
    except Exception as e:      # noqa: BLE001
        problems.append("line {}: {} cannot use those settings, {}".format(
            entry.line, entry.effect, e))

    return None, None, None


def __callables(effect, how, count, entry, problems):
    """One callable per channel, in the order the entry wrote them."""
    if how is None:
        return [effect] * count
    if how == "position":
        return [effect(index) for index in range(count)]

    # Fewer outputs than the effect drives takes the first of them, as calling only
    # some of its methods would. More leaves outputs nothing could ever light
    if count > len(how):
        problems.append("line {}: {} drives {} outputs, {} named".format(
            entry.line, entry.effect, len(how), count))
    return [getattr(effect, how[index])() if index < len(how) else None
            for index in range(count)]


def __curve(curve, seconds):
    """One curve's setting as a player takes it, the file having written one part or two."""
    return curve(*seconds) if isinstance(seconds, tuple) else curve(seconds)


def __assemble(entries, slots, effects, levels, colours, curves, claimed, problems):
    """
    Fill one scene's arrays from its entries, or the always-on set's from those
    before any heading. Claims span every call, since scenes take turns with the
    same hardware but different channels on it would fight. Returns the slots
    driven here, which is what a switch must know to clear, and the effects built,
    which is what a restart begins again.
    """
    driven = set()
    sources = []

    for entry in entries:
        count = len(entry.channels)

        # Named together and before the effect is built, so a range reaching past the
        # board answers once rather than per output, and a line with two mistakes
        # reports both instead of costing an eject each
        missing = [channel.name for channel in entry.channels if channel.name not in slots]
        if missing:
            problems.append("line {}: this board has no {}".format(
                entry.line, ", ".join(missing)))

        for key in SCREEN_SETTINGS:
            if any(getattr(channel, key) is not None for channel in entry.channels):
                problems.append("line {}: {} is for a screen, an output takes {}".format(
                    entry.line, key, ", ".join(OUTPUT_SETTINGS)))

        effect, kind, how = __build_effect(entry, count, problems)
        if effect is None:
            continue

        # Position is the channel's place as written, so a rejected channel does not
        # shift the phase of the ones after it
        wanted = []
        for position, channel in enumerate(entry.channels):
            slot = slots.get(channel.name)
            if slot is None:
                continue
            if kind == "colour" and slot[0] not in CHROMATIC:
                # A mono channel cannot show a colour, but a colour channel can play a
                # mono effect: the player draws it in the channel's own tint
                problems.append("line {}: {} brings its own colour, which {} cannot show".format(
                    entry.line, entry.effect, channel.name))
            else:
                wanted.append((channel, slot[0], slot[1], position))

        if not wanted:
            continue

        sources.append(effect)

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
            driven.add((where, index))
            if channel.level is not None:
                levels[where][index] = channel.level
            if channel.ease is not None:
                curves[where][index] = __curve(ease, channel.ease)
            elif channel.fade is not None:
                curves[where][index] = __curve(fade, channel.fade)
            if channel.colour is not None and where in colours:
                colours[where][index] = channel.colour

    return driven, sources


def __apply_scene(players, shows, scene):
    """
    Point the players and shows at one scene. Its arrays already carry the always-on
    entries and turn off what other scenes drive, so this is an exchange of lists the
    players read on their next tick.

    A scene told to restart begins its own content again, the always-on entries
    carrying on: their effects are built in their own pass and so are never among a
    scene's, and an effect that keeps no offset has nothing to begin again.
    """
    if scene.restart:
        for source in scene.sources:
            begin = getattr(source, "reset", None)
            if begin is not None:
                begin()

    for player in players:
        player.effects = scene.effects[player.kind]
        player.levels = scene.levels[player.kind]
        player.curves = scene.curves[player.kind]
        if player.kind in scene.colours:
            player.colours = scene.colours[player.kind]

    # A screen another scene was using goes dark unless this one, or an always-on
    # entry, is still on it: the glass keeps its frame, the light says it is over
    # One show at a time may have a panel, and a screen may be named by an always-on
    # entry and by a scene both. The scene's own takes it while the scene shows, as a
    # scene takes an always-on output, and the always-on one has it the rest of the time
    holding = {}
    for show in shows:
        if show.scene is None:
            holding.setdefault(show.screen, show)
    for show in shows:
        if show.scene == scene.key:
            holding[show.screen] = show

    live = set(holding.values())
    lit = set(holding)

    for show in shows:
        show.live = show in live
        if show.live:
            if scene.restart and show.scene == scene.key:
                show.restart()
            show.resume()
        elif show.screen in lit:
            # Another show has this panel, so it stays lit and this one just waits
            show.pause()
        else:
            show.rest()


def load(text, fx, maker=None):
    """
    Read the effects file. Returns the board it plays on, the players it describes,
    the shows its screen entries play, the sounds its audio entries name, its
    scenes in heading order, the settings its board entries carry, and any
    problems. Without headings there are no scenes and everything plays at once,
    which is the file as it has always been.

    `fx` is a board or something that makes one, a board class being the usual thing.
    Where it makes one, the board is built here rather than by the caller, once the
    file's own board entry has been read, so what the file declares reaches the
    constructor. A board built already is used as it is, unless `maker` says what
    would build its replacement: then a board entry that no longer matches the
    running hardware shuts the board down and a fresh one is built, as a restart
    would. Without a maker the change is reported instead.
    """
    entries, problems = parse(text)
    has_strips = __has_strips(fx)

    # Board entries are settings rather than effects, a heading begins a scene, and
    # a screen name routes its whole entry to the screens, so a mistyped one is
    # answered about screens and not about outputs the board never had
    board = {}
    scenes = []
    known = {}
    grouped = {None: []}
    screen_entries = []
    audio_entries = []
    args_line = None

    for entry in entries:
        if entry.heading is not None:
            name = entry.heading["name"]
            already = known.get(name.lower())
            if already is None:
                scene = Scene(name, entry.line, entry.heading["hold"],
                              entry.heading["restart"])
                scene.advised = entry.heading["advised"]
                known[scene.key] = scene
                scenes.append(scene)
                grouped[scene.key] = []
            else:
                problems.append("line {}: [{}] was already begun on line {}".format(
                    entry.line, name, already.line))
            continue

        if len(entry.channels) == 1 and entry.channels[0].name == BOARD:
            if entry.scene is not None:
                problems.append("line {}: the board entry is about the board, so it "
                                "sits outside every scene".format(entry.line))
            given = __check_board(entry, has_strips, problems)
            # A board entry may be written more than once, so where the arguments were
            # written is kept rather than checked here: the program may name a later line
            if "args" in given:
                args_line = entry.lines.get("args", entry.line)
            board.update(given)
            continue

        sounding = [channel for channel in entry.channels if channel.name == AUDIO]
        if sounding and len(sounding) != len(entry.channels):
            problems.append("line {}: outputs and audio cannot share an entry".format(
                entry.line))
            continue
        if sounding:
            audio_entries.append(entry)
            continue

        named = [channel for channel in entry.channels if channel.name.startswith("screen")]
        if named and len(named) != len(entry.channels):
            problems.append("line {}: outputs and screens cannot share an entry".format(
                entry.line))
        elif named:
            screen_entries.append(entry)
        else:
            grouped[entry.scene].append(entry)

    # Arguments with nothing to receive them, which nothing else would report
    if args_line is not None and not board.get("program"):
        problems.append("line {}: args needs a program to give them to. Write it like "
                        "'board: program=demo.py args=first|second'".format(args_line))

    # Rotation is by time and time alone for now, so a scene without one stops it
    if len(scenes) > 1:
        for scene in scenes:
            if scene.hold is None and not scene.advised:
                problems.append("line {}: [{}] names no time, so the scenes after it "
                                "will not show. Write it like '[{}: 30s]'".format(
                                    scene.line, scene.name, scene.name))

    # A changed board entry gets a fresh board, as a restart would: the running one
    # is shut down and the build below makes its replacement from the file's own
    # declarations. The strip record goes first, so nothing here still holds a strip
    # when shutdown() collects them, and the screens die with their ports
    if maker is not None and not callable(fx) and __hardware_changed(fx, board):
        __STRIPS.clear()
        __SCREENS.clear()
        fx.shutdown()
        fx = maker

    # The board comes up here, now that its own entry has been read: a strip's length
    # is declared at construction, and this is the first point it is known
    fx = __board(fx, board, problems)
    mono, colour = channels(fx)

    # The strips the file asked for, taken before its channel names are resolved: a
    # bare strip name stands for a run whose length only the board entry knows
    built, failed = strips(fx, board, problems)
    __resolve_strips(entries, board, has_strips, problems, failed)

    # Every kind of channel this board offers, as the names each player's slots take.
    # A strip is one kind per connector, since each is a player writing to its own
    names = [("mono", [name for name, _ in mono]), ("colour", [name for name, _ in colour])]

    # LEDs the board builds past the length a strip was asked for, to catch a frame
    # torn by a flash write before it overruns onto a strip's last real LED. Their
    # names carry a space, which nothing a file can write ever does, so they hold a
    # slot each without being reachable
    spare = getattr(type(fx), "STRIP_FLUSH_LEDS", 0)
    for kind, _, count in built:
        holds = ["{}{}".format(kind, number) for number in range(1, count + 1)]
        holds += ["{} flush {}".format(kind, number) for number in range(spare)]
        names.append((kind, holds))

    slots = {}
    for kind, holds in names:
        for index, name in enumerate(holds):
            slots[name] = (kind, index)

    effects = {kind: [None] * len(holds) for kind, holds in names}
    levels = {kind: [1.0] * len(holds) for kind, holds in names}
    curves = {kind: [None] * len(holds) for kind, holds in names}
    colours = {kind: [(255, 255, 255)] * len(holds) for kind, holds in names
               if kind in CHROMATIC}
    claimed = {}

    always, _ = __assemble(grouped[None], slots, effects, levels, colours, curves,
                           claimed, problems)

    union = set()
    for scene in scenes:
        scene.effects = {kind: list(held) for kind, held in effects.items()}
        scene.levels = {kind: list(held) for kind, held in levels.items()}
        scene.colours = {kind: list(held) for kind, held in colours.items()}
        scene.curves = {kind: list(held) for kind, held in curves.items()}
        scene.driven, scene.sources = __assemble(grouped[scene.key], slots, scene.effects,
                                                 scene.levels, scene.colours, scene.curves,
                                                 claimed, problems)
        union |= scene.driven

    # A slot any scene drives goes dark in the scenes that do not drive it, and dark
    # is an effect: None means "not driven", which keeps whatever was showing
    off = NoneFX()
    for scene in scenes:
        for kind, index in union - scene.driven - always:
            scene.effects[kind][index] = off

    live_effects = scenes[0].effects if scenes else effects
    live_levels = scenes[0].levels if scenes else levels
    live_colours = scenes[0].colours if scenes else colours
    live_curves = scenes[0].curves if scenes else curves

    # A player exists if anything in any scene wants it, or a scene reached only by
    # rotation would arrive with nowhere to play
    players = []
    every = [effects] + [scene.effects for scene in scenes]

    def wanted(kind):
        return any(item is not None for one in every for item in one[kind])

    def filled(player, kind):
        # The kind is kept on the player because a scene switch has to know which
        # arrays to hand it, and two strips are one class told apart only by this
        player.kind = kind
        player.effects = live_effects[kind]
        player.levels = live_levels[kind]
        player.curves = live_curves[kind]
        if kind in live_colours:
            player.colours = live_colours[kind]
        return player

    if wanted("mono"):
        players.append(filled(MonoPlayer([led for _, led in mono]), "mono"))

    if wanted("colour"):
        players.append(filled(ColourPlayer([led for _, led in colour]), "colour"))

    for kind, strip, count in built:
        if wanted(kind):
            players.append(filled(StripPlayer(strip, num_leds=count + spare), kind))

    # The spare LEDs are driven dark rather than left alone, in every scene: an
    # effect of None is a slot nothing writes, which is what would let a torn frame
    # stay lit there. Set once the players are decided, so a strip nothing plays on
    # is still a strip with no player
    for kind, _, count in built:
        for index in range(count, count + spare):
            effects[kind][index] = off
            for scene in scenes:
                scene.effects[kind][index] = off

    # One timer drives them all, each ticking the next, so every channel steps together
    for first, second in zip(players, players[1:]):
        first.pair(second)

    # A program takes the whole board and sets up its own screens, so building these
    # before it runs resets a panel and decodes its content into heap for something
    # about to be replaced. They are built when it gives the board back instead, which
    # is where a program that is missing, that stops, or that returns all end up
    if board.get("program"):
        __PENDING_SHOWS[:] = [(screen_entries, fx, board)]
        shows = __build_shows(screen_entries, fx, board, problems, build=False)
    else:
        __PENDING_SHOWS[:] = []
        shows = __build_shows(screen_entries, fx, board, problems)

    # Opening a file is all a sound costs, so a named program defers nothing here:
    # its handle waits, opened while the board is sure to hold the drive
    sounds = __build_sounds(audio_entries, fx, problems)

    # Found in the order the work happens, which is every line the parser read and
    # then every entry the loader built, so a reader gets them in the file's order
    return fx, players, shows, sounds, scenes, board, __in_line_order(problems)
