import time
from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import image, rect

"""
Draw a scrolling billboard, its posters carried on a loop and read from the card one at a
time.

Press "Boot" to exit the program.
"""

# The loop, in the order it comes round. As many as you like: the board only ever holds the poster
# on show and the one behind it, so the length costs nothing but the files themselves
POSTER_FILES = (
    "/examples/assets/billboards/portrait/amityville.png",
    "/examples/assets/billboards/portrait/crunchweet.png",
    "/examples/assets/billboards/portrait/travel.png",
    "/examples/assets/billboards/portrait/scooshers.png",
    "/examples/assets/billboards/portrait/weevil.png",
    "/examples/assets/billboards/portrait/vitaminy.png",
    "/examples/assets/billboards/portrait/comedy.png",
    "/examples/assets/billboards/portrait/zeropoint.png",
    "/examples/assets/billboards/portrait/radical.png",
    "/examples/assets/billboards/portrait/jk7.png",
    "/examples/assets/billboards/portrait/falconmouse.png",
)

DWELL = 5.0                         # How long a poster faces out before the loop moves on
SCROLL_MS = 4000                    # How long it takes for the next one to come up

# A motor gets the loop moving, runs it, then brings it to a stand, so the move ramps at each end and
# coasts between. RAMP is how much of it each ramp takes: 0 is no ramp and a jolt at both ends, and
# 0.5 is all ramp and no coast, which peaks at twice the average speed in the middle of the move.
# The middle is where a jump between frames shows most, so a coast is what keeps it smooth
RAMP = 0.2


# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# Two posters tall, and the panel's own way up, so nothing is rotated and nothing is drawn: the
# scroll is the driver reading its frame from further down this canvas each time. On the GC heap
# rather than in SRAM, a portrait frame from PSRAM costing the same as a landscape one from the
# fast region, which leaves that free for anything else
WIDTH, HEIGHT = screen.width, screen.height
canvas = image(WIDTH, HEIGHT * 2)
spare = image(WIDTH, HEIGHT)


def read_into(where, path):
    """One poster from the card, at the panel's size, into the top or bottom half of the loop.

    load() decodes straight to the size asked for, so a file of another shape is fitted rather than
    cropped. A palettised one ignores that and arrives at its own size, one byte a pixel, so it goes
    through a blit instead, which fits it and gives it colour.
    """
    poster = image.load(path, WIDTH, HEIGHT)
    if poster.width == WIDTH and poster.height == HEIGHT and not poster.has_palette:
        canvas.blit(poster, 0, where)
    else:
        canvas.blit(poster, rect(0, 0, poster.width, poster.height),
                    rect(0, where, WIDTH, HEIGHT))


def travelled(part):
    """How far through the move the loop is, from how far through its time it is.

    Ramp up, coast, ramp down. The coast runs at 1 / (1 - RAMP) of the average speed, so a shorter
    ramp is a slower coast and a smoother middle, at the cost of a sharper start and stop.
    """
    if RAMP <= 0:
        return part

    coasting = 1 / (1 - RAMP)
    if part < RAMP:
        return coasting * part * part / (2 * RAMP)
    if part < 1 - RAMP:
        return coasting * (part - RAMP / 2)

    return 1 - coasting * (1 - part) * (1 - part) / (2 * RAMP)


def advance(next_index):
    """Bring the lower poster up and read the one behind it into the space.

    Both happen while the board is standing still, so the third of a second they take is never
    seen. Nothing is written to the panel afterwards either: the top half now holds exactly what
    the panel is already showing, so the loop simply carries on from an offset of nothing.
    """
    spare.blit(canvas, rect(0, HEIGHT, WIDTH, HEIGHT), rect(0, 0, WIDTH, HEIGHT))
    canvas.blit(spare, 0, 0)
    read_into(HEIGHT, POSTER_FILES[next_index])


print(f"{len(POSTER_FILES)} posters on the loop, two of them held at a time")

read_into(0, POSTER_FILES[0])
read_into(HEIGHT, POSTER_FILES[1 % len(POSTER_FILES)])
screen.update(canvas, offset=(0, 0))

behind = 1                          # The poster in the lower half, and so the next one up
started = None
due = time.ticks_add(time.ticks_ms(), int(DWELL * 1000))

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        now = time.ticks_ms()

        if started is not None:
            part = min(1.0, time.ticks_diff(now, started) / SCROLL_MS)

            at = round(HEIGHT * travelled(part))
            screen.update(canvas, offset=(0, -at))

            if part >= 1.0:
                behind = (behind + 1) % len(POSTER_FILES)
                advance(behind)
                started = None
                due = time.ticks_add(time.ticks_ms(), int(DWELL * 1000))

        elif time.ticks_diff(now, due) >= 0:
            started = now

        else:
            time.sleep_ms(10)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
