# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# The screens' shows. Each feeds a screen or a hub from a player, a still or a drawing. The
# screen entries are built into shows here along with the screens they need. A pass over
# the shows draws whichever are due and sends two screens as a pair where it can.
#
# Its records are shared with the files that import them. Each is changed in place and
# never rebound

import io
import sys
import time

from .vocabulary import (CURVES, EFFECTS, ERRORS_PATH, HUB, HUB_POSITIONS, SCREEN_EFFECTS,
                         SCREEN_SIZES)
from .hardware import (__BOARD_HUB, __BOARD_SCREENS, __HUB, __hub_example, __hub_port, __hub_shown,
                       __port_classes, __screen_kinds, __screen_port, __screen_shown, __SCREENS)
from .parser import __shown
from .checks import __check_settings, __find_image, __REFUSED

# Where a problem found after the file was read is written, which run() sets to
# whatever it was told to report to. A drawing is the one thing that can stop long
# after load, so it is the only writer of this
__REPORTING_TO = [ERRORS_PATH]


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
        # The other show of a pair update_pair refused, which is not tried again until a
        # scene changes
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


# Whether the heap is PSRAM, the RP2350's window from 0x11000000, where a drawing gains
# from a canvas in SRAM. id() is an object's address on this port
__HEAP_IN_PSRAM = 0x11000000 <= id(bytearray(16)) < 0x12000000


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
