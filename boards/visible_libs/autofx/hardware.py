# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# The board's hardware as its class declares it and as built for the effects file. A reload
# keeps it and compares the new file against it. The strips are built here and the screens
# and hub are recorded here once built. A name goes back into a message as the board
# declares it.
#
# Its records are shared with the files that import them. Each is changed in place and
# never rebound

import sys

from picofx import RGBLED

from .vocabulary import __BRIGHTNESS, COMPONENTS, HUB, HUB_POSITIONS, __ORDER

# A strip's LEDs are named like the outputs, so 'stripL1-10' is a range of them and
# the bare name is the whole run. One kind of channel per connector, since each is a
# player of its own writing to its own strip. The board declares its strips, and those of
# the board being loaded are kept here as (kind, property, name as written), the kind being
# the name in lower case
__BOARD_STRIPS = []

# The board's strips taking a brightness after their length where the rest take a colour
# order, and each strip taking other strips' terminals as (kind, other kinds), so it cannot
# play beside them. An APA102 has one brightness for the whole strip and one colour order,
# and takes data and clock both
__BOARD_BRIGHTNESS = []
__BOARD_TAKES = []

# The selector the parser's examples name: an output by number where the board numbers its
# outputs, or else its own LED, or else its first strip
__BOARD_EXAMPLE = ["out4"]

# The selector names that reach a screen. The board declares its screen ports, and those of the
# board being loaded are kept here as (kind, property, name as written), the kind being the name
# in lower case, with whether the board can carry a Screen Hub
__BOARD_SCREENS = []
__BOARD_HUB = [False]


def __hub_shown(places):
    """Hub positions as the reader writes them, a run of three or more as a range."""
    letters = sorted(HUB_POSITIONS.index(place[len(HUB):]) for place in places)
    parts = []
    at = 0
    while at < len(letters):
        end = at
        while end + 1 < len(letters) and letters[end + 1] == letters[end] + 1:
            end += 1
        if end - at >= 2:
            parts.append(HUB_POSITIONS[letters[at]].upper() + "-" +
                         HUB_POSITIONS[letters[end]].upper())
        else:
            parts.extend(HUB_POSITIONS[one].upper() for one in letters[at:end + 1])
        at = end + 1
    return HUB + ",".join(parts)


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

    # The board's own RGB output, which breaks into three mono channels as an output does
    rgb = getattr(fx, "rgb", None)
    if rgb is not None:
        colour.append(("rgb", rgb))
        for letter, led in zip(COMPONENTS, (rgb.led_r, rgb.led_g, rgb.led_b)):
            mono.append(("rgb.{}".format(letter), led))

    return mono, colour


def __learn_board(fx):
    """
    Keep the strips and screen ports the board declares, and whether it can carry a Screen
    Hub, for everything that names them.

    Asked of the class, so no board need exist yet and no property is evaluated:
    MicroPython's dir() and getattr() both run a property's getter, and one that
    answers by raising would read as an absent connector.
    """
    board = fx if isinstance(fx, type) else type(fx)
    __BOARD_STRIPS[:] = [(name.lower(), prop, name) for name, prop in getattr(board, "STRIPS", ())]
    __BOARD_BRIGHTNESS[:] = [name.lower() for name in getattr(board, "STRIP_BRIGHTNESS", ())]
    __BOARD_TAKES[:] = [(name.lower(), tuple(other.lower() for other in others))
                        for name, others in getattr(board, "STRIP_TAKES", ())]
    __BOARD_SCREENS[:] = [(name.lower(), prop, name) for name, prop in getattr(board, "SCREENS", ())]
    # A board's outputs and its own LED are known by their pins
    outputs = len(getattr(board, "OUT_PINS", ()))
    if outputs:
        __BOARD_EXAMPLE[0] = "out{}".format(min(4, outputs))
    elif hasattr(board, "RGB_PINS"):
        __BOARD_EXAMPLE[0] = "rgb"
    elif __BOARD_STRIPS:
        __BOARD_EXAMPLE[0] = __BOARD_STRIPS[0][2]
    # A hub takes both connectors and is built by the board, so it needs two screen ports, a
    # port able to carry its selects, and a board that hands it back
    hub = len(__BOARD_SCREENS) > 1 and hasattr(board, "hub") and \
        hasattr(__port_classes(fx)[0], "HUB_SELECTS")
    __BOARD_HUB[:] = [hub]


def __port_classes(fx):
    """
    SPCE and SPCEPort as the board's own module defines them, each board naming what its
    connectors can carry. Found by the module holding the board's class, since a MicroPython
    class does not name its module.
    """
    board = fx if isinstance(fx, type) else type(fx)
    for module in sys.modules.values():
        if getattr(module, board.__name__, None) is board:
            return module.SPCE, module.SPCEPort
    raise ImportError("{} is not reachable from any imported module".format(board.__name__))


def __after(kind):
    """Which of a strip's settings follows its length, its brightness or its colour order."""
    return __BRIGHTNESS if kind in __BOARD_BRIGHTNESS else __ORDER


def __hub_example():
    """A board entry giving the board's first screen port the hub, as a message quotes it."""
    return "'board: {}=hub'".format(__BOARD_SCREENS[0][2])


def __screen_kinds():
    """The screen ports' kinds, in the order the board declares them."""
    return [kind for kind, _prop, _shown in __BOARD_SCREENS]


def __screen_port(kind):
    """A screen port as (property, port letter), or None for one the board has not got."""
    for known, prop, _shown in __BOARD_SCREENS:
        if known == kind:
            # Lettered by its property, spce_a being A, since a board with one port names it bare
            return prop, prop[-1].upper()
    return None


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
    for kind, prop, _shown in __BOARD_STRIPS:
        count = settings.get(kind)
        if count:
            after = settings.get(kind + __after(kind))
            declared[prop] = count if after is None else (count, after)

    # A hub is declared at construction, its panels on the connector named and its
    # selects on the other, so the board builds the hub itself
    hub = __hub_port(settings)
    if hub is not None:
        SPCE = __port_classes(fx)[0]
        for kind, prop, _shown in __BOARD_SCREENS:
            declared[prop] = SPCE.SCREEN if kind == hub else SPCE.HUB_SELECTS

    if not declared:
        return fx()

    try:
        return fx(**declared)
    except Exception as e:      # noqa: BLE001
        problems.append("the board could not be set up as the file asks: {}".format(e))
        return fx()


# The strips already running, as (strip, count, after) per connector, after being the colour
# order or brightness that followed the length, or None where the board chose it. A board is
# built once, a reload keeping the one it has, so this is what a changed strip is answered against
__STRIPS = {}

# The hub the board was built with: the screen selector whose connector carries it, and
# each position's size. Empty where the board has none
__HUB = {}


def __hub_declared(board):
    """The hub a board entry asks for, in the shape __HUB records one."""
    hub = __hub_port(board)
    if hub is None:
        return {}
    return {"port": hub, "sizes": {key: board[key] for key in board if key.startswith(HUB)}}


def strips(fx, lengths, problems):
    """
    The strips the file asked for, as (kind, strip, count), and the kinds a board
    would not set up.

    A board declares its strips in STRIPS, each by the name a file writes and the
    property handing it back, something taking set_rgb(index, red, green, blue), and is
    built with each one's length given by that property's name.
    """
    built = []
    failed = set()

    for kind, prop, _shown in __BOARD_STRIPS:
        count = lengths.get(kind)
        if not count:
            continue

        after = lengths.get(kind + __after(kind))
        running = __STRIPS.get(kind)
        if running is not None:
            strip, leds, running_after = running
            if count != leds:
                problems.append("{} is already running with {} LEDs, so its new length "
                                "needs the board turning off and on".format(
                                    __strip_shown(kind), leds))
            if after != running_after and kind in __BOARD_BRIGHTNESS:
                problems.append("{} is already running at another brightness, so the new "
                                "one needs the board turning off and on".format(
                                    __strip_shown(kind)))
            elif after != running_after:
                problems.append("{} is already running with its colours in another "
                                "order, so the new one needs the board turning off and "
                                "on".format(__strip_shown(kind)))
            lengths[kind] = leds
            built.append((kind, strip, leds))
            continue

        try:
            strip = getattr(fx, prop)
        # Reached where the board refused the length or offers no such connector,
        # which the board's own message may already have said. Said again here so an
        # entry naming the strip is answered rather than left with no slots
        except Exception as e:      # noqa: BLE001
            failed.add(kind)
            lengths.pop(kind, None)
            problems.append("{} could not be set up: {}".format(__strip_shown(kind), e))
            continue

        __STRIPS[kind] = (strip, count, after)
        built.append((kind, strip, count))

    return built, failed


# How long a presence probe watches a tearing-effect line for. Two periods of a
# 60Hz panel and a little over, which is all it takes to see any edge at all
PRESENCE_PROBE_MS = 40


def __screen_gone(screen):
    # Whether a panel that was brought up has stopped answering.
    #
    # One unplugged and put back has lost the TEON its bringup set, so it asserts
    # nothing. Nothing is sent to find out: a screen owning its line keeps TE on
    # from bringup, so any edge at all is the panel still being there. One with no
    # signal to read cannot be told about either way, so it counts as present
    if not screen.__v_sync:
        return False
    try:
        return screen.__display.te_probe(PRESENCE_PROBE_MS)[2] == 0
    except Exception:      # noqa: BLE001
        return False


def __hardware_changed(fx, declared, full_size=False):
    """
    Whether the board entry no longer matches what is running: a strip added,
    dropped or resized, a screen's size changed, a panel swapped for another, or a
    file whose screens now want the other reserve, all of which have to come up
    again to be talked to. Asked of a running board on a reload, so what is running
    is this module's own record of what it built.
    """
    # A hub added, dropped, moved to the other connector or given another size at a
    # position is declared at construction, as a strip is
    asked_hub = __hub_declared(declared)
    if asked_hub.get("port") != __HUB.get("port") or \
            asked_hub.get("sizes") != __HUB.get("sizes"):
        return True

    __learn_board(fx)
    for kind, _prop, _shown in __BOARD_STRIPS:
        asked = declared.get(kind)
        running = __STRIPS.get(kind)
        if asked and running is None:
            return True
        if running is not None and (asked != running[1] or
                                    declared.get(kind + __after(kind)) != running[2]):
            return True

    # Check if any screen is running, since a board with none may have no screens module
    if not __SCREENS:
        return False
    from screens import Reserve
    wanted = Reserve.FULL_SIZE_IMAGES if full_size else Reserve.CANVAS_SPACE

    for name in __screen_kinds():
        asked = declared.get(name)
        known = __SCREENS.get(name)
        if known is None:
            continue
        if asked is not None and asked != known[1]:
            return True
        # A screen reserves for full-size images or for canvas space, and update_pair
        # refuses two that disagree, so a file wanting the other wants both rebuilt
        if known[0].__reserve != wanted:
            return True
        if __screen_gone(known[0]):
            return True
    return False


def __strip_of(name):
    """The board's strip a channel name belongs to, or None where it names something else."""
    for kind, _prop, _shown in __BOARD_STRIPS:
        if name == kind or (name.startswith(kind) and not name[len(kind)].isalpha()):
            return kind
    return None


def __strip_shown(kind):
    """
    The strip as the reader writes it, as the board declares it, or for one the board has not
    got its last letter in capitals, as a connector letter is written.
    """
    for known, _prop, shown in __BOARD_STRIPS:
        if known == kind:
            return shown
    return kind[:-1] + kind[-1].upper()


def __channel_shown(name):
    """A channel name as the reader writes it, a strip's with its capitals back and its LEDs after."""
    letters = name
    while letters and not letters[-1].isalpha():
        letters = letters[:-1]
    if not letters.startswith("strip") or letters == "strip":
        return name
    return __strip_shown(letters) + name[len(letters):]


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
    """The selector as the board declares it, or with the port letter back in capitals."""
    for kind, _prop, shown in __BOARD_SCREENS:
        if kind == name:
            return shown
    return "screen" + name[6:].upper()


def __hub_port(board):
    """The screen selector whose connector carries the hub, or None without one."""
    for name in __screen_kinds():
        if board.get(name) == HUB:
            return name
    return None
