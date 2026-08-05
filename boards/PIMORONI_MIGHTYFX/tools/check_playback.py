# Checks playback.py, against the two 320x320 test GIFs on the board and against
# synthetic frame counts for the sizes no GIF here has.
#
# Phases: the traversal, printed as a step, frame and dwell table since a bare delays
# list cannot be read without knowing where the cycle was cut, and asserted for the two
# orders that are easy to get wrong; the origin rule, a dwell being earned by arriving
# rather than served to anything placed there; placement, pause and reverse, including
# reverse part way through a dwell; every raise, each naming its fix; and a run on a
# real pair reporting what was achieved against what was asked, where the shortfall is
# real and known.
#
# The pair phase needs two Screen280 on the SP/CE ports; set PAIR to False to skip it.
# A diagnostic, not an example, so it is not copied to the board. Run it with mpremote.

import time

from playback import GIFPlayer, ImagePlayer

SLOW_GIF = "/images/ezgif.com-speed.gif"            # 8 frames at 80ms
FAST_GIF = "/images/ezgif.com-gif-maker (1).gif"    # 6 frames at 40ms
NAMED_FOLDER = "/car"                               # 8 frames, delays in their names
BIG_FOLDER = "/fireplace"                           # 4 frames, larger than the panel
PLAIN_FOLDER = "/frames"                            # 160 half-size palettised frames
PAIR = True
ROTATION = 90
PAIR_MS = 10_000


class Numbered(ImagePlayer):
    """An ImagePlayer whose image is its own frame number, so a check reads the position."""

    def __image_for(self, frame):
        return frame


def numbered(count, delay=80, **settings):
    return Numbered(count, (delay,) * count, **settings)


def steps_of(player):
    """The traversal as frame numbers, by walking it with the public surface."""
    order = []
    player.to_first()
    for _ in range(2 * player.frames):
        order.append(player.image)
        player.advance()
    return order


def dwell_ms(player, limit=8000):
    """How long the frame showing now lasts, on the real clock."""
    showing = player.image
    t0 = time.ticks_ms()
    while player.image == showing:
        if time.ticks_diff(time.ticks_ms(), t0) > limit:
            raise AssertionError("a frame outlasted the measurement window")
    return time.ticks_diff(time.ticks_ms(), t0)


def refuses(what, call):
    try:
        call()
    except ValueError as e:
        print("    {:<44} {}".format(what, e))
        return
    raise AssertionError(f"{what} did not refuse")


def show_cycle(player, label):
    """The cycle with step, frame and dwell lined up, which is the only readable form."""
    delays = player.__delays
    order = player.__order
    print("  {}, cycle {}ms".format(label, player.cycle_ms()))
    print("    step   " + " ".join("{:>5}".format(s) for s in range(len(order))))
    print("    frame  " + " ".join("{:>5}".format(f) for f in order))
    print("    ms     " + " ".join("{:>5}".format(d) for d in delays))


def check_traversal():
    """The orders, their durations, and where a dwell lands."""
    print("The traversal")

    for count in (1, 2, 3, 8):
        plain = numbered(count)
        assert len(plain.__order) == count
        looping = numbered(count, ping_pong=True)
        assert len(looping.__order) == max(2 * count - 2, 1), f"looping ping-pong at n={count}"
        one_shot = numbered(count, loop=False, ping_pong=True)
        assert len(one_shot.__order) == 2 * count - 1, f"one-shot ping-pong at n={count}"
        # The one that is silent when wrong: a one-shot must come to rest back home, or
        # an animation that plays in and out stops one frame short of retracted.
        assert one_shot.__order[-1] == 0, f"one-shot ping-pong rests on {one_shot.__order[-1]}"
        assert numbered(count, loop=False).__order[-1] == count - 1
    print("  orders hold for 1, 2, 3 and 8 frames, and a one-shot ping-pong closes on frame 0")

    sheet_total = 8 * 80
    assert numbered(8).cycle_ms() == sheet_total
    assert numbered(8, ping_pong=True).cycle_ms() == 2 * sheet_total - 160
    assert numbered(8, loop=False, ping_pong=True).cycle_ms() == 2 * sheet_total - 80
    print("  durations hold, the looping figure dropping both endpoints and the one-shot one")

    show_cycle(numbered(6, ping_pong=True, hold=(2, 0.5)), "6 frames at 80ms, hold=(2, 0.5)")
    held = numbered(6, ping_pong=True, hold=(2, 0.5))
    assert list(held.__delays) == [580, 80, 80, 80, 80, 2080, 80, 80, 80, 80]
    assert held.cycle_ms() == 10 * 80 + 2500
    # The dwells come out of the reported target, or a long pause reads as a slow rate.
    assert held.target_ms() == 80, held.target_ms()
    assert numbered(1, ping_pong=True, hold=(2, 0.5)).__delays == (580,), "n=1 dwells once"
    print("  a pair lands chronologically, its second value at the head of the cycle")
    print("  target_ms stays {}ms with 2500ms of dwell in the cycle".format(held.target_ms()))


def check_origin():
    """A dwell is served by arriving, not to anything placed on the step."""
    print("The origin rule")

    player = numbered(6, ping_pong=True, hold=(2, 0.5))
    first = dwell_ms(player)
    assert 60 < first < 140, f"frame 0 showed for {first}ms on the first lap, wanted its own 80"
    while player.image != 0:
        pass
    while player.image == 0:
        pass
    while player.image != 0:
        pass
    later = dwell_ms(player)
    assert 520 < later < 660, f"frame 0 showed for {later}ms on a later lap, wanted 580"
    print("  frame 0 shows for {}ms first time and {}ms after, the dwell being earned".format(
        first, later))

    player = numbered(6, ping_pong=True, hold=2)
    player.to_last()
    placed = dwell_ms(player)
    assert placed < 200, f"a placement on the far end dwelled {placed}ms"
    print("  a placement on the far end sets off in {}ms, not 2080".format(placed))


def check_position_and_pause():
    """Placement, and a pause that keeps its position."""
    print("Placement and pause")

    player = numbered(6, ping_pong=True)
    player.to_frame(4)
    assert player.image == 4
    assert not player.is_reversed(), "to_frame lands on the first step showing a frame"
    player.to_last()
    assert player.image == 5
    player.to_frame(-2)
    assert player.image == 4
    print("  to_frame, to_first and to_last land where they say, negatives included")

    player = numbered(6)
    while player.image != 2:
        pass
    player.pause()
    assert not player.is_playing()
    time.sleep_ms(500)
    assert player.image == 2, "a pause did not hold the frame"
    player.play()
    assert player.is_playing()
    print("  a pause holds its frame across 500ms and plays on from it")

    player = numbered(6, paused=True)
    assert player.has_advanced(), "the first call must fire so the frame reaches the screen"
    assert player.image == 0
    time.sleep_ms(300)
    assert not player.has_advanced(), "a paused player must not advance"
    player.play()
    time.sleep_ms(120)
    assert player.has_advanced()
    print("  paused=True still offers its first frame, then waits for play()")


def check_reverse():
    """Turning around, on a plain order and on both ping-pong legs."""
    print("reverse()")

    player = numbered(6, loop=False)
    while player.image != 2:
        pass
    assert not player.is_reversed()
    player.reverse()
    assert player.image == 2, "reverse must not jump the frame"
    assert player.is_reversed()
    while player.image != 1:
        pass
    print("  a plain order flips and walks back down from where it stood")

    player = numbered(6, loop=False)
    time.sleep_ms(700)
    assert player.is_done()
    player.reverse()
    assert not player.is_done(), "reverse gives an ended one-shot a run to do"
    print("  and an ended one-shot gets a run to do")

    player = numbered(6, ping_pong=True)
    while player.image != 3:
        pass
    assert not player.is_reversed(), "outward leg"
    player.reverse()
    assert player.image == 3, "the mirrored step shows the same frame"
    assert player.is_reversed(), "return leg"
    player.reverse()
    assert not player.is_reversed(), "twice returns"
    print("  ping-pong mirrors the step, and is_reversed follows the leg")

    player = numbered(6, ping_pong=True, hold=2)
    player.to_frame(4)
    while player.image != 5:
        pass
    time.sleep_ms(500)                  # part way into the far end's 2080ms dwell
    player.reverse()
    left = dwell_ms(player)
    assert left < 200, f"{left}ms of dwell survived a reverse"
    assert player.image == 4, "and then it heads back"
    print("  reversing in a dwell drops the balance, leaving {}ms, and heads back".format(left))


def check_refusals():
    """Every raise, each naming the setting that would allow it."""
    print("What it refuses")
    refuses("has_advanced() under fps=False", lambda: numbered(4, fps=False).has_advanced())
    refuses("pause() under fps=False", lambda: numbered(4, fps=False).pause())
    refuses("play() under fps=False", lambda: numbered(4, fps=False).play())
    refuses("is_playing() under fps=False", lambda: numbered(4, fps=False).is_playing())
    refuses("advance() with a clock", lambda: numbered(4).advance())
    refuses("is_done() while looping", lambda: numbered(4).is_done())
    refuses("hold under fps=False", lambda: numbered(4, fps=False, hold=1))
    refuses("paused=True under fps=False", lambda: numbered(4, fps=False, paused=True))
    refuses("hold with no turn to dwell at", lambda: numbered(4, loop=False, hold=1))
    refuses("a hold pair outside a looping ping-pong", lambda: numbered(4, hold=(1, 2)))
    refuses("a hold pair of three values", lambda: numbered(4, ping_pong=True, hold=(1, 2, 3)))
    refuses("a negative dwell", lambda: numbered(4, ping_pong=True, hold=-1))
    refuses("to_frame past the end", lambda: numbered(4).to_frame(4))
    refuses("an fps under a millisecond a frame", lambda: numbered(4, fps=2000))
    refuses("no frames at all", lambda: Numbered(0, ()))
    # A cycle of no length would divide by zero on the first read, and GIFs declaring a
    # zero delay for every frame are written by real tools.
    refuses("a source whose delays are all zero", lambda: numbered(4, delay=0))


def check_caller_driven():
    """fps=False, where advance() is the clock."""
    print("Caller driven")

    player = numbered(8, fps=False)
    assert steps_of(player) == list(range(8)) * 2
    player = numbered(8, fps=False, ping_pong=True)
    assert steps_of(player)[:14] == [0, 1, 2, 3, 4, 5, 6, 7, 6, 5, 4, 3, 2, 1]
    print("  advance() walks the same order the clock would")

    player = numbered(4, fps=False, loop=False)
    for _ in range(10):
        player.advance()
    assert player.image == 3, "a one-shot must stay on its last frame"
    assert player.is_done()
    assert player.cycle_ms() is None and player.target_ms() is None
    print("  a one-shot stays on its last frame and reports done, with no rate to report")


def check_gifs():
    """The real files, and what their figures come out as."""
    print("The GIFs on the board")
    for path, frames, delay in ((SLOW_GIF, 8, 80), (FAST_GIF, 6, 40)):
        player = GIFPlayer(path)
        assert player.frames == frames, f"{path} has {player.frames} frames"
        assert player.frames == len(player.sheet.timings)
        assert player.cycle_ms() == frames * delay
        image = player.image
        assert image.width == 320 and image.height == 320
        print("  {:<38} {} frames, {}ms, {:.1f}fps asked, {}x{} palettised {}".format(
            path.split("/")[-1], player.frames, player.cycle_ms(), player.target_fps(),
            image.width, image.height, image.has_palette))


def check_logging():
    """The level settings, and that a quiet library is the default."""
    import logging

    print("Saying it is working")
    assert (logging.LOG_NONE, logging.LOG_WARN, logging.LOG_INFO, logging.LOG_DEBUG) == (0, 1, 2, 3)
    assert logging.level == logging.LOG_INFO, f"the default level is {logging.level}"
    # The name has to resolve to this module and not to a mip-installed one, which has no
    # warn(), no level and no LOG_* at all.
    for name in ("warn", "info", "debug", "level", "LOG_WARN"):
        assert hasattr(logging, name), f"logging has no {name}, so something has replaced it"
    print("  levels {} to {}, default LOG_INFO, so a wait says so and diagnostics do not".format(
        logging.LOG_NONE, logging.LOG_DEBUG))
    print("  LOG_WARN carries nothing yet, being kept for what actually goes wrong")


def check_sequence():
    """A folder of frames: its order, where its delays come from, and what it costs."""
    from playback import SequencePlayer

    print("Folders of frames")
    for folder, count, delay in ((NAMED_FOLDER, 8, 80), (BIG_FOLDER, 4, 100)):
        t0 = time.ticks_ms()
        player = SequencePlayer(folder)
        took = time.ticks_diff(time.ticks_ms(), t0)
        assert player.frames == count, f"{folder} loaded {player.frames} frames"
        assert player.cycle_ms() == count * delay, f"{folder} cycle {player.cycle_ms()}ms"
        print("  {:<12} {} frames at {}ms from their names, loaded in {}ms".format(
            folder, player.frames, delay, took))
        del player

    # Ordered by the numbers in the names, not lexicographically, or any export past nine
    # frames plays out of order and says nothing about it.
    t0 = time.ticks_ms()
    player = SequencePlayer(PLAIN_FOLDER, fps=25)
    took = time.ticks_diff(time.ticks_ms(), t0)
    numbers = [int(path.split("_")[-1].split(".")[0]) for path in player.paths]
    assert numbers == sorted(numbers), "frames are out of numeric order"
    assert numbers == list(range(len(numbers))), "frames are not a contiguous run"
    assert player.frames == 160
    assert player.cycle_ms() == 160 * 40
    print("  {:<12} {} frames at 25fps, in numeric order, loaded in {}ms".format(
        PLAIN_FOLDER, player.frames, took))
    print("  which is {}ms a frame, and the line above it is the player saying so".format(
        took // player.frames))
    del player

    # Delays from anywhere else arrive as timings, one a frame.
    player = SequencePlayer(NAMED_FOLDER, timings=(50,) * 8)
    assert player.cycle_ms() == 400
    print("  timings given by hand override what the names declare")

    refuses("a folder whose names carry no delay", lambda: SequencePlayer(PLAIN_FOLDER))
    refuses("timings of the wrong length", lambda: SequencePlayer(NAMED_FOLDER, timings=(50, 50)))
    refuses("a folder with no images in it", lambda: SequencePlayer("/lib"))


def check_pair():
    """Two GIFs on a real pair, and the shortfall between asked and achieved."""
    from mighty_fx import SPCE, MightyFX
    from screens import Reserve, Screen280, ScreenPair

    print("On a pair")
    mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
    try:
        # No announcement here: ScreenPair says it is calibrating for itself now.
        pair = ScreenPair(Screen280(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES),
                          Screen280(mighty.spce_b, reserve=Reserve.FULL_SIZE_IMAGES))

        slow = GIFPlayer(SLOW_GIF)
        fast = GIFPlayer(FAST_GIF)
        moved = [0, 0]
        pushes = 0
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < PAIR_MS:
            # Both asked before either is acted on, since or would short-circuit and this
            # phase counts what each player reached. An example is free to short-circuit.
            slow_moved = slow.has_advanced()
            fast_moved = fast.has_advanced()
            if slow_moved or fast_moved:
                pair.update(slow.image, fast.image, rotation=ROTATION)
                pushes += 1
                moved[0] += slow_moved
                moved[1] += fast_moved

        late = sum(screen.display.te_timeouts() for screen in pair.screens)
        for name, player, count in (("slow", slow, moved[0]), ("fast", fast, moved[1])):
            asked = player.target_fps() * PAIR_MS / 1000
            print("  {:<5} asked {:.1f}fps so {:.0f} frames, reached {} at {:.1f}fps".format(
                name, player.target_fps(), asked, count, player.measured_fps()))
        print("  {} pair frames in {}ms, te_timeouts {}".format(pushes, PAIR_MS, late))
        assert late == 0, f"{late} frames began without their TE edge"
        assert pushes > 100, f"only {pushes} pushes, the pair should manage over 100"
    finally:
        mighty.shutdown()


check_traversal()
check_origin()
check_position_and_pause()
check_reverse()
check_refusals()
check_caller_driven()
check_gifs()
check_logging()
check_sequence()
if PAIR:
    check_pair()

print()
print("playback holds")
