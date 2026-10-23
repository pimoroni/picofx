# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# The loader. load() turns an effects file into what the board plays. It builds the effects
# into players beside the shows and sounds and gathers them into scenes. A scene change hands
# the players, shows and sounds to the next scene.

from picofx import ColourPlayer, MonoPlayer, StripPlayer, ease, fade
from picofx.mono import NoneFX

from .vocabulary import (AUDIO, BOARD, COMPONENTS, EFFECTS, HUB, OUTPUT_SETTINGS, SCREEN_EFFECTS,
                         SCREEN_SETTINGS)
from .hardware import (after_length, BOARD_SCREENS, BOARD_STRIPS, BOARD_TAKES, build_board,
                       BUILT_HUB, BUILT_SCREENS, BUILT_STRIPS, channel_shown, channels,
                       hardware_changed, hub_declared, hub_port, learn_board, resolve_strips,
                       strip_of, strip_shown, strips)
from .parser import in_line_order, parse
from .checks import check_board, check_hub, check_settings
from .shows import build_shows, DEFERRED_SHOWS, settle_hub, wants_full_size
from .sounds import build_sounds, cue_sound


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


def __build_effect(entry, count, problems):
    # The effect an entry asks for, or None if it could not be made
    known = EFFECTS.get(entry.effect)
    if known is None:
        # An entry that named none at all has already been reported as such, and
        # saying the missing name is not an effect only shows the reader an internal
        if entry.effect in SCREEN_EFFECTS and not BOARD_SCREENS:
            problems.append("line {}: {} plays on a screen, and this board has none".format(
                entry.line, entry.effect))
        elif entry.effect in SCREEN_EFFECTS:
            problems.append("line {}: {} plays on a screen, such as '{}: {} "
                            "file=anim.gif'".format(entry.line, entry.effect,
                                                    BOARD_SCREENS[0][2], entry.effect))
        elif entry.effect is not None:
            problems.append("line {}: '{}' is not an effect".format(entry.line, entry.effect))
        return None, None, None

    cls, kind, how, taken = known
    settings = check_settings(entry, taken, problems)

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
                entry.line, ", ".join(channel_shown(name) for name in missing)))

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


def apply_scene(players, shows, sounds, scene):
    """
    Point the players, shows and sounds at one scene. Its arrays already carry the
    always-on entries and turn off what other scenes drive, so this is an exchange
    of lists the players read on their next tick.

    A scene told to restart begins its own content again, the always-on entries
    carrying on: their effects are built in their own pass and so are never among a
    scene's, and an effect that keeps no offset has nothing to begin again.
    """
    # A refused pair is tried again. update_pair judges a pair by conversion times it
    # measures, so a pair near the limit can pass on another try
    for show in shows:
        show.refused_with = None

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

    settle_hub(shows)

    # Beginning again reaches the scene's sound too, which forgets where it was up to
    if scene.restart:
        for sound in sounds:
            if sound.scene == scene.key:
                sound.restart()
    cue_sound(sounds, scene)


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
    learn_board(fx)
    entries, problems = parse(text)
    has_strips = bool(BOARD_STRIPS)

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
            given = check_board(entry, has_strips, problems, board_lines)
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
    used = {strip_of(channel.name) for group in grouped.values() for entry in group
            for channel in entry.channels}
    for kind, _prop, _shown in BOARD_STRIPS:
        if kind not in used:
            board.pop(kind, None)
            board.pop(kind + after_length(kind), None)

    # A strip taking another's terminals cannot play beside it. The other plays, being the
    # commoner build, and this one's entries go unanswered past the reason given here
    left_off = set()
    for kind, taken in BOARD_TAKES:
        playing = [other for other in taken if board.get(other)]
        if board.get(kind) and playing:
            others = " and ".join(strip_shown(other) for other in playing)
            problems.append("line {}: {} uses the same terminals as {}, so it is left off. "
                            "Take {} off the board line to play it".format(
                                board_lines[kind], strip_shown(kind), others, others))
            board.pop(kind)
            board.pop(kind + after_length(kind), None)
            left_off.add(kind)

    check_hub(board, board_lines, screen_entries, problems)

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
            hardware_changed(fx, board, wants_full_size(screen_entries, board)):
        BUILT_STRIPS.clear()
        BUILT_SCREENS.clear()
        BUILT_HUB.clear()
        fx.shutdown()
        fx = maker

    # The board comes up here, now that its own entry has been read: a strip's length
    # is declared at construction, and this is the first point it is known
    fx = build_board(fx, board, problems)
    mono, colour = channels(fx)

    # The hub built with the board is recorded once, so a reload compares against it
    if not BUILT_HUB and hub_port(board) is not None and \
            getattr(type(fx), "hub", None) is not None:
        BUILT_HUB.update(hub_declared(board))
        BUILT_HUB["groups"] = {}

    # The strips the file asked for, taken before its channel names are resolved: a
    # bare strip name stands for a run whose length only the board entry knows
    built, failed = strips(fx, board, problems)
    resolve_strips(entries, board, has_strips, problems, failed | left_off)

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
        DEFERRED_SHOWS[:] = [(screen_entries, fx, board)]
        shows = build_shows(screen_entries, fx, board, problems, build=False)
    else:
        DEFERRED_SHOWS[:] = []
        shows = build_shows(screen_entries, fx, board, problems)

    # Opening a file is all a sound costs, so a named program defers nothing here:
    # its handle waits, opened while the board is sure to hold the drive
    sounds = build_sounds(audio_entries, fx, problems, volume)

    # Found in the order the work happens, which is every line the parser read and
    # then every entry the loader built, so a reader gets them in the file's order
    return fx, players, shows, sounds, scenes, board, in_line_order(problems)
