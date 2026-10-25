# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# The runner. run() plays the effects file and watches the button and the drive, reading the
# file again when a press or a save asks. Problems go to errors.txt and to the indicators. A
# board entry can name a program to run instead.

import os
import sys
import time

from picofx import RGBLED
from picofx.colour import BLUE, RED, WHITE

from .vocabulary import CONFIG_PATH, ERRORS_PATH
from .hardware import BUILT_HUB, BUILT_SCREENS, BUILT_STRIPS, forget_built
from .parser import in_line_order
from .checks import copies
from .shows import (DEFERRED_SHOWS, pending_shows, REPORTING_TO, service_shows, settle_hub,
                    user_trace)
from .sounds import cue_sound
from .loader import apply_scene, load

# Short of full, which is uncomfortable on an indicator at arm's length and buys no
# legibility across a room
INDICATOR_LEVEL = 0.75

# One length for all of them, so the count is the only thing carrying the scale
FLASH_MS = 150

# What the indicators say where a file cannot, as (colour, level, times, period). A
# board carries indicator LEDs shadowing its outputs, or one LED of its own where it
# has no outputs, so colour reaches a user whatever they have wired in and is what
# they read first. The count reaches anyone whose indicators are removed. Both climb
# with how much trouble the reader is in, and red lands on the one condition with
# nothing else to say it, errors.txt speaking for the blue and the drive itself for
# the white. Never red against green, the pair most often confused by eye.
#
# White lights three channels and still reads dimmer than one channel does at the
# same level, so its own is set by eye.

BLOCKED = (WHITE, 0.5, 1, FLASH_MS)              # The computer was mid-write, nothing happened
PROBLEM = (BLUE, INDICATOR_LEVEL, 2, FLASH_MS)   # Written down as well, in errors.txt
UNREPORTED = (RED, INDICATOR_LEVEL, 3, FLASH_MS)  # Nowhere to write it, so this is all there is

# Shown while the computer is copying, as (colour, resting level, travelling level).
# White is the computer's colour here, a spot travelling the outputs while it works
# and one bright flash of every output where it refused a press, so the flash reads
# on top. The spot stays below BLOCKED's level for that reason, and the floor stays
# above the point an output stops being visibly lit.
TRANSFER = (WHITE, 0.1, 0.35)

# How long the spot spends on each output, and how long the whole thing is held on
# past the transfer. Each file a user drags is its own run of busy, and the outputs
# would otherwise stop and start between them.
TRANSFER_STEP_MS = 120
TRANSFER_HOLD_MS = 500

# How often a single indicator flashes while the computer is copying, lit for one step at
# the end of each period, since a spot with nowhere to travel would hold it steady
TRANSFER_PERIOD_MS = 840

# What one pass of the spot costs as the drive changes hands, per output. Half the
# transfer's step, since this says something happened rather than that it is still going
HANDOVER_STEP_MS = TRANSFER_STEP_MS // 2


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
    problems = in_line_order(problems)

    for problem in problems:
        print(problem)

    try:
        with open(path, "w") as handle:
            # General, since a named program that will not run is reported here too
            # and the effects file may have read perfectly
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
    # The LEDs a signal shows on, the outputs or else the board's own LED
    if fx.outputs:
        return fx.outputs
    rgb = getattr(fx, "rgb", None)
    return [] if rgb is None else [rgb]


def __flashed(fx):
    # The LEDs a flash shows on, the indicators and the board's own LED beside its outputs,
    # since mono outputs alone would show the count and not the colour. That LED takes no
    # part in the spot, sitting outside the line the outputs make
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


def __tell(fx, problems, errors, running):
    # Write the problems down and flash how bad they are. A drive that is full, damaged
    # or absent leaves the report nowhere to go, and the outputs then say it alone
    wrote = report(problems, errors, running)
    if problems:
        indicate(fx, PROBLEM if wrote else UNREPORTED)


def __play(fx, volume, path, errors, playing, sounding=(), maker=None):
    # Stop what is playing, read the file again, and play what it now says.
    #
    # Takes a board or something that makes one, and hands the board back, since the file
    # is what declares a strip and on the first read nothing is built yet. `maker` is
    # passed through to load(), which rebuilds the board where its entry changed
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
    # The rail follows the players, down here with everything stopped and up again in
    # __start() once something is driving the header
    if not callable(fx):
        fx.clear()
        # The panels go out with the lights. Left lit they are the one thing still
        # showing the file that has just been set aside, and a screen an entry no
        # longer names would stay lit for good
        for screen, _size in BUILT_SCREENS.values():
            screen.backlight.off()
        light = BUILT_HUB.get("light")
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
    # failed, and the board still has to come up, being what answers on the lights
    if callable(fx):
        fx = fx()

    # Without a volume nothing here will run the program, so the screen entries it
    # deferred are wanted now rather than never
    if volume is None and DEFERRED_SHOWS:
        shows = pending_shows(problems)

    if volume is not None:
        # A shipped document the mount left stale is said here too, errors.txt being
        # where a reader with only the drive in front of them will look
        for name in volume.unhealed():
            problems.append("the FX drive is full, so {} is out of date; delete a "
                            "picture or sound from the drive to let it "
                            "rebuild".format(name))
    __tell(fx, problems, errors, bool(players or shows or sounds))

    # Started by the caller, which is the only one that knows whether a program is
    # about to take the board over
    return fx, players, shows, sounds, scenes, settings, problems


# What the players are ticked at. picofx defaults to 100, which a board driving
# screens as well cannot afford, the timer running on the same core as the frames
# and taking most of their time. Effects tick by elapsed time, so the rate is
# smoothness alone.
PLAYER_FPS = 50


def __start(players, fx):
    # A paired player is ticked by its partner, so only the head starts a timer.
    #
    # The strip header's rail comes up here as well, where a strip was built, since the
    # board leaves it down until asked and this is when something starts driving it
    if BUILT_STRIPS:
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
    # which way the drive went, reading the outputs as a line from the USB connector
    # to the far end. A pass towards the end is the board taking the drive, the way
    # a transfer travels since the drive reports only writes, and one towards the
    # connector is the computer taking it
    count = len(__indicators(fx))
    order = range(count) if to_board else range(count - 1, -1, -1)
    for lit in order:
        __spot(fx, lit)
        time.sleep_ms(HANDOVER_STEP_MS)


def __transfer_frame(fx, at):
    # One frame of the wait shown while the computer is copying, a spot travelling the
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


def __read_program(name, problems):
    # The source of a program the file named, or None if there is none to read.
    #
    # Read before the drive is shown, since exposing it unmounts the mount point and a
    # program kept on the drive could not be opened once the computer has it
    found = copies(name)
    source = None
    if found:
        # Only the copy that runs is read, since a program can be large
        try:
            with open(found[0]) as handle:
                source = handle.read()
        except OSError:
            pass

    if source is None:
        # What is running is said here rather than in the report's heading, which
        # speaks for the file as a whole and is right about it either way
        problems.append("there is no program called {}, so the effects are running "
                        "instead".format(name))
        return None

    # The drive's copy runs, so a copy on the board's own filesystem is worth saying,
    # since edits made to it would do nothing
    if len(found) > 1:
        problems.append("{} is on the drive and on the board's own filesystem, so "
                        "the drive's copy is the one that runs".format(name))

    return source


def __run_program(name, source, args, problems):
    # Run what was read, and say so if it stops rather than letting it take the board.
    #
    # The file's arguments arrive the way a program receives them anywhere, so the same
    # file runs unchanged from an editor, where sys.argv is empty and a program falls
    # back to its own constants. sys.argv cannot be rebound, so it is filled in place and
    # emptied after, or a reload would inherit the last program's arguments. The name
    # sits at [0] as it does everywhere, and a program reads argv[1:], since no editor
    # supplies one
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

    With one, the drive is shown at boot and the button is watched from then on. A
    double press shows or hides it, a single press re-reads the file and puts the
    drive back, and hiding or ejecting re-reads it and leaves it away, since a user
    who ejected is done with it. This does not return.

    The effects stand aside while the computer is copying, and the outputs answer for
    themselves where there is no file to answer in, for a problem written down, a
    problem with nowhere to write it and a press refused mid-write.

    A board entry can name a program to run instead, and can keep the drive hidden
    until the button asks for it. A screen entry is serviced from this loop, so
    without a volume the caller services the shows it is returned.
    """
    # What rebuilds the board where a reload's board entry changes the hardware.
    # A caller handing in a built board keeps it for the whole run
    maker = fx if callable(fx) else None

    # A drawing that stops does so long after this returned its problems, so it writes
    # its own, and this is how it knows where they go
    REPORTING_TO[0] = errors

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
        """
        Enter the first scene, set its clock and start the players, for a boot and every
        reload.
        """
        nonlocal scene_at, scene_deadline
        scene_at = 0
        scene_deadline = None
        if scenes:
            apply_scene(players, shows, sounds, scenes[0])
            if scenes[0].hold:
                scene_deadline = time.ticks_add(time.ticks_ms(), int(scenes[0].hold * 1000))
        else:
            cue_sound(sounds, None)
            settle_hub(shows)
        __start(players, fx)

    if volume is None:
        begin_scenes()
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
    # are never started, since reading the program and showing the drive both take long
    # enough for a flash of them to be seen
    if not program:
        begin_scenes()

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
        shows = pending_shows(problems)

        # Here because the program could not be found or run, or because it finished
        # by itself. Either way the effects take the board back, and anything that
        # went wrong is said where the user is looking
        if volume.exposed():
            volume.withdraw()
        __tell(fx, problems, errors, bool(players or shows or sounds))
        begin_scenes()                  # Never started above, whether the program ran or not
        if drive_up:
            volume.expose()

    paused = False
    sounds_aside = False
    idle_since = None

    # A quick tap can start and end inside one screen's service, which a level read
    # between frames never sees. A board catching presses by interrupt is asked for
    # those instead. The rest are polled, and sampled around each screen as well
    pressed = False
    pending = volume.IDLE

    def watch():
        """
        The button and the drive, looked at between the screens as well as at the
        top of the loop. One pass of the screens can outlast the double press
        window, and an event held back until the next pass reads as the button
        being slow. The first event stands until the loop has taken it.

        The board is asked for its tap each time, since a rebuild hands back a new
        board whose interrupt replaces the old one's, and a method held from before
        would never hear another press.
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

    def interrupted():
        """Whether watch() has an event waiting, which stops a pass of the screens."""
        return watch() != volume.IDLE

    # A stop from the REPL arrives as an exception, and without this the outputs
    # keep whatever they were last written and the computer keeps the drive
    try:
        while True:
            event = watch()
            pending = volume.IDLE

            if event == volume.SHOWN:
                # The drive has gone to the computer and the effects carry on. They
                # stand aside for the pass, as they do for a transfer, and take the
                # outputs back after it
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
                # A frame each as the lights start, so the panels come back with them
                service_shows(shows)

            # The rotation, standing aside with everything else while a transfer runs
            if scene_deadline is not None and not paused and \
                    time.ticks_diff(time.ticks_ms(), scene_deadline) >= 0:
                scene_at = (scene_at + 1) % len(scenes)
                scene = scenes[scene_at]
                apply_scene(players, shows, sounds, scene)
                scene_deadline = (time.ticks_add(time.ticks_ms(), int(scene.hold * 1000))
                                  if scene.hold else None)

            # The effects stand aside for a transfer, whose hitch volume.busy() describes,
            # and something of the board's own travels the outputs instead of the show
            # lurching through. So they do for enumeration, which a reset seen since the
            # last pass is the start of
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
                drew = service_shows(shows, interrupted)

            if event == volume.BUSY:
                # A press the computer's writing blocked otherwise looks exactly like
                # one that did nothing. The effects are already standing aside, so
                # every output flashing reads on top of the one that is travelling,
                # and the next frame paints over it
                indicate(fx, BLOCKED)

            # A pass that drew goes straight round, since the next frame may
            # already be due and a wait would then be added to every frame the
            # screens send. Nothing here needs answering sooner than the wait, as
            # the lights run from a timer and a press is latched until it is read
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
        forget_built()
        DEFERRED_SHOWS.clear()
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
