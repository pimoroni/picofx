import gc
import machine
import network
import ntptime
import spidisplay
import sys
import time
import timezones
from mighty_fx import MightyFX, SPCE
from timing import Pacer
from screens import SCREEN_TYPES
from picovector import image

"""
Draw a clock in a choice of styles across a Screen Hub with one digit on each screen. Six panels
show hours, minutes and seconds, and four show hours and minutes or minutes and seconds.

Frames are drawn ahead of the moment they show, so when it comes only the writes remain, and only a
panel whose digit changes is written. The panels share one bus, so the writes take turns: the seconds
keep their pace while a change further left runs alongside them, right to left a digit at a time.

With a WiFi network in secrets.py, the clock reads the time over the internet and shows it in the
TIME_ZONE set there. Where it cannot, it shows the time the board's clock kept from an earlier read,
until the board is powered off, and otherwise counts on from CLOCK_START. The board's clock is taken
to hold UTC, so an editor that sets it to local time puts the clock out by the zone's offset.

The outputs glow white while the time is read, then show green for a time read over WiFi, amber for
one the board's clock kept and blue for CLOCK_START, before the clock starts.

Press "Boot" for the next face, and hold it to exit the program.

Section: Multi-screen
Args: Face = split_flap or flip_dot or drums or lamp_matrix or nixie or lixie or seven_segment or scope
"""

# The face the clock starts in, from what the effects file passes in args
FACE = "split_flap" if not sys.argv[1:] else sys.argv[1]

# The faces in clock_faces, each named by its file without .py, in the order "Boot" steps through them
FACES = ("split_flap", "flip_dot", "drums", "lamp_matrix", "nixie", "lixie", "seven_segment", "scope")
if FACE not in FACES:
    raise ValueError(f"FACE is {FACE!r}. Set it to one of {', '.join(FACES)}")

# Constants for the clock
SCREEN_SIZE = "2.8"                 # The screen on every hub position, as the faces are drawn for 2.8" panels
CLOCK_START = (23, 59, 50)          # The time it counts on from where the board does not know the time
CONNECT_TIMEOUT = 15                # How many seconds to wait for the WiFi network
CLOCK_SET_SINCE = 2025              # A year the board's clock only reaches once set, as it starts in 2021 at power on
FOUR_PANELS_SHOW = "hours"          # What four panels show, "hours" and minutes or minutes and "seconds"
BLANK_LEADING_ZERO = False          # Whether an hour under ten shows one digit, where a 24 hour clock shows both
BEAT_MS = 500                       # How long the colons stay lit each second. It must divide 1000, as frames are drawn ahead a beat at a time
WARM_UP_MS = 1500                   # How long the panels stay dark at start, and at each new face, while its first frames are drawn
QUIT_MS = 1500                      # Held at least this long, the button ends the example
FACES_FOLDER = "/examples/programs/showcase/hub_clock/clock_faces"   # Where the faces are on the board's filesystem
COLONS = (1, 3)                     # The digits of HHMMSS a colon follows, drawn on their right edge
WRITE_BUDGET = 6                    # Writes a change may take at the board's own speed, before an animated face's steps are cut to fit
AHEAD_MS = 2000                     # How far ahead frames are drawn while nothing is being written
KEEP_FREE = 512 * 1024              # Memory left free after the frames are made, for everything else

# Constants for the panels' wire. Faster than the board's own setting, as six panels share the one wire
OVERCLOCK = True                    # Whether to raise the peripheral clock and the wire, so a 2.8" panel writes in about 28ms, not 44ms
BAUDRATE = 37_500_000               # The wire every panel runs at, the fastest the hub's wiring carries
BOARD_PERI_FREQ = 48_000_000        # The peripheral clock Mighty FX runs at, restored on exit

# Constants for the outputs, which say how the clock found the time before it starts
READING = (40, 40, 40)              # While the time is read over WiFi
TIME_READ = (0, 160, 0)             # The time was read over WiFi
TIME_KEPT = (160, 90, 0)            # The time is the one the board's clock kept from an earlier read
NO_TIME = (0, 0, 200)               # The clock counts on from CLOCK_START
STATUS_MS = 1500                    # How long the outputs show how the time was found


def show(outputs, colour):
    """Light every output in one colour."""
    for output in outputs:
        output.set_rgb(*colour)


def set_time(outputs):
    """
    Set the board's clock to UTC over WiFi, saying whether it was set.

    The outputs show READING while it tries. The WiFi is turned off again afterwards, so it takes no
    time from the panels' writes.
    """
    try:
        from secrets import WIFI_PASSWORD, WIFI_SSID
    except ImportError:
        return False
    if len(WIFI_SSID) == 0:
        return False

    show(outputs, READING)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        print(f"Connecting to network '{WIFI_SSID}'")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        began = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), began) > CONNECT_TIMEOUT * 1000:
                print("No connection to the WiFi network")
                return False
            time.sleep(0.1)

        ntptime.settime()
        print("Time set over WiFi")
        return True
    except (OSError, OverflowError):
        print("The time could not be read over WiFi")
        return False
    finally:
        wlan.disconnect()
        wlan.active(False)


def time_known():
    """
    Check if the board's clock holds the time, read over WiFi now or earlier since power on.

    The outputs then show how the time was found for STATUS_MS.
    """
    # Read the time zone first, so a mistake in TIME_ZONE is reported at once
    timezones.utc_offset()

    # A board of its own for the outputs, released before the clock sets up the hub
    indicators = MightyFX()
    try:
        if set_time(indicators.outputs):
            known, colour = True, TIME_READ
        # Check if the board's clock was set by an earlier read, as it keeps the time through a soft reset
        elif time.gmtime()[0] >= CLOCK_SET_SINCE:
            print("Showing the time the board's clock kept")
            known, colour = True, TIME_KEPT
        else:
            print("Counting on from CLOCK_START")
            known, colour = False, NO_TIME
        show(indicators.outputs, colour)
        time.sleep_ms(STATUS_MS)
    finally:
        indicators.shutdown()
    return known


# Set first, so a mistake in secrets.py is reported before the board is set up
time_set = time_known()

# The second the clock started at, in UTC since the epoch where the time was set and otherwise into the day
start_seconds = CLOCK_START[0] * 3600 + CLOCK_START[1] * 60 + CLOCK_START[2]

# The SPI divides the peripheral clock by an even number, so BAUDRATE needs the peripheral clock raised to
# a system clock that is a multiple of twice it. On any other the panels keep the board's own wire
board_freq = machine.freq()
fast_wire = OVERCLOCK and board_freq % (2 * BAUDRATE) == 0

# The clock's pace, by how quickly a panel is written. With quicker writes, frames come closer together
# and a change takes more of them, half as many again, so it lasts about as long but moves more smoothly
FRAME_MS = 80 if fast_wire else 120  # Between one frame of a panel's change and its next, room for another panel's in between
PACE = 1.5 if fast_wire else 1      # How many more frames a change takes than a face asks, and a carry's budget allows

if fast_wire:
    # Set before the board is set up, so its buses start at the new rate
    machine.freq(board_freq, board_freq)

# Create a MightyFX object driving a screen hub, which takes SP/CE port B for extra chip selects
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.HUB_SELECTS)
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Named as 12-bit, since at BAUDRATE the screens default to 16-bit, a third longer on the wire
wire = {"baudrate": BAUDRATE, "bitdepth": 12} if fast_wire else {}
# Build a screen on every hub port and keep those that answer, as a hub need not be full
panels = []
for port in mighty.hub.ports:
    try:
        panels.append(ScreenType(port, **wire))
    except ValueError:
        pass

if len(panels) not in (4, 6):
    # Release the hub first, as one of its chip selects is a panel's backlight pin
    mighty.shutdown()
    if fast_wire:
        machine.freq(board_freq, BOARD_PERI_FREQ)
    raise RuntimeError(f"The clock needs four or six panels on the hub, and {len(panels)} answered!")

WIDTH, HEIGHT = panels[0].width, panels[0].height

# Faces are loaded from their own files, so only the one showing takes memory. Their folder goes first on
# the path, as the drive's root may hold a showcase of the same name
sys.path.insert(0, FACES_FOLDER)

# The face showing, its module and name, and what it asks of the clock, all set by load()
face = face_name = sram_canvas = None
colon_blinks = True                 # Whether the colons blink with the seconds, or stay lit
steps = 0                           # Frames between one digit and the next, for a face that animates a change
budget = WRITE_BUDGET               # Writes a change may take before its steps are cut to fit, or None for every step
pace = PACE                         # How many more frames a change takes than the face asks
carry_together = False              # Whether a carry changes every digit at once, as lamps switch
carrying = []                       # The panels left of the rightmost, in the order a carry takes them

# The hub's panels share one backlight, dark while a face loads and lit once every panel holds the time
unlit = set()
lit = [False]


def steps_between(previous, digit):
    """Count the frames between two digits, which a face may set by how far apart they are, at its pace."""
    count = face.change_steps(previous, digit) if hasattr(face, "change_steps") else steps
    return round(count * pace)


def shows(reading, place):
    """
    Find what a panel shows for a reading of HHMMSS. That is its digit, or what the face makes of the
    reading for that place where it depends on more than one digit, such as a drum's position.
    """
    if hasattr(face, "shows"):
        return face.shows(reading, place)
    return reading[place]

# Which digits of HHMMSS the panels show, left to right in hub order, and which carry a colon, never the last
FIRST = 2 if len(panels) == 4 and FOUR_PANELS_SHOW == "seconds" else 0
PLACES = range(FIRST, FIRST + len(panels))
WITH_COLON = [place in COLONS and place != PLACES[-1] for place in PLACES]

# What a panel shows is its digit from shows() and whether its colon is lit, None where it has none. A
# picture is that, or a step on the way to it from a digit before. Frames are kept in PSRAM by picture,
# not by panel, so panels showing the same thing share one, and a colon's lit and unlit frames are drawn
# once a digit. As many are made as memory allows once a face has what it needs, by load()
frames = {}
spare = []

# Each panel's pictures still to write, what its queue ends on, the digit it shows now, and when it was
# last written in its current change, on the clock's count from clock_elapsed()
queues = [[] for _ in panels]
targets = [None] * len(panels)
digits = [None] * len(panels)
written = [None] * len(panels)


def showing_at(elapsed):
    """Calculate what each panel shows this many milliseconds after the clock started."""
    total = start_seconds + elapsed // 1000
    if time_set:
        # The offset is found for each second, so the clock follows a change to or from summer time
        total += timezones.utc_offset(total) * 60
    total %= 86400
    reading = f"{total // 3600:02d}{total // 60 % 60:02d}{total % 60:02d}"
    if BLANK_LEADING_ZERO and reading[0] == "0":
        reading = " " + reading[1:]
    colon_lit = elapsed % 1000 < BEAT_MS or not colon_blinks
    return [(shows(reading, place), colon_lit if colon else None) for place, colon in zip(PLACES, WITH_COLON)]


def pictures(before, after):
    """
    List, for each panel, the pictures a change from one showing to the next writes, in order.

    A digit changing on an animated face passes through its steps on the way, as many as the face's
    budget allows with every different change written each step, and anything else goes straight to what
    is shown after. A panel not changing writes nothing. A picture on the way carries its step and how
    many steps its change had, which together say how far along it is.
    """
    moving = {(old[0], new) for old, new in zip(before, after) if steps and old is not None and old[0] != new[0]}

    changes = []
    for old, new in zip(before, after):
        if old == new:
            changes.append([])
        elif (old[0] if old else None, new) in moving:
            full = steps_between(old[0], new[0])
            shown = full if budget is None else max(0, min(full, budget // len(moving) - 1))
            # The steps kept, spread evenly through the full set
            kept = [round(step * (full + 1) / (shown + 1)) for step in range(1, shown + 1)]
            changes.append([(new[0], new[1], old[0], step, full) for step in kept] + [new])
        else:
            changes.append([new])
    return changes


def needed(elapsed, before=None):
    """
    List the pictures still to write, soonest first, as far ahead as AHEAD_MS. The beats change from
    before= where it is given, otherwise from what the queues end on.

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
    for change in queues[-1:] + beats[0] + [queues[index] for index in carrying]:
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


DRAW_MS = 90                        # A first guess at how long a face takes to draw a frame
draw_ms = DRAW_MS                   # How long the face takes to draw a frame, kept up to date as it draws


def draw_picture(picture, order):
    """
    Draw a picture into a spare frame, or the one needed latest, and return whether it drew.

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

    canvas = frame if sram_canvas is None else sram_canvas
    if len(picture) == 2:
        face.draw(canvas, *picture)
    else:
        digit, colon_lit, previous, step, full = picture
        face.draw(canvas, digit, colon_lit, previous, step / (full + 1))
    if sram_canvas is not None:
        frame.raw[:] = sram_canvas.raw
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
    return (1, 0) if index == len(panels) - 1 else (2, carrying.index(index))


def write_next(elapsed):
    """
    Write the most urgent panel's next picture, or say how long until one is due, 0 where one was written.

    Only the rightmost panel and the first other panel in carry order with a change waiting move at once,
    a frame each FRAME_MS so they take turns and neither stalls, and the rest wait their turn. Where a
    face carries together, every panel with a change waiting moves. A colon changing alone is due at once.

    A digit is written for its own panel, even where another is changing to the same, as each keeps its
    own time, and colons changing together are written one after the other. A picture not drawn ahead in
    time is drawn just before its write, ahead of everything else in the order of what is needed.
    """
    waiting = [index for index, queue in enumerate(queues) if queue]
    moving = waiting
    if not carry_together:
        others = [index for index in waiting if index != len(panels) - 1 and urgency(index)[0] != 0]
        moving = [index for index in waiting if urgency(index)[0] < 2] + ([min(others, key=urgency)] if others else [])
    waits = [0 if urgency(index)[0] == 0 or written[index] is None else written[index] + FRAME_MS - elapsed
             for index in moving]
    due = [index for index, wait in zip(moving, waits) if wait <= 0]
    if not due:
        return min(waits)

    first = min(due, key=urgency)
    if carry_together and urgency(first)[0] != 0:
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
        # Without waiting for the panel's refresh, as a clock's frame is gone too soon for a tear to show
        panels[index].update(frames[picture], v_sync=False)
        queues[index].pop(0)
        # A panel part way through a change shows no digit yet
        digits[index] = picture[0] if len(picture) == 2 else None
        written[index] = elapsed
        # The hub's one backlight lights once every panel holds the time, so none shows what it held before
        unlit.discard(index)
        if not unlit and not lit[0]:
            panels[0].backlight.on()
            panels[0].brightness(1.0)
            lit[0] = True
    return 0


def load(next_name):
    """
    Switch the clock to a face. Its panels stay dark until each holds the time in it.

    The face before gives back everything it held, its frames included, so the next face can use more
    memory than the last. The frames are then made again from what memory is left.
    """
    global face, face_name, sram_canvas, colon_blinks, steps, budget, pace, carry_together, carrying, draw_ms
    panels[0].backlight.off()
    unlit.update(range(len(panels)))
    lit[0] = False
    for index in range(len(panels)):
        queues[index].clear()
        targets[index] = digits[index] = written[index] = None

    frames.clear()
    spare.clear()
    if face_name is not None:
        sys.modules.pop(face_name, None)
    face = sram_canvas = None
    # The SRAM the face claimed, or its canvas took, goes with it
    spidisplay.release_buffers()
    gc.collect()

    face_name = next_name
    face = __import__(face_name)
    face.prepare(WIDTH, HEIGHT)
    colon_blinks = getattr(face, "COLON_BLINKS", True)
    steps = getattr(face, "CHANGE_STEPS", 0)
    # A face too slow to draw for the extra frames keeps its own, still written the quicker way
    pace = PACE if getattr(face, "PACED", True) else 1
    budget = getattr(face, "WRITE_BUDGET", WRITE_BUDGET)
    if budget is not None:
        budget = round(budget * pace)
    carry_together = getattr(face, "CARRY_TOGETHER", False)
    # Check if the face's carry runs left to right, as a sign's controller scans
    if getattr(face, "CARRY_FROM_LEFT", False):
        carrying = list(range(len(panels) - 1))
    else:
        carrying = list(range(len(panels) - 2, -1, -1))

    # Check if the face asks for a canvas in SRAM, where a slow face draws faster. Each frame is then
    # copied into its place in PSRAM
    if getattr(face, "DRAW_IN_SRAM", False):
        try:
            sram_canvas = image(WIDTH, HEIGHT, spidisplay.buffer(WIDTH * HEIGHT * spidisplay.PIXEL_BYTES))
        except ValueError:
            # The panels leave SRAM no room, so the face draws in PSRAM
            pass

    gc.collect()
    count = (gc.mem_free() - KEEP_FREE) // (WIDTH * HEIGHT * spidisplay.PIXEL_BYTES)
    try:
        for _ in range(count):
            spare.append(image(WIDTH, HEIGHT))
    except MemoryError:
        # Memory freed by the face before can be left in pieces too small for a frame, so fewer are made
        pass
    if not spare:
        raise MemoryError(f"There is not enough memory for the {face_name} face's frames")
    draw_ms = DRAW_MS


DAY_MS = 86_400_000                 # A day in milliseconds, after which the clock's count starts again
clock_origin = None                 # The ticks the clock's count is from, set once the clock starts


def clock_elapsed():
    """Count the milliseconds since the clock started, less a day for each day next_day() has moved it on."""
    return time.ticks_diff(time.ticks_ms(), clock_origin)


def next_day():
    """
    Move the clock's count on a day, and its start with it, keeping what it shows.

    A ticks difference holds about six days, so the count starts again each day.
    """
    global clock_origin, start_seconds
    clock_origin = time.ticks_add(clock_origin, DAY_MS)
    start_seconds += DAY_MS // 1000
    for index, at in enumerate(written):
        if at is not None:
            written[index] = at - DAY_MS


def warm_up(at):
    """
    Draw the frames the clock first shows, at this many milliseconds on its count, then as many after them
    as there is time for, and wait until then.

    A frame costs the most the first time it is drawn, so these are drawn while the panels are dark.
    """
    first = showing_at(at)
    draw_ahead([picture for change in pictures(targets, first) for picture in change])
    later = needed(at, first)
    for picture in later:
        if at - clock_elapsed() < draw_ms:
            break
        if picture not in frames and not draw_picture(picture, later):
            break
    while clock_elapsed() < at:
        pacer.hold()


pressed_since = None
leaving = False

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    load(FACE)
    if time_set:
        # Started on the turn of a second, so the clock's seconds change with the real ones
        second = time.time()
        while time.time() == second:
            pass
        start_seconds = second + 1
    clock_origin = time.ticks_ms()
    pacer = Pacer(0.01)             # A pacer that looks for a change every 10ms
    warm_up(WARM_UP_MS)
    print(f"Press Boot for the next face, hold it {QUIT_MS}ms to finish")

    while not leaving:
        # Check if Boot is down. A press is judged on release, since it cannot be told from a hold until then
        if mighty.boot_pressed():
            if pressed_since is None:
                pressed_since = time.ticks_ms()

        elif pressed_since is not None:
            held = time.ticks_diff(time.ticks_ms(), pressed_since)
            pressed_since = None
            if held >= QUIT_MS:
                leaving = True
                continue
            # The clock keeps counting while the next face loads, and shows it from where it has got to
            load(FACES[(FACES.index(face_name) + 1) % len(FACES)])
            warm_up(clock_elapsed() + WARM_UP_MS)
            print(f"> {face_name}")

        elapsed = clock_elapsed()
        # Check if the clock has run a day. Moved on here and nowhere else, as the waits above count to a set time
        if elapsed >= DAY_MS:
            next_day()
            elapsed -= DAY_MS
        now = showing_at(elapsed)

        # A change joins the end of a panel's queue, so a cascade still running carries on into the next
        for index, change in enumerate(pictures(targets, now)):
            if change:
                queue = queues[index]
                # Check if the panel starts a change afresh, so it has not been written in it yet
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
    if fast_wire:
        machine.freq(board_freq, BOARD_PERI_FREQ)
    # The face and its folder go too, so a run again without a reset loads the face afresh
    sys.modules.pop(face_name, None)
    sys.path.remove(FACES_FOLDER)
