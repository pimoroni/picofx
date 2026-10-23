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
from picofx.colour import BLUE, RED, WHITE
from picofx.mono import NoneFX

from .vocabulary import (AUDIO, AUDIO_EFFECTS, BOARD, BOARD_SETTINGS, __BRIGHTNESS, CHANNEL_KINDS,
                         COLOURS, COMPONENTS, CONFIG_PATH, CURVES, EFFECTS, ERRORS_PATH, HUB,
                         HUB_POSITIONS, MOUNT_DIR, __ORDER, OUTPUT_SETTINGS, PAIRED_SETTINGS,
                         SCREEN_EFFECTS, SCREEN_SETTINGS, SCREEN_SIZES, SETTINGS, TILING)
from .hardware import (__after, __board, __BOARD_BRIGHTNESS, __BOARD_HUB, __BOARD_SCREENS,
                       __BOARD_STRIPS, __BOARD_TAKES, __channel_shown, channels, __hardware_changed,
                       __HUB, __hub_declared, __hub_example, __hub_port, __hub_shown, __learn_board,
                       __port_classes, __resolve_strips, __screen_kinds, __screen_port,
                       __screen_shown, __SCREENS, __strip_of, __strip_shown, __STRIPS, strips)
from .parser import (Channel, __expand, __in_line_order, __number, parse, __shown, __unquoted,
                     __value_fault)

# Where a problem found after the file was read is written, which run() sets to
# whatever it was told to report to. A drawing is the one thing that can stop long
# after load, so it is the only writer of this
__REPORTING_TO = [ERRORS_PATH]

# Short of full, which is uncomfortable on an indicator at arm's length and buys no
# legibility across a room
INDICATOR_LEVEL = 0.75

# One length for all of them, so the count is the only thing carrying the scale
FLASH_MS = 150

# What the indicators say where a file cannot, as (colour, level, times, period). A
# board carries indicator LEDs shadowing its outputs, or one LED of its own where it
# has no outputs, so colour reaches a user whatever they have wired in and is what
# they read first; the count reaches anyone whose indicators are removed. Both climb
# with how much trouble the reader is in, and red lands on the one condition with
# nothing else to say it, errors.txt speaking for the blue and the drive itself for
# the white. Never red against green, the pair most often confused by eye.
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

# The longest a sound paused for the board joining the bus is given to fade out of the
# player's ring before the player shuts down, which a board may make a few hundred
# milliseconds long
SOUND_FADE_MS = 400

# How often a single indicator flashes while the computer is copying, lit for one step at
# the end of each period, since a spot with nowhere to travel would hold it steady
TRANSFER_PERIOD_MS = 840

# What one pass of the spot costs as the drive changes hands, per output. Half the
# transfer's step: this says something happened rather than that it is still going
HANDOVER_STEP_MS = TRANSFER_STEP_MS // 2


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
    def __init__(self, screen, player, channel, scene=None, places=None, hub=None, line=0):
        import picovector

        self.screen = screen
        self.player = player
        self.scene = scene
        # The selector names this show draws on, one for a screen or several on a hub,
        # which is what a scene switch hands over
        self.places = tuple(places) if places else (channel.name,)
        # The hub's one backlight where this show is on a hub, which lights and dims for
        # every position at once, so this show never turns it off itself
        self.hub = hub
        self.line = line
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
        # The brightness the entry asks for, or None for full
        self.backlight = channel.backlight
        self.__lit = False
        self.__redraw = False
        self.__due = False
        # Whether this show has the panel. Only a scene takes it away, so a file
        # without scenes never has to say so
        self.live = True
        # The other show of a pair update_pair refused, which is never tried again, since
        # neither show's sources change
        self.refused_with = None

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

        # Check if the backlight is the hub's, which waits for every position
        if self.hub is not None:
            self.hub.drawn(self.places)
            return

        # on() waits a scan before lighting a dark line, but relights at the level last
        # set, so the entry's own level follows it, full where it gives none
        self.screen.backlight.on()
        self.screen.brightness(1.0 if self.backlight is None else self.backlight)

    def service(self):
        """This show's frame on its own, where nothing else is due beside it."""
        if self.wants():
            self.send()

    def send(self):
        """Stream the frame due, which stage() may have converted ahead."""
        self.__due = False
        self.__redraw = False
        self.screen.update(self.player.image, rotation=self.rotation, mirror=self.mirror,
                           pixel_double=self.pixel_double, offset=self.offset,
                           tile=self.tile, bg_color=self.background)
        self.lit()

    def pause(self):
        self.player.pause()

    def wait(self):
        """Put aside while another show has the panel, which draws over this one's frame
        and may light it to another level."""
        self.player.pause()
        self.__lit = False
        self.__redraw = True

    def resume(self):
        self.player.play()

    def rest(self):
        """Put aside by a scene switch: paused and dark, relighting on return."""
        self.player.pause()
        # A hub's positions share one backlight, which the hub turns off itself
        if self.hub is None:
            self.screen.backlight.off()
        self.__lit = False
        self.__redraw = True

    def restart(self):
        """Back to the first frame, for a scene that begins again on every entry."""
        self.player.to_first()
        self.__redraw = True


class __HubLight:
    """
    A Screen Hub's one backlight, shared by every position. It lights once every panel
    holds a frame, so no panel shows what an earlier run left on it, and stays lit across
    scenes until nothing on the hub is shown at all.
    """
    def __init__(self, panels, sizes, groups):
        self.panels = panels            # Each position's screen, for those that answered
        self.sizes = sizes
        self.groups = groups            # One broadcast group per panel size
        self.value = None
        self.__lit = False
        self.__waiting = set(panels)
        self.__blank = set()

    def drawn(self, places):
        """Note that these positions hold a frame, lighting the hub once all of them do."""
        self.__waiting.difference_update(places)
        if not self.__lit and not self.__waiting:
            self.__lit = True
            self.__apply()

    def ask(self, value):
        """Take the brightness the hub's live entries agreed on, None being full."""
        if value != self.value:
            self.value = value
            if self.__lit:
                self.__apply()

    def show(self, held):
        """Clear the positions nothing holds to black, or go dark where nothing is held."""
        if not held:
            self.off()
            return

        empty = set(self.panels) - set(held)
        cleared = empty - self.__blank
        self.__blank = empty
        if cleared:
            import picovector
            dot = picovector.image(1, 1)
            for size, group in self.groups.items():
                members = [self.panels[place] for place in cleared if self.sizes[place] == size]
                if members:
                    group.subset(*members).update(dot, bg_color=picovector.color.black)
        self.drawn(empty)

    def off(self):
        """Dark until every position holds a frame again."""
        self.__first().backlight.off()
        self.__lit = False
        self.__waiting = set(self.panels)
        self.__blank = set()

    def __first(self):
        return next(iter(self.panels.values()))

    def __apply(self):
        # on() relights at the level last set, so the agreed one follows it, full by default
        self.__first().backlight.on()
        self.__first().brightness(1.0 if self.value is None else self.value)


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


def user_trace(error):
    """
    The traceback of an error raised in a user's own code, less the frames from autofx's
    own files, which are the machinery that ran it and are not the user's to read.
    """
    trace = io.StringIO()
    sys.print_exception(error, trace)
    return "\n".join(line for line in trace.getvalue().rstrip().split("\n")
                     if "autofx/" not in line)


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

    def __init__(self, name, code, canvas, ground, errors, fps=None, paused=False):
        self.image = canvas
        self.__name = name
        self.__code = code
        self.__ground = ground
        self.__errors = errors
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
        # Run the module body and the first frame, raising as the file does
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
        # Keep the last frame and say why, once; the loop around this carries on
        self.__stopped = True
        message = ("the drawing {} stopped, so its screen keeps its last "
                   "frame:\n{}".format(self.__name, user_trace(error)))
        print(message)
        # Where the reader is already looking, while the board holds the volume;
        # exposed, the mount is gone and there is nowhere to write. Appended rather
        # than written, so a drive with no room left keeps the account it has
        try:
            with open(self.__errors, "a") as handle:
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
    and whether it starts again when it ends. A file on the drive is read straight
    from the flash, so it plays through a handover, and the player stands it aside
    while the computer writes. One the computer rewrites goes silent until the next
    reload, since what it reads is no longer that sound.

    The board plays one sound at a time, so the sounds share the player and `live`
    says which of them has it. One put aside by a scene switch remembers where it
    reached and picks up from there on its next turn; one that had already ended
    starts again from the top.
    """
    def __init__(self, wav, handle, loop, scene=None):
        self.wav = wav
        self.handle = handle
        self.loop = loop
        self.scene = scene
        self.live = False
        self.__at = None
        self.__moved = None
        self.__from = 0         # Where the next start picks up, 0 being the top
        self.__gone = False     # Whether the computer changed the file since load
        self.__held = False     # Whether joining the bus stopped it part way through

    def start(self):
        if self.__gone:
            return
        try:
            self.wav.play_wav(self.handle, loop=self.loop, position=self.__from)
        except (OSError, ValueError) as e:
            # Unreadable as a WAV, however it came to be: nothing plays until a
            # reload brings a readable one
            print("the sound could not start, and waits for the next reload:", e)
        self.__from = 0
        self.live = True

    def service(self):
        """
        Watch a playing sound for progress, and start it again where it stalls.
        The player feeds its buffers over a chain of I2S callbacks, and a lost
        callback ends the chain: the state stays playing while nothing sounds.
        A restart from the held position rebuilds the player, and the chain
        with it. Half a second of stillness says stalled; a sound that ended
        reports no position and is left alone.
        """
        if not self.live:
            self.__at = None
            return
        at = self.wav.position()
        now = time.ticks_ms()
        # Check if it has just ended because the computer replaced its file, which the
        # player found as the writes finished
        if at is None and self.__at is not None and self.__file_changed():
            return
        if at is None or at != self.__at:
            self.__at = at
            self.__moved = now
            return
        if time.ticks_diff(now, self.__moved) < 500:
            return
        self.__from = at
        self.__moved = now
        print("the sound stalled, and starts again from where it stopped")
        self.start()

    def set_aside(self):
        """Put aside by a scene switch: silenced, remembering where it reached."""
        if not self.live:
            return
        self.wav.pause()
        # None where the sound had already ended, which is a start from the top
        self.__from = self.wav.position() or 0
        self.live = False

    # The player is shared, so a sound standing aside while the board joins the bus only
    # touches it while the speaker is its own. It stops outright, as the effects do, and
    # resume() picks up where it was
    def pause(self):
        if not self.live:
            return
        # None is a sound that had already ended, which joining the bus leaves ended
        if self.wav.position() is None:
            return
        # Faded out before it stops, a cut mid-waveform clicking
        self.wav.pause()
        deadline = time.ticks_add(time.ticks_ms(), SOUND_FADE_MS)
        while not self.wav.is_paused() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
            time.sleep_ms(5)
        at = self.wav.position()
        self.wav.deinit()
        # None again is a sound that ended during the fade
        if at is not None:
            self.__from = at
            self.__held = True

    def resume(self):
        # The watch starts afresh: the position stood still through the pause
        self.__at = None
        if self.__file_changed():
            return
        if self.__held:
            self.__held = False
            self.start()

    def __file_changed(self):
        # Check if the computer has replaced the file, which leaves the sound silent until
        # the next reload
        changed = getattr(self.handle, "changed", None)
        if self.__gone or changed is None or not changed():
            return False
        self.__gone = True
        if self.live:
            self.wav.stop()
        self.live = False
        self.__held = False
        print("a sound's file changed on the drive, and it waits for the next reload")
        return True

    def restart(self):
        """Back to the top, for a scene that begins again on every entry."""
        self.__from = 0
        if self.live:
            self.start()

    def close(self):
        # Neither half may stop the other, nor whatever is tidying up after this: a
        # player mid-transfer and a handle on a volume the computer has taken are both
        # reached here, and there is nothing left to save either way
        try:
            self.wav.deinit()
        except Exception as e:      # noqa: BLE001
            print("the sound would not stop:", e)
        try:
            self.handle.close()
        except OSError:
            pass


def __degrees(text):
    # A fraction of a turn from 0 to 360 written with 'deg', or None if it is not
    if not isinstance(text, str) or not text.lower().endswith("deg"):
        return None

    number = __number(text[:-3])
    if number is None or not 0.0 <= number <= 360.0:
        return None
    return number / 360.0


def report(problems, path, running=True):
    """
    Write the problems where the user is already looking, or clear the file when
    there are none, so its presence is the message.

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


def __indicators(fx):
    # The LEDs a signal shows on: the outputs, or the board's own LED where it has none
    if fx.outputs:
        return fx.outputs
    rgb = getattr(fx, "rgb", None)
    return [] if rgb is None else [rgb]


def __flashed(fx):
    # The LEDs a flash shows on: the indicators, and the board's own LED beside its outputs too,
    # where mono outputs alone would show the count and not the colour. The board's LED takes
    # no part in the spot, sitting outside the line the outputs make
    lights = __indicators(fx)
    rgb = getattr(fx, "rgb", None)
    return lights if rgb is None or rgb in lights else lights + [rgb]


def indicate(fx, pattern=PROBLEM):
    """
    Flash every indicator together in the pattern's colour, or plain where one shows
    no colour. Nothing an effect does starts like this, so it reads as a signal
    rather than as the show.
    """
    colour, level, times, period_ms = pattern
    red, green, blue = (part * level for part in colour)
    lights = __flashed(fx)

    for _ in range(times):
        for output in lights:
            if isinstance(output, RGBLED):
                output.set_rgb(red, green, blue)
            else:
                output.brightness(level)
        time.sleep_ms(period_ms)

        for output in lights:
            output.off()
        time.sleep_ms(period_ms)


def __play(fx, volume, path, errors, playing, sounding=(), maker=None):
    # Stop what is playing, read the file again, and play what it now says.
    #
    # Takes a board or something that makes one, and hands the board back: the file is
    # what declares a strip, so on the first read there is nothing built yet. `maker`
    # is passed through to load(), which rebuilds the board where its entry changed
    for player in playing:
        player.stop()
    # The players held the strips. A board rebuilt below for a changed entry claims
    # their state machines again, which a strip still referenced would refuse
    playing.clear()

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
        light = __HUB.get("light")
        if light is not None:
            light.off()
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
            fx, players, shows, sounds, scenes, settings, problems = load(text, fx, maker, volume)
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
    if volume is None and __PENDING_SHOWS:
        shows = __pending_shows(problems)

    if volume is None:
        wrote = report(problems, errors, bool(players or shows or sounds))
    else:
        # A shipped document the mount left stale is said here too, errors.txt being
        # where a reader with only the drive in front of them will look
        for name in volume.unhealed():
            problems.append("the FX drive is full, so {} is out of date; delete a "
                            "picture or sound from the drive to let it "
                            "rebuild".format(name))
        wrote = report(problems, errors, bool(players or shows or sounds))

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


def __service_shows(shows, between=None):
    """
    One pass of every screen that has the panel, answering whether one was drawn.

    Two panels on their own ports stream together in about the time one of them
    takes alone, so a frame due on each is sent as a pair. Measured at 58ms
    against 110ms for the two in turn, and 89ms against 155ms with the players
    running. Placement stays per screen, prepare() holding each frame until both
    are ready.

    `between` is asked after each screen where they are drawn one at a time, and
    stops the pass when it answers true, so a press waits out one screen rather
    than all of them. A pair is one stream and cannot be interrupted part way.
    """
    due = [show for show in shows if show.live and show.wants()]

    if len(due) == 2 and due[0].screen.port is not due[1].screen.port \
            and due[0].refused_with is not due[1]:
        from screens import update_pair
        try:
            for show in due:
                show.stage()
            update_pair(due[0].screen, due[1].screen)
            for show in due:
                show.lit()
            return True
        # Screens built too differently to share a stream, or two PSRAM sources the
        # smaller reserve cannot convert together, which update_pair says for itself.
        # A staged frame is still waiting on each, so each is sent rather than lost
        except ValueError as e:
            due[0].refused_with, due[1].refused_with = due[1], due[0]
            print("the screens are being drawn one at a time: {}".format(e))
            for show in due:
                show.send()
            return True

    for show in due:
        show.service()
        if between is not None and between():
            break

    return bool(due)


def __start(players, fx):
    # A paired player is ticked by its partner, so only the head starts a timer.
    #
    # The strip header's rail comes up here as well, where a strip was built: the
    # board leaves it down until asked, and this is when something starts driving it
    if __STRIPS:
        rail = getattr(fx, "enable_rail", None)
        if rail is not None:
            rail()
    if players:
        players[0].start(fps=PLAYER_FPS)


def __resume(players, fx):
    # Start the players again after a pass of the spot, over dark outputs.
    #
    # The spot leaves every output it did not carry at its resting floor, and a
    # player writes only the outputs an effect drives, so one the file never names
    # would keep that floor for good. Darkening first costs the driven outputs one
    # frame, which the players paint over. The outputs only, since clear() would
    # take a strip's player with it
    for output in __indicators(fx):
        output.off()
    __start(players, fx)


def __spot(fx, lit):
    # The indicator at lit at the travelling level, the rest at the resting floor
    colour, floor, spot = TRANSFER
    for index, output in enumerate(__indicators(fx)):
        level = spot if index == lit else floor
        if isinstance(output, RGBLED):
            output.set_rgb(colour[0] * level, colour[1] * level, colour[2] * level)
        else:
            output.brightness(level)


def __handover(fx, to_board):
    # The drive changing hands, said with one pass of the spot a transfer travels.
    #
    # A double press reloads the board exactly as a single press does, so without
    # this nothing on the outputs tells the two apart. Which way the spot runs says
    # which way the drive went, reading the outputs as the line they are: the first
    # sits by the USB connector and the last at the far end, so a pass towards the
    # end is the board taking the drive and one towards the connector is the
    # computer taking it. A transfer travels the first way, into the board, which
    # is the only direction it can mean: the drive reports a write and never a
    # read. Half the transfer's step, so the whole pass is brief
    count = len(__indicators(fx))
    order = range(count) if to_board else range(count - 1, -1, -1)
    for lit in order:
        __spot(fx, lit)
        time.sleep_ms(HANDOVER_STEP_MS)


def __transfer_frame(fx, at):
    # One frame of the wait shown while the computer is copying: a spot travelling the
    # indicators over a resting floor, so a transfer reads as something happening rather
    # than as the board having stopped.
    #
    # Driven from the caller's own loop rather than a player, since the players are
    # stopped for the duration, and stepped from the clock so a frame the transfer
    # delays does not slow the travel down.
    #
    # Nothing is sent to a strip meanwhile. A frame reaches one as a single timed
    # run of bits, and a flash write pauses the transfer sending it partway, which
    # breaks it apart into the wrong colours or into a run that overruns the LEDs
    # declared into one nothing addresses afterwards. Every frame sent is another
    # that can be torn, so the strips are left holding what they have
    lights = __indicators(fx)
    if len(lights) == 1:
        __spot(fx, 0 if at % TRANSFER_PERIOD_MS >= TRANSFER_PERIOD_MS - TRANSFER_STEP_MS else -1)
    elif lights:
        __spot(fx, (at // TRANSFER_STEP_MS) % len(lights))


def __candidates(name):
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


def __read_program(name, problems):
    # The source of a program the file named, or None if there is none to read.
    #
    # Read before the drive is shown, since exposing it unmounts the mount point and a
    # program kept on the drive could not be opened once the computer has it
    found = []
    for candidate in __candidates(name):
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
    # Run what was read, and say so if it stops rather than letting it take the board

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
        # someone with no way to see a console
        problems.append("the program {} stopped, so the effects are running "
                        "instead:\n{}".format(name, user_trace(e)))
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

    # A drawing that stops does so long after this returned its problems, so it writes
    # its own, and this is how it knows where they go
    __REPORTING_TO[0] = errors

    # A board that asks its hardware which of its parts it has does so once, before any is read
    board = fx if isinstance(fx, type) else type(fx)
    if hasattr(board, "detect"):
        board.detect()

    if volume is not None:
        volume.mount(screens=bool(getattr(board, "SCREENS", ())),
                     wireless=getattr(board, "WIRELESS", False))

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
            __apply_scene(players, shows, sounds, scenes[0])
            if scenes[0].hold:
                scene_deadline = time.ticks_add(time.ticks_ms(), int(scenes[0].hold * 1000))
        else:
            __cue_sound(sounds, None)
            __settle_hub(shows)

    if volume is None:
        begin_scenes()
        __start(players, fx)
        return fx, players, shows, sounds, scenes, problems

    # A save landing on effects.txt answers as a single press does, unless the file
    # says reload=manual
    volume.watch(settings.get("reload") != "manual")

    # Enumeration after a bus reset has deadlines the players' ticks would make the board
    # miss, so they stop the moment one arrives, from the USB task itself, and the loop
    # below stands everything aside until the computer has finished
    reset_seen = False

    def quiet():
        nonlocal reset_seen
        reset_seen = True
        for player in players:
            player.stop()

    volume.on_bus_reset(quiet)

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

    # Read while the board still holds the drive, since exposing it takes the mount
    # point away and a program kept there would have nothing left to open
    source = __read_program(program, problems) if program else None

    if drive_up:
        volume.expose()

    if program:
        if source is not None:
            # Nothing here looks at the drive until the program ends, so a save that
            # would reload the file resets the board instead, which then reads it as at
            # power on
            volume.reset_on_save(True)
            try:
                __run_program(program, source, settings.get("args", ()), problems)
            finally:
                volume.reset_on_save(False)

        # The board is the effects' again, so the screen entries put off for the
        # program are built now, before the report, so anything wrong with them is in it
        shows = __pending_shows(problems)

        # Here because the program could not be found or run, or because it finished
        # by itself. Either way the effects take the board back, and anything that
        # went wrong is said where the user is looking
        if volume.exposed():
            volume.withdraw()
        wrote = report(problems, errors, bool(players or shows or sounds))
        if problems:
            indicate(fx, PROBLEM if wrote else UNREPORTED)
        begin_scenes()
        __start(players, fx)            # Never started above, whether the program ran or not
        if drive_up:
            volume.expose()

    paused = False
    sounds_aside = False
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
                __resume(players, fx)

            if event in (volume.HIDDEN, volume.EJECTED, volume.RELOADED):
                if event == volume.HIDDEN:
                    # Before the reload, which darkens everything and would swallow it
                    for player in players:
                        player.stop()
                    __handover(fx, True)
                fx, players, shows, sounds, scenes, settings, problems = __play(
                    fx, volume, path, errors, players, sounds, maker)
                # A program only runs from a start, so a file that now names one restarts
                # the board, which then runs it as it does at power on
                if settings.get("program"):
                    import machine
                    machine.reset()
                paused = False
                sounds_aside = False
                idle_since = None
                volume.watch(settings.get("reload") != "manual")
                if event == volume.RELOADED:
                    # A single press asks to try an edit without putting the drive
                    # away, so it goes back once the file has been read, and before
                    # anything starts, so the lights and the screens come up together
                    # behind it
                    volume.expose()
                begin_scenes()
                __start(players, fx)
                # A frame each as the lights start, so the panels come back with them
                __service_shows(shows)

            # The rotation, standing aside with everything else while a transfer runs
            if scene_deadline is not None and not paused and \
                    time.ticks_diff(time.ticks_ms(), scene_deadline) >= 0:
                scene_at = (scene_at + 1) % len(scenes)
                scene = scenes[scene_at]
                __apply_scene(players, shows, sounds, scene)
                scene_deadline = (time.ticks_add(time.ticks_ms(), int(scene.hold * 1000))
                                  if scene.hold else None)

            # A transfer costs a running effect most of a tenth of a second in one
            # hitch, so the effects stand aside for it and something of the board's
            # own travels the outputs instead of the show lurching through. So they do
            # for enumeration, which a reset seen since the last pass is the start of
            settling = reset_seen or volume.enumerating()
            reset_seen = False
            if volume.busy() or settling:
                idle_since = None
                # The player stands a sound aside for the computer's writes itself, so only
                # joining the bus stops one here
                if settling and not sounds_aside:
                    for sound in sounds:
                        sound.pause()
                    sounds_aside = True
                if not paused:
                    for player in players:
                        player.stop()
                    for show in shows:
                        show.pause()
                    paused = True
            elif paused:
                if idle_since is None:
                    idle_since = time.ticks_ms()
                elif time.ticks_diff(time.ticks_ms(), idle_since) >= TRANSFER_HOLD_MS:
                    # The sound goes first again, its ring filling before the screens'
                    # first frames can hold up its refills
                    for sound in sounds:
                        sound.resume()
                    sounds_aside = False
                    __resume(players, fx)
                    for show in shows:
                        if show.live:
                            show.resume()
                    paused = False

            drew = False
            if paused:
                __transfer_frame(fx, time.ticks_ms())
            else:
                for sound in sounds:
                    sound.service()

                # A frame can cost longer than the double press window, so the
                # button is answered between the screens rather than after them all
                drew = __service_shows(shows, lambda: watch() != volume.IDLE)

            if event == volume.BUSY:
                # A press the computer's writing blocked otherwise looks exactly like
                # one that did nothing. The effects are already standing aside, so
                # every output flashing reads on top of the one that is travelling,
                # and the next frame paints over it
                indicate(fx, BLOCKED)

            # A pass that drew goes straight round, since the next frame may
            # already be due and a wait would then be added to every frame the
            # screens send. Nothing here needs answering sooner than the wait:
            # the lights run from a timer, and a press is latched until it is read
            if not drew:
                time.sleep_ms(interval_ms)
    finally:
        # Darkening the board comes first and nothing fallible stands in front of it.
        # A stop from the REPL arrives as an interrupt and the next one lands wherever
        # this has reached, so a step that waits, such as handing the drive back while
        # a computer is mid-write, would otherwise leave the outputs lit for good.
        # shutdown() releases the screen ports and the header's rail, so neither
        # record of what is running may outlive them, and anything a program put off
        # is never going to be built now
        for player in players:
            player.stop()
        __SCREENS.clear()
        __STRIPS.clear()
        __HUB.clear()
        __PENDING_SHOWS.clear()
        fx.shutdown()

        # Tidying up after it, each on its own, since neither can undo the above
        for sound in sounds:
            try:
                sound.close()
            except Exception as e:      # noqa: BLE001
                print("a sound would not close:", e)
        try:
            if volume.exposed():
                volume.withdraw()
        except Exception as e:      # noqa: BLE001
            print("the drive would not go back to the board:", e)


# Whether the heap is PSRAM, the RP2350's window from 0x11000000, where a drawing gains
# from a canvas in SRAM. id() is an object's address on this port
__HEAP_IN_PSRAM = 0x11000000 <= id(bytearray(16)) < 0x12000000


def __find_image(name, line, problems):
    """
    The file or folder a screen entry names, or None if there is none to play. The
    drive's copy wins, as a program's does, and for the same reason: it is the one
    the reader can see and edit.
    """
    found = []
    for candidate in __candidates(name):
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
    # A graphics file compiled against its own name, or None with the reason said.
    # Compiled while the entries are read, so a file that will not parse is answered
    # at load, and kept as a code object so a restart never goes back to the drive
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
    # The player for a graphics entry: its canvas, its ground, and the file begun
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
                          __REPORTING_TO[0], fps=fps, paused=asleep)
    # Sized and answered as a picture that will not fit is, the two landing in the
    # same file, though only the canvas is this entry's to make smaller
    except MemoryError as e:
        problems.append(__too_big(at, target, "graphics", e))
    # The traceback, since this is the user's own code and a line number is what
    # makes it fixable
    except Exception as e:      # noqa: BLE001
        problems.append("line {}: {} could not start:\n{}".format(at, target, user_trace(e)))
    return None


def __place_canvases(shows):
    # Move each drawing to a canvas in SRAM while one fits, the largest first, where the
    # heap is PSRAM, since a drawing clears and paints there in a fraction of the time.
    #
    # Run once every panel of the file holds its workspace, as canvases and workspaces
    # share one region and a workspace claimed after a canvas could find no room. The
    # last file's canvases are released first, all together, nothing else holding them.
    # A drawing keeps the frame its setup drew, copied across
    if not __HEAP_IN_PSRAM:
        return

    import picovector
    import spidisplay

    spidisplay.release_buffers()

    drawings = [show.player for show in shows if isinstance(show.player, __Graphics)]
    # Sizes paired with positions, so the sort compares numbers and never a player, and
    # of two the same size the one earlier in the file comes first
    order = sorted(((player.image.width * player.image.height, -index)
                    for index, player in enumerate(drawings)), reverse=True)

    for pixels, negated in order:
        player = drawings[-negated]
        width, height = player.image.width, player.image.height
        try:
            buffer = spidisplay.buffer(pixels * spidisplay.PIXEL_BYTES)
        # Left in PSRAM, where it already draws
        except ValueError:
            continue
        # The bytes themselves, as a blit blends and is a few levels off in places
        buffer[:] = memoryview(player.image)
        player.image = picovector.image(width, height, buffer)


def __wants_full_size(entries, board):
    """
    Whether the file's screens reserve for converting a full-size image each, which
    costs one screen about a third of its speed. Where the heap is PSRAM it is taken
    only where some scene streams two screens the smaller reserve cannot convert in
    time, either turned a quarter or both full colour, and never beside a drawing,
    which takes the smaller reserve so its canvas fits in SRAM (__place_canvases()).
    An animation converts fast from its palette, a sequence's frames count as full
    colour, and a picture is sent once.

    Read from the file rather than from what a scene happens to show: a pair shares
    out one reservation and both screens have to agree on it, so it cannot follow
    the content.
    """
    kinds = __screen_kinds()
    named = {name for name in kinds if board.get(name) and board.get(name) != HUB}
    on_screens = [entry for entry in entries
                  if entry.channels and entry.channels[0].name in kinds]
    named.update(entry.channels[0].name for entry in on_screens)
    if len(named) < 2:
        return False

    # A heap in SRAM keeps the reserve two screens have always taken
    if not __HEAP_IN_PSRAM:
        return True
    if any(entry.effect == "graphics" for entry in on_screens):
        return False

    # What each scene streams on each screen, its own entries over the always-on ones
    streaming = [entry for entry in on_screens if entry.effect in ("gif", "sequence")]
    always = {entry.channels[0].name: entry for entry in streaming if entry.scene is None}
    for scene in {entry.scene for entry in streaming} - {None} or {None}:
        shown = dict(always)
        shown.update((entry.channels[0].name, entry) for entry in streaming
                     if entry.scene == scene)
        if len(shown) < 2:
            continue
        if any((entry.channels[0].rotation or 0) in (90, 270) for entry in shown.values()):
            return True
        if all(entry.effect == "sequence" for entry in shown.values()):
            return True
    return False


def __screen_on(fx, name, line, problems, size, full_size=False):
    # The panel a selector name reaches, built once and kept: construction resets the
    # glass, so a screen is only ever constructed the first time it is asked for, at
    # the board entry's size for it or 2.8 unsaid, size being unreadable from a panel
    known = __SCREENS.get(name)
    if known is not None:
        screen, built_size = known
        if size is not None and size != built_size:
            problems.append("{} is already running as a {} screen, so its new size "
                            "needs the board turning off and on".format(
                                __screen_shown(name), built_size))
        return screen

    SPCE, SPCEPort = __port_classes(fx)

    attr, port_name = __screen_port(name)
    port = getattr(fx, attr)
    shown = __screen_shown(name)

    if port.mode is None:
        # The port was never declared, so it becomes a screen port here: the same
        # construction a program would make, made because the file asked for it
        pins = getattr(type(fx), attr.upper() + "_PINS")
        port = SPCEPort(port_name, SPCE.SCREEN, pins)
        setattr(fx, attr, port)
    elif port.mode != SPCE.SCREEN:
        problems.append("line {}: SP/CE {} is set up for something else, so {} cannot "
                        "show anything".format(line, port_name, shown))
        return None

    if size is None:
        size = "2.8"

    # Read here rather than at the top of the file, which also runs on a board with no
    # screens module to import
    from screens import SCREEN_TYPES, Reserve

    try:
        screen = SCREEN_TYPES[size](
            port, reserve=Reserve.FULL_SIZE_IMAGES if full_size
            else Reserve.CANVAS_SPACE)
    except Exception as e:      # noqa: BLE001
        problems.append("line {}: {} could not start: {}".format(line, shown, e))
        return None

    __SCREENS[name] = (screen, size)
    return screen


def __screen_entry_fits(entry, fx, hub, board, problems):
    # Whether an entry names one screen this board has, declared with its size
    name = entry.channels[0].name

    if len(entry.channels) > 1:
        problems.append("line {}: name one screen per entry".format(entry.line))
        return False

    # The hub has both connectors, one for its panels and one for their selects
    port = __screen_port(name)
    if hub is not None and port is not None:
        if name == hub:
            problems.append("line {}: {} is a Screen Hub, so name its panels hubA to "
                            "hub{}".format(entry.line, __screen_shown(name),
                                           HUB_POSITIONS[-1].upper()))
        else:
            problems.append("line {}: SP/CE {} carries the hub's selects, so {} has no "
                            "screen".format(entry.line, port[1], __screen_shown(name)))
        return False

    if port is None or getattr(fx, port[0], None) is None:
        offered = [shown for _kind, prop, shown in __BOARD_SCREENS
                   if getattr(fx, prop, None) is not None]
        if offered:
            problems.append("line {}: this board has no {}, it has {}".format(
                entry.line, __screen_shown(name), " and ".join(offered)))
        else:
            problems.append("line {}: this board has no screens".format(entry.line))
        return False

    # A panel cannot say what size it is, and driven as the wrong one it shows nonsense
    if board.get(name) is None:
        problems.append("line {}: {} needs its size. Write it like 'board: {}=2.8'".format(
            entry.line, __screen_shown(name), __screen_shown(name)))
        return False

    return True


def __hub_entry_fits(entry, places, hub, board, problems):
    # Whether an entry's hub positions are on a declared hub, sized, and all one size
    shown = __hub_shown(places)

    if hub is None:
        if not __BOARD_HUB[0]:
            problems.append("line {}: this board cannot carry a Screen Hub, so it has no "
                            "{}".format(entry.line, shown))
        else:
            problems.append("line {}: {} is on a Screen Hub, so the board entry needs one. "
                            "Write it like {}".format(entry.line, shown, __hub_example()))
        return False

    missing = [place for place in places if place not in board]
    if missing:
        problems.append("line {}: {} needs its size. Write it like 'board: {}=2.8'".format(
            entry.line, __hub_shown(missing), __hub_shown(missing)))
        return False

    # One stream carries one panel size, so positions of two sizes are two entries
    sizes = [size for size in SCREEN_SIZES if any(board[place] == size for place in places)]
    if len(sizes) > 1:
        split = [__hub_shown([place for place in places if board[place] == size])
                 for size in sizes]
        problems.append("line {}: {} mixes {} panels, which cannot share one stream, so "
                        "write them as two entries, {}".format(
                            entry.line, shown, " and ".join(sizes), " and ".join(split)))
        return False

    return True


def __hub_panel(fx, place, size, problems):
    # The panel at one hub position, built once and kept, or None where none answered
    known = __SCREENS.get(place)
    if known is not None:
        return known[0]

    from screens import SCREEN_TYPES

    shown = __hub_shown([place])
    try:
        port = getattr(fx.hub, place[len(HUB):])
        screen = SCREEN_TYPES[size](port)
    # A position with no panel refuses a screen, and claims nothing in doing so
    except ValueError:
        problems.append("{} is on the board entry but no panel answered there. Check it is "
                        "seated, or take it off the board entry".format(shown))
        return None
    except Exception as e:      # noqa: BLE001
        problems.append("{} could not start: {}".format(shown, e))
        return None

    __SCREENS[place] = (screen, size)
    return screen


def __hub_stream(fx, places, board, line, problems):
    # The stream an entry's positions play through: a subset of the group for their panel
    # size. Every declared position is built the first time the hub is asked for, one
    # group per size, so the hub's light knows every panel it waits on
    if not __HUB:
        problems.append("line {}: the board was not set up with the Screen Hub".format(line))
        return None

    groups = __HUB["groups"]
    if not groups:
        from screens import ScreenGroup
        sizes = __HUB["sizes"]
        for size in SCREEN_SIZES:
            fitted = sorted(place for place in sizes if sizes[place] == size)
            panels = [__hub_panel(fx, place, size, problems) for place in fitted]
            panels = [panel for panel in panels if panel is not None]
            if not panels:
                continue
            try:
                groups[size] = ScreenGroup(*panels)
            except Exception as e:      # noqa: BLE001
                problems.append("the hub's {} panels could not be driven together: "
                                "{}".format(size, e))
        built = {place: __SCREENS[place][0] for place in sizes if place in __SCREENS}
        if built:
            __HUB["light"] = __HubLight(built, sizes, groups)

    group = groups.get(board[places[0]])
    members = [__SCREENS[place][0] for place in places if place in __SCREENS]
    if group is None or not members:
        return None
    return group.subset(*members)


def __agree_hub_backlight(shows, problems):
    # Report hub entries playing at once that ask for different backlights
    asking = sorted((show for show in shows if show.hub is not None and
                     show.backlight is not None), key=lambda show: show.line)
    scenes = {show.scene for show in shows if show.hub is not None} - {None}

    said = set()
    for scene in scenes or {None}:
        # The always-on entries play in every scene, beside the scene's own
        together = [show for show in asking if show.scene in (None, scene)]
        for show in together[1:]:
            if show.backlight != together[0].backlight and show.line not in said:
                said.add(show.line)
                # A percentage, since single precision shows 60% back as 0.59999996
                problems.append("line {}: the hub's panels share one backlight, so {} takes "
                                "the {}% from line {}".format(
                                    show.line, __hub_shown(show.places),
                                    int(together[0].backlight * 100 + 0.5), together[0].line))


def __settle_hub(shows):
    """
    Give the hub's light the shows now live on it: the backlight the first of them asks
    for, positions none of them hold cleared to black, and dark where none is live.
    """
    light = __HUB.get("light")
    if light is None:
        return

    live = sorted((show for show in shows if show.hub is not None and show.live),
                  key=lambda show: show.line)
    held = set()
    for show in live:
        held.update(show.places)

    asking = [show.backlight for show in live if show.backlight is not None]
    light.ask(asking[0] if asking else None)
    light.show(held)


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


def __in_kilobytes(count):
    # Kilobytes, rounded up, matching how picovector reports a GIF's own limit: the
    # two messages can land in the same file and comparing them should need no sums
    return "{}KB".format((count + 1023) // 1024)


def __asked_for(error):
    # The bytes an allocation wanted, from a MemoryError that says so
    for word in reversed(str(error).replace(",", " ").split()):
        if word.isdigit():
            return int(word)
    return 0


def __too_big(at, target, effect, error):
    # Why a picture would not fit, and what to do about it.
    #
    # A player already reports the sizes and says an animation is stored whole, so where
    # it has, only what this file adds is written: another screen draws on the same
    # memory, which is what makes one picture play and two fail
    said = str(error).strip()
    if "was free" in said:
        # The player has sized it up and said why an animation wants so much
        head = said[:-1] if said.endswith(".") else said
        join = ", and both screens share that memory."
    elif "allocation failed" in said:
        import gc
        gc.collect()
        wanted = __asked_for(error)
        spare = gc.mem_free()
        if not wanted:
            room = "did not fit in the {} free".format(__in_kilobytes(spare))
        elif wanted > spare:
            room = "needs {} and {} was free".format(
                __in_kilobytes(wanted), __in_kilobytes(spare))
        else:
            # More free than was asked for, so the total was never the problem: what
            # was left is in pieces smaller than the one piece a picture needs
            room = ("needs {} in one piece and the {} free is in smaller "
                    "pieces".format(__in_kilobytes(wanted), __in_kilobytes(spare)))
        head = "{} {}".format(target, room)
        join = ". Both screens share that memory."
    else:
        # picovector says by how much a GIF misses its own limit and what to do about
        # it, which is a fixed ceiling rather than a shortage: nothing to add but the
        # file, so its own "cannot load GIF" opening comes off
        if said.startswith("cannot load ") and ": " in said:
            said = said.split(": ", 1)[1]
        return "line {}: {}: {}".format(at, target, said)

    if effect in ("gif", "sequence"):
        advice = ("Try fewer frames, or frames half the size with pixel_double=true, "
                  "which costs a quarter as much.")
    elif effect == "graphics":
        # A drawing's canvas is the entry's to size, where a picture's is the file's
        advice = ("Try a smaller canvas with width= and height=, or pixel_double=true, "
                  "which halves both.")
    else:
        advice = "Try a smaller picture."
    return "line {}: {}{} {}".format(at, head, join, advice)


def __build_shows(entries, fx, board, problems, build=True):
    """
    A show per screen entry: the panel it names and the player feeding it.

    Without `build` the entries are checked and nothing is made, which is what a file
    naming a program wants: its screen entries are answered when it is read, and the
    panels and players wait until the program gives the board back.
    """
    shows = []
    built = set()
    full_size = __wants_full_size(entries, board)

    hub = __hub_port(board)

    for entry in entries:
        channel = entry.channels[0]
        name = channel.name
        places = [one.name for one in entry.channels]
        on_hub = name.startswith(HUB)

        if on_hub != all(place.startswith(HUB) for place in places):
            problems.append("line {}: a hub's positions and a screen cannot share an "
                            "entry".format(entry.line))
            continue

        # A hub and a screen both played on have been refused together, and said once
        if (HUB if on_hub else name) in board.get(__REFUSED, ()):
            continue

        if on_hub:
            if not __hub_entry_fits(entry, places, hub, board, problems):
                continue
        elif not __screen_entry_fits(entry, fx, hub, board, problems):
            continue

        # Named twice in one scene is already reported as a repeat, so the later
        # entry only skips; the same screen in two scenes takes turns
        if any((entry.scene, place) in built for place in places):
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

        if on_hub:
            screen = __hub_stream(fx, places, board, entry.line, problems)
        else:
            screen = __screen_on(fx, name, entry.line, problems, board.get(name),
                                 full_size)
        if screen is None:
            continue

        light = __HUB.get("light") if on_hub else None

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
            built.update((entry.scene, place) for place in places)
            shows.append(ScreenShow(screen, player, channel, entry.scene, places, light,
                                    entry.line))
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
        except MemoryError as e:
            problems.append(__too_big(at, target, entry.effect, e))
            continue
        except Exception as e:      # noqa: BLE001
            problems.append("line {}: {} could not be played: {}".format(at, target, e))
            continue

        built.update((entry.scene, place) for place in places)
        shows.append(ScreenShow(screen, player, channel, entry.scene, places, light,
                                entry.line))

    # A screen the file no longer names keeps its last frame but goes dark, since
    # nothing is left to say anything on it. A check has built nothing, so it has
    # nothing to say about which screens are still wanted. A hub's positions share
    # one backlight, which the hub's light answers for
    if build:
        __place_canvases(shows)

        names = {used for _, used in built}
        for name, (screen, _) in __SCREENS.items():
            if name not in names and not name.startswith(HUB):
                screen.backlight.off()
        __agree_hub_backlight(shows, problems)

    return shows


def __open_sound(path, stream):
    # A handle the player can read for the whole run. The drive's mount ends whenever
    # a computer takes the drive, so a file there is read from the flash, or held in
    # memory where the drive cannot find it that way. The board never gives up its
    # own filesystem, so a file there is read as it plays
    if path.startswith(MOUNT_DIR + "/"):
        handle = stream(path[len(MOUNT_DIR) + 1:]) if stream is not None else None
        if handle is not None:
            return handle
        with open(path, "rb") as source:
            return io.BytesIO(source.read())
    return open(path, "rb")


def __build_sounds(entries, fx, problems, volume=None):
    """
    A sound per audio entry: one before any heading playing throughout, and one per
    scene taking the speaker while its scene shows. The file is found here, while
    the board holds the drive, which is what lets it stream on after a computer
    takes the volume.
    """
    sounds = []
    stream = volume.stream if volume is not None else None
    taken = set()
    # A board without audio raises from the property, naming the setting to change
    try:
        wav = fx.wav
    except (AttributeError, RuntimeError):
        wav = None

    for entry in entries:
        if wav is None:
            problems.append("line {}: this board has no audio".format(entry.line))
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

        # One sound at a time is the hardware, so a scene carries one and so does the
        # part before any heading. A second in the same place has already been
        # answered by the parser as a repeated selector, so it only skips here
        if entry.scene in taken:
            continue

        at = entry.lines.get("file", entry.line)
        path = __find_image(target, at, problems)
        if path is None:
            continue

        try:
            handle = __open_sound(path, stream)
        except OSError as e:
            problems.append("line {}: {} could not be opened: {}".format(at, target, e))
            continue
        except MemoryError:
            problems.append("line {}: {} is too large to load. A sound has to fit "
                            "in memory beside everything else that is "
                            "playing.".format(at, target))
            continue

        taken.add(entry.scene)
        sounds.append(Sound(wav, handle, bool(settings.get("loop", False)), entry.scene))

    return sounds


def __check_board(entry, has_strips, problems, lines):
    """
    The board settings the entry carries, with anything it cannot use dropped. A
    board entry names no effect, so nothing else would ever look at these: a typo in
    'drive' or 'program' would leave a board acting as though the line were absent.

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
                named, prefix = __expand(part, prefix, at, problems)
                places.extend(named)
            text = value if isinstance(value, str) else __shown(value)
            if text not in SCREEN_SIZES:
                problems.append("line {}: the board's {} is {}, it takes {}".format(
                    at, __hub_shown(places) if places else key, __shown(value),
                    ", ".join(SCREEN_SIZES)))
                continue
            for place in places:
                settings[place] = text
                written[place] = at
            continue

        kinds = [kind for kind, _prop, _shown in __BOARD_STRIPS]
        screens = __screen_kinds()
        if key not in BOARD_SETTINGS and key not in kinds and key not in screens:
            if not has_strips and key.startswith("strip"):
                problems.append("line {}: this board has no strip connectors, so it "
                                "has no {}".format(at, __strip_shown(key)))
                continue
            if not screens and key.startswith("screen"):
                problems.append("line {}: this board has no screen connectors, so it "
                                "has no {}".format(at, __screen_shown(key)))
                continue
            problems.append("line {}: the board has no setting '{}', it takes {}".format(
                at, key, ", ".join(sorted(list(BOARD_SETTINGS) + kinds + screens))))
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
        if key in kinds:
            length, _divider, order = text.partition("|")
            number = __number(length)
            fault = ("expected a number" if number is None
                     else __value_fault("count", number))
            if fault is not None:
                problems.append("line {}: the board's {} is {}, {}".format(
                    at, __strip_shown(key), __shown(length), fault))
                continue

            # A strip with a brightness of its own takes it as written, or the board's own
            # where none is. A wrong one still leaves the strip its length, so it plays at
            # the board's own
            if key in __BOARD_BRIGHTNESS:
                after = order.strip()
                shown = __strip_shown(key)
                brightness = __number(after) if after else None
                if after.isalpha():
                    problems.append("line {}: the board's {} takes its colours in one order, "
                                    "so what follows its length is its brightness, such as "
                                    "'{}={}|50%'".format(at, shown, shown, int(number)))
                    brightness = None
                elif after and (brightness is None or
                                __value_fault("fraction", brightness) is not None):
                    problems.append("line {}: the board's {} has its brightness as {}, so "
                                    "give it from 0% to 100%, such as '{}={}|50%'".format(
                                        at, shown, __shown(after), shown, int(number)))
                    brightness = None
                settings[key] = int(number)
                settings[key + __BRIGHTNESS] = brightness
                continue

            # The strip takes its colours in the order written, or the board's own order
            # where none is, so a later board entry without one takes it back to that.
            # A wrong order still leaves the strip its length, so it plays in the board's own
            order = order.strip().lower()
            if order and sorted(order) != ["b", "g", "r"]:
                problems.append("line {}: the board's {} has its colours in the order {}, "
                                "so give the letters r, g and b in the order the strip "
                                "takes them, such as '{}={}|rgb'".format(
                                    at, __strip_shown(key), __shown(order),
                                    __strip_shown(key), int(number)))
                order = ""
            settings[key] = int(number)
            settings[key + __ORDER] = order or None
            continue

        if key in screens:
            allowed = SCREEN_SIZES + (HUB,) if __BOARD_HUB[0] else SCREEN_SIZES
        else:
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

    # A later board entry setting the same thing takes over its line, as it takes its value
    for key in settings:
        written.setdefault(key, entry.lines.get(key, entry.line))
    lines.update(written)
    return settings


# Where a hub and a screen were both played on, which of them was refused, kept among the
# board settings under a name no file can write so their entries are not answered twice
__REFUSED = " refused"


def __check_hub(board, lines, entries, problems):
    """
    Settle what the board entries say about a hub against what the entries play on. A
    hub nothing plays on is dropped, as a strip is, and a screen declared on the connector
    the hub's selects take is dropped where nothing plays on it. Where both are played on,
    either could be the mistake, so neither plays.
    """
    hub = __hub_port(board)
    places = sorted(key for key in board if key.startswith(HUB))
    named = {channel.name for entry in entries for channel in entry.channels}

    if hub is None:
        if places and not __BOARD_HUB[0]:
            problems.append("line {}: this board cannot carry a Screen Hub, so it has no "
                            "{}".format(lines[places[0]], __hub_shown(places)))
        elif places:
            problems.append("line {}: the board entry gives {} a size, but no connector has "
                            "the hub. Write it like {}".format(
                                lines[places[0]], __hub_shown(places), __hub_example()))
        for place in places:
            board.pop(place)
        return

    # Drop a hub no entry shows anything on, so its connectors stay free
    if not any(name.startswith(HUB) for name in named):
        for setting in places + [hub]:
            board.pop(setting)
        return

    # The hub takes one connector for its panels and the other for their selects
    for name in __screen_kinds():
        if name == hub or board.get(name) is None:
            continue
        port_name = __screen_port(name)[1]

        if board[name] == HUB:
            problems.append("line {}: the board entry gives both connectors the hub, which "
                            "takes one for its panels and SP/CE {} for their selects".format(
                                lines[name], port_name))
            board.pop(name)
        elif name in named:
            # Nothing says which of the two is wired, so neither is driven
            problems.append("line {}: the hub takes both connectors, so {} and the hub "
                            "cannot both play. Keep one".format(
                                lines[name], __screen_shown(name)))
            for setting in places + [hub, name]:
                board.pop(setting)
            board[__REFUSED] = (HUB, name)
        else:
            problems.append("line {}: SP/CE {} carries the hub's selects, so {} has no "
                            "screen of its own".format(lines[name], port_name,
                                                       __screen_shown(name)))
            board.pop(name)


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
    # The effect an entry asks for, or None if it could not be made
    known = EFFECTS.get(entry.effect)
    if known is None:
        # An entry that named none at all has already been reported as such, and
        # saying the missing name is not an effect only shows the reader an internal
        if entry.effect in SCREEN_EFFECTS and not __BOARD_SCREENS:
            problems.append("line {}: {} plays on a screen, and this board has none".format(
                entry.line, entry.effect))
        elif entry.effect in SCREEN_EFFECTS:
            problems.append("line {}: {} plays on a screen, such as '{}: {} "
                            "file=anim.gif'".format(entry.line, entry.effect,
                                                    __BOARD_SCREENS[0][2], entry.effect))
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
    # One callable per channel, in the order the entry wrote them
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
    # One curve's setting as a player takes it, the file having written one part or two
    return curve(*seconds) if isinstance(seconds, tuple) else curve(seconds)


def __assemble(entries, slots, effects, levels, colours, curves, claimed, problems):
    # Fill one scene's arrays from its entries, or the always-on set's from those
    # before any heading. Claims span every call, since scenes take turns with the
    # same hardware but different channels on it would fight. Returns the slots
    # driven here, which is what a switch must know to clear, and the effects built,
    # which is what a restart begins again
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
                entry.line, ", ".join(__channel_shown(name) for name in missing)))

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
            if kind == "colour" and slot[0] == "mono":
                # A mono channel cannot show a colour, but a colour channel or a strip can
                # play a mono effect: the player draws it in the channel's own tint
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


def __cue_sound(sounds, scene):
    """
    Give the speaker to the sound this scene wants: its own, or the one from before
    any heading where it brings none. The one giving it up remembers where it
    reached, so a long sound picks up where it left off on its next turn, and one
    that had ended starts again from the top.
    """
    wanted = None
    for sound in sounds:
        if sound.scene is None and wanted is None:
            wanted = sound
        if scene is not None and sound.scene == scene.key:
            wanted = sound

    for sound in sounds:
        if sound is not wanted:
            sound.set_aside()

    # One already playing carries on: the scene it also serves has come round again,
    # or it is the always-on sound outlasting a scene with none of its own
    if wanted is not None and not wanted.live:
        wanted.start()


def __apply_scene(players, shows, sounds, scene):
    """
    Point the players, shows and sounds at one scene. Its arrays already carry the
    always-on entries and turn off what other scenes drive, so this is an exchange
    of lists the players read on their next tick.

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
        # A curve and an effect bringing its own colour refuse each other in either
        # order, so a channel this scene leaves uncurved lets go of its curve first
        curves = scene.curves[player.kind]
        player.curves = [held if coming is not None else None
                         for held, coming in zip(player.curves, curves)]
        player.effects = scene.effects[player.kind]
        player.levels = scene.levels[player.kind]
        player.curves = curves
        if player.kind in scene.colours:
            player.colours = scene.colours[player.kind]

    # A screen another scene was using goes dark unless this one, or an always-on
    # entry, is still on it: the glass keeps its frame, the light says it is over
    # One show at a time may have a panel, and a screen may be named by an always-on
    # entry and by a scene both. The scene's own takes it while the scene shows, as a
    # scene takes an always-on output, and the always-on one has it the rest of the time
    # Held by place, since a hub's show covers several positions. An always-on show a
    # scene takes one position from sits the scene out, its other positions cleared
    holding = {}
    for show in shows:
        if show.scene is None:
            for place in show.places:
                holding.setdefault(place, show)
    for show in shows:
        if show.scene == scene.key:
            for place in show.places:
                holding[place] = show

    live = {show for show in shows
            if all(holding.get(place) is show for place in show.places)}
    lit = {place for show in live for place in show.places}

    for show in shows:
        show.live = show in live
        if show.live:
            if scene.restart and show.scene == scene.key:
                show.restart()
            show.resume()
        elif any(place in lit for place in show.places):
            # Another show has this panel, so it stays lit and this one just waits
            show.wait()
        else:
            show.rest()

    __settle_hub(shows)

    # Beginning again reaches the scene's sound too, which forgets where it was up to
    if scene.restart:
        for sound in sounds:
            if sound.scene == scene.key:
                sound.restart()
    __cue_sound(sounds, scene)


def load(text, fx, maker=None, volume=None):
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
    would. Without a maker the change is reported instead. `volume` is the drive the
    file came from, whose sounds play on while a computer holds it.
    """
    # The board is learned first, so the parser's examples name its own parts
    __learn_board(fx)
    entries, problems = parse(text)
    has_strips = bool(__BOARD_STRIPS)

    # Board entries are settings rather than effects, a heading begins a scene, and
    # a screen name routes its whole entry to the screens, so a mistyped one is
    # answered about screens and not about outputs the board never had
    board = {}
    board_lines = {}
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
            given = __check_board(entry, has_strips, problems, board_lines)
            # A board entry may be written more than once, so where the arguments were
            # written is kept rather than checked here: the program may name a later line
            if "args" in given:
                args_line = entry.lines.get("args", entry.line)
            board.update(given)
            continue

        # A selector that named nothing has been answered already, and read as outputs it
        # would be answered again about an effect it never reached
        if not entry.channels:
            continue

        sounding = [channel for channel in entry.channels if channel.name == AUDIO]
        if sounding and len(sounding) != len(entry.channels):
            problems.append("line {}: outputs and audio cannot share an entry".format(
                entry.line))
            continue
        if sounding:
            audio_entries.append(entry)
            continue

        named = [channel for channel in entry.channels
                 if channel.name.startswith("screen") or channel.name.startswith(HUB)]
        if named and len(named) != len(entry.channels):
            problems.append("line {}: outputs and screens cannot share an entry".format(
                entry.line))
        elif named:
            screen_entries.append(entry)
        else:
            grouped[entry.scene].append(entry)

    # Drop the length of any strip no entry plays on, so its connector stays off
    used = {__strip_of(channel.name) for group in grouped.values() for entry in group
            for channel in entry.channels}
    for kind, _prop, _shown in __BOARD_STRIPS:
        if kind not in used:
            board.pop(kind, None)
            board.pop(kind + __after(kind), None)

    # A strip taking another's terminals cannot play beside it. The other plays, being the
    # commoner build, and this one's entries go unanswered past the reason given here
    left_off = set()
    for kind, taken in __BOARD_TAKES:
        playing = [other for other in taken if board.get(other)]
        if board.get(kind) and playing:
            others = " and ".join(__strip_shown(other) for other in playing)
            problems.append("line {}: {} uses the same terminals as {}, so it is left off. "
                            "Take {} off the board line to play it".format(
                                board_lines[kind], __strip_shown(kind), others, others))
            board.pop(kind)
            board.pop(kind + __after(kind), None)
            left_off.add(kind)

    __check_hub(board, board_lines, screen_entries, problems)

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
    if maker is not None and not callable(fx) and \
            __hardware_changed(fx, board, __wants_full_size(screen_entries, board)):
        __STRIPS.clear()
        __SCREENS.clear()
        __HUB.clear()
        fx.shutdown()
        fx = maker

    # The board comes up here, now that its own entry has been read: a strip's length
    # is declared at construction, and this is the first point it is known
    fx = __board(fx, board, problems)
    mono, colour = channels(fx)

    # The hub built with the board is recorded once, so a reload compares against it
    if not __HUB and __hub_port(board) is not None and \
            getattr(type(fx), "hub", None) is not None:
        __HUB.update(__hub_declared(board))
        __HUB["groups"] = {}

    # The strips the file asked for, taken before its channel names are resolved: a
    # bare strip name stands for a run whose length only the board entry knows
    built, failed = strips(fx, board, problems)
    __resolve_strips(entries, board, has_strips, problems, failed | left_off)

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
    # Every kind but the mono channels can show a colour, and holds the tint a mono effect
    # is drawn in
    colours = {kind: [(255, 255, 255)] * len(holds) for kind, holds in names
               if kind != "mono"}
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
    sounds = __build_sounds(audio_entries, fx, problems, volume)

    # Found in the order the work happens, which is every line the parser read and
    # then every entry the loader built, so a reader gets them in the file's order
    return fx, players, shows, sounds, scenes, board, __in_line_order(problems)
