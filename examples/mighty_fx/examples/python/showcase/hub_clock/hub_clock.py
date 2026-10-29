import gc
import machine
import sys
import time
from mighty_fx import MightyFX, SPCE
from timing import Pacer
from screens import SCREEN_TYPES
from picovector import image

"""
Draw a clock across the panels on a screen hub, a digit a panel, in one of the faces kept in the
clock_faces folder beside this file. Six panels show hours, minutes and seconds, and four show hours
and minutes or minutes and seconds.

Frames are drawn ahead of the moment they show, so when it comes only the writes remain, and only a
panel whose digit changes is written. The panels share one bus, so the writes take turns: the seconds
keep their pace while a change further left runs alongside them, right to left a digit at a time.

Press "Boot" to exit the program.

Section: Across several screens
"""

# The face and the panels, from what the effects file passes in args, the face first and then the size
args = sys.argv[1:]
THEME = args[0] if args else "seven_segment"        # A face in clock_faces, named by its file without .py
SCREEN_SIZE = args[1] if args[1:] else "2.8"        # Which screen is on every hub position, "2.8" or "1.54"

# Constants for the clock
CLOCK_START = (23, 59, 50)          # The time it counts on from, Mighty FX having no clock to read
FOUR_PANELS_SHOW = "hours"          # What four panels show, "hours" and minutes or minutes and "seconds"
BLANK_LEADING_ZERO = False          # Whether an hour under ten shows one digit, where a 24 hour clock shows both
BEAT_MS = 500                       # How long the colons stay lit each second
LAMP_TEST_MS = 1500                 # How long every segment stays lit at start, as a clock tests its display at power on
FACES = "/examples/python/showcase/hub_clock/clock_faces"   # Where the faces are on the board's filesystem
COLONS = (1, 3)                     # The digits of HHMMSS a colon follows, drawn on their right edge
WRITE_BUDGET = 6                    # Writes a change may take at the board's own speed, before an animated face's steps are cut to fit
AHEAD_MS = 2000                     # How far ahead frames are drawn while nothing is being written
KEEP_FREE = 512 * 1024              # Memory left free after the frames are made, for everything else

# Constants for the panels' wire. Faster than the board's own setting, as six panels share the one wire
OVERCLOCK = True                    # Whether to raise the system clock and the wire, a panel's write taking about 28ms against 44ms
BAUDRATE = 37_500_000               # The wire every panel runs at, the fastest the hub's wiring carries
CPU_FREQ = 225_000_000              # The system clock, the overclock that still divides down to that wire
BOARD_FREQ = (150_000_000, 48_000_000)  # The system and peripheral clocks Mighty FX runs at, restored on exit

# The clock's pace, by how quickly a panel is written. With quicker writes, frames come closer together
# and a change takes more of them, half as many again, so it lasts about as long but moves more smoothly
FRAME_MS = 80 if OVERCLOCK else 120 # Between one frame of a panel's change and its next, room for another panel's in between
PACE = 1.5 if OVERCLOCK else 1      # How many more frames a change takes than a face asks, and a carry's budget allows

if OVERCLOCK:
    # The SPI divider only reaches BAUDRATE with the peripheral clock raised to the system clock's. Set
    # before the board is set up, so its buses start at the new rate
    machine.freq(CPU_FREQ, CPU_FREQ)

# Create a MightyFX object driving a screen hub, which takes SP/CE port B for extra chip selects
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.HUB_SELECTS)
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Build a screen on every hub port and keep those that answer, as a hub need not be full. 12-bit named,
# as BAUDRATE also has a 16-bit setting, which takes a third longer on the wire
wire = {"baudrate": BAUDRATE, "bitdepth": 12} if OVERCLOCK else {}
panels = []
for port in mighty.hub.ports:
    try:
        panels.append(ScreenType(port, **wire))
    except ValueError:
        pass

if len(panels) not in (4, 6):
    # Release the hub first, as one of its chip selects is a panel's backlight pin
    mighty.shutdown()
    if OVERCLOCK:
        machine.freq(*BOARD_FREQ)
    raise RuntimeError(f"The clock needs four or six panels on the hub, and {len(panels)} answered!")

WIDTH, HEIGHT = panels[0].width, panels[0].height

# The face is loaded from its own file, so only the chosen one takes memory
sys.path.append(FACES)
face = __import__(THEME)
face.prepare(WIDTH, HEIGHT)
COLON_BLINKS = getattr(face, "COLON_BLINKS", True)  # A face may keep its colon steady
STEPS = getattr(face, "CHANGE_STEPS", 0)            # Frames between one digit and the next, for a face that animates a change
WRITE_BUDGET = getattr(face, "WRITE_BUDGET", WRITE_BUDGET)  # Or None, for a face whose every step must show
if not getattr(face, "PACED", True):
    # A face too slow to draw for the extra frames keeps its own, still written the quicker way
    PACE = 1
if WRITE_BUDGET is not None:
    WRITE_BUDGET = round(WRITE_BUDGET * PACE)
CARRY_TOGETHER = getattr(face, "CARRY_TOGETHER", False)     # Whether a carry changes every digit at once, as lamps switch
CARRY_FROM_LEFT = getattr(face, "CARRY_FROM_LEFT", False)   # Whether the rest of a carry runs left to right, as a sign's controller scans
# The panels left of the rightmost, in the order a carry takes them
CARRYING = list(range(len(panels) - 1)) if CARRY_FROM_LEFT else list(range(len(panels) - 2, -1, -1))


def steps_between(previous, digit):
    """Count the frames between two digits, which a face may set by how far apart they are, at PACE."""
    steps = face.change_steps(previous, digit) if hasattr(face, "change_steps") else STEPS
    return round(steps * PACE)


def shows(reading, place):
    """
    Find what a panel shows for a reading of HHMMSS, its digit, or what a face makes of the reading for
    that place, such as a drum's position, which may depend on more than the one digit.
    """
    if hasattr(face, "shows"):
        return face.shows(reading, place)
    return reading[place]

# Which digits of HHMMSS the panels show, left to right in hub order, and those carrying a colon, which
# the last panel never does
FIRST = 2 if len(panels) == 4 and FOUR_PANELS_SHOW == "seconds" else 0
PLACES = range(FIRST, FIRST + len(panels))
WITH_COLON = [place in COLONS and place != PLACES[-1] for place in PLACES]

# What a panel shows is its digit from shows() and whether its colon is lit, None where it has none. A
# picture is that, or a step on the way to it from a digit before. Frames are kept in PSRAM by picture,
# not by panel, so panels showing the same thing share one, and a colon's lit and unlit frames are drawn
# once a digit. As many are made as memory allows once the face has what it needs
frames = {}
gc.collect()
spare = [image(WIDTH, HEIGHT) for _ in range((gc.mem_free() - KEEP_FREE) // (WIDTH * HEIGHT * 4))]

# Each panel's pictures still to write, what its queue ends on, the digit it shows now, and when it was
# last written in its current change, on the clock's pacer
queues = [[] for _ in panels]
targets = [None] * len(panels)
digits = [None] * len(panels)
written = [None] * len(panels)


def showing_at(elapsed):
    """Calculate what each panel shows this many milliseconds after the clock started."""
    hours, minutes, seconds = CLOCK_START
    total = (hours * 3600 + minutes * 60 + seconds + elapsed // 1000) % 86400
    reading = f"{total // 3600:02d}{total // 60 % 60:02d}{total % 60:02d}"
    if BLANK_LEADING_ZERO and reading[0] == "0":
        reading = " " + reading[1:]
    lit = elapsed % 1000 < BEAT_MS or not COLON_BLINKS
    return [(shows(reading, place), lit if colon else None) for place, colon in zip(PLACES, WITH_COLON)]


def pictures(before, after):
    """
    List, for each panel, the pictures a change from one showing to the next writes, in order.

    A digit changing on an animated face passes through its steps on the way, as many as WRITE_BUDGET
    allows with every different change written each step, and anything else goes straight to what is
    shown after. A panel not changing writes nothing. A picture on the way carries its step and how many
    steps its change had, which together say how far along it is.
    """
    moving = {(old[0], new) for old, new in zip(before, after) if STEPS and old is not None and old[0] != new[0]}

    changes = []
    for old, new in zip(before, after):
        if old == new:
            changes.append([])
        elif (old[0] if old else None, new) in moving:
            full = steps_between(old[0], new[0])
            steps = full if WRITE_BUDGET is None else max(0, min(full, WRITE_BUDGET // len(moving) - 1))
            # The steps kept, spread evenly through the full set
            kept = [round(step * (full + 1) / (steps + 1)) for step in range(1, steps + 1)]
            changes.append([(new[0], new[1], old[0], step, full) for step in kept] + [new])
        else:
            changes.append([new])
    return changes


def needed(elapsed, before=None):
    """
    List the pictures still to write, soonest first, as far ahead as AHEAD_MS, the beats changing from
    before, or from what the queues end on.

    The rightmost panel's queue comes first, then the next beat, then the other queues in carry order, as
    the seconds change again before a carry further left is done, then the later beats.
    """
    beats = []
    before = targets if before is None else before
    for beat in range((elapsed // BEAT_MS + 1) * BEAT_MS, elapsed + AHEAD_MS, BEAT_MS):
        after = showing_at(beat)
        beats.append(pictures(before, after))
        before = after

    order = []
    for change in queues[-1:] + beats[0] + [queues[index] for index in CARRYING]:
        order.extend(change)
    for changes in beats[1:]:
        for change in changes:
            order.extend(change)
    return order


def draw_ahead(order, all_of_them=True):
    """Draw a frame for each picture in this order that has none yet, or only the first missing."""
    for picture in order:
        if picture in frames:
            continue
        if not draw_picture(picture, order) or not all_of_them:
            return


draw_ms = 90                        # How long the face takes to draw a frame, kept up to date as it draws


def draw_picture(picture, order):
    """
    Draw a picture into a spare frame, saying whether there was one.

    With no spare, the frame taken is the one whose picture comes latest in the order of what is needed,
    or is not needed at all. Where every frame is needed sooner than this picture, the drawing waits.
    """
    global draw_ms
    began = time.ticks_ms()
    if spare:
        frame = spare.pop()
    else:
        # Each picture's place in the order, the first place where it comes twice
        place = {}
        for index in range(len(order) - 1, -1, -1):
            place[order[index]] = index
        later = len(order)
        latest = max(frames, key=lambda old: place.get(old, later))
        if place.get(latest, later) <= place.get(picture, later):
            return False
        frame = frames.pop(latest)

    if len(picture) == 2:
        face.draw(frame, *picture)
    else:
        digit, colon_lit, previous, step, full = picture
        face.draw(frame, digit, colon_lit, previous, step / (full + 1))
    frames[picture] = frame
    draw_ms = (draw_ms * 3 + time.ticks_diff(time.ticks_ms(), began)) / 4
    return True


def urgency(index):
    """
    Rank a panel's next write, the lowest first.

    A colon changing alone goes first, on the beat, then the rightmost panel, so the seconds tick and
    fall in time, then the rest in carry order, each finishing before the next.
    """
    picture = queues[index][0]
    if len(picture) == 2 and picture[0] == digits[index]:
        return (0, -index)
    return (1, 0) if index == len(panels) - 1 else (2, CARRYING.index(index))


def write_next(elapsed):
    """
    Write the most urgent panel's next picture, or say how long until one is due, 0 where one was written.

    Only the rightmost panel and the first other panel in carry order with a change waiting move at once,
    a frame each FRAME_MS so they take turns and neither stalls, and the rest wait their turn. With
    CARRY_TOGETHER every panel with a change waiting moves. A colon changing alone is due at once.

    A digit is written for its own panel, even where another is changing to the same, as each keeps its
    own time, and colons changing together are written one after the other. A picture not drawn ahead in
    time is drawn just before its write, ahead of everything else in the order of what is needed.
    """
    waiting = [index for index, queue in enumerate(queues) if queue]
    moving = waiting
    if not CARRY_TOGETHER:
        others = [index for index in waiting if index != len(panels) - 1 and urgency(index)[0] != 0]
        moving = [index for index in waiting if urgency(index)[0] < 2] + sorted(others, key=urgency)[:1]
    waits = [0 if urgency(index)[0] == 0 or written[index] is None else written[index] + FRAME_MS - elapsed
             for index in moving]
    due = [index for index, wait in zip(moving, waits) if wait <= 0]
    if not due:
        return min(waits)

    first = min(due, key=urgency)
    if CARRY_TOGETHER and urgency(first)[0] != 0:
        # Panels carrying together take turns with the seconds, the one written longest ago first, so none
        # is left behind. Those not yet written in this change go right to left
        first = min(due, key=lambda index: (-1 if written[index] is None else written[index], -index))
    picture = queues[first][0]
    together = [first]
    if urgency(first)[0] == 0:
        together = [index for index in waiting if queues[index][0] == picture and urgency(index)[0] == 0]
    if picture not in frames:
        draw_picture(picture, [picture] + needed(elapsed))

    for index in together:
        # Without waiting for the panel's refresh to come round, as a clock's frame is gone again too soon
        # for a tear to show
        panels[index].update(frames[picture], v_sync=False)
        queues[index].pop(0)
        # A panel part way through a change shows no digit yet
        digits[index] = picture[0] if len(picture) == 2 else None
        written[index] = elapsed
    return 0


# A lamp test first, every segment lit on every panel, the one frame they all share. Drawn in a spare
# frame, left among the spares, as the memory the frames leave may not hold another
lamp_test = spare[0]
face.draw(lamp_test, shows("888888", 5), True)
for panel in panels:
    panel.update(lamp_test, v_sync=False)
del lamp_test

# The clock's first frames are drawn while the lamp test shows, so it starts with them ready, then as
# many after them as the lamp test leaves time for, as a frame costs the most the first time it is drawn
lamp_ends = time.ticks_add(time.ticks_ms(), LAMP_TEST_MS)
lamp_hold = Pacer(LAMP_TEST_MS / 1000)
first = showing_at(0)
draw_ahead([picture for change in pictures(targets, first) for picture in change])
later = needed(0, first)
for picture in later:
    if time.ticks_diff(lamp_ends, time.ticks_ms()) < draw_ms:
        break
    if picture not in frames and not draw_picture(picture, later):
        break
lamp_hold.hold()

pacer = Pacer(0.01)                 # The clock's pace, looking for a change every 10ms

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        elapsed = pacer.elapsed
        now = showing_at(elapsed)

        # A change joins the end of a panel's queue, so a cascade still running carries on into the next
        for index, change in enumerate(pictures(targets, now)):
            if change:
                queue = queues[index]
                # A panel starting a change afresh has not been written in it yet
                if not queue:
                    written[index] = None
                # Is only the colon changing on a digit still waiting to be written? It takes that picture's
                # place, so blinks missed while a long change was written do not follow it one after another
                if len(change) == 1 and len(change[0]) == 2 and queue and len(queue[-1]) == 2 \
                        and queue[-1][0] == change[0][0]:
                    queue[-1] = change[0]
                else:
                    queue.extend(change)
                targets[index] = now[index]

        # A write that is due goes first, and with none due a frame is drawn ahead if there is time for one
        if any(queues):
            wait = write_next(elapsed)
            if not wait:
                continue
            if wait < draw_ms:
                pacer.hold()
                continue

        # Drawn a frame at a time, so a write waits for one draw at most
        draw_ahead(needed(elapsed), all_of_them=False)
        pacer.hold()

# Stop any running effects and turn off all the outputs, then put the board's clocks back, as they outlast
# a soft reset and the next program's screens expect them
finally:
    mighty.shutdown()
    if OVERCLOCK:
        machine.freq(*BOARD_FREQ)
