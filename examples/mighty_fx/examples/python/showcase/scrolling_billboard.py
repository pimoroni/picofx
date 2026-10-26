import os

from mighty_fx import MightyFX, SPCE
from timing import Pacer, Roller
from screens import Screen280
from picovector import image, rect

"""
Draw a scrolling billboard, its posters carried on a loop and read from the board one at a time.

Press "Boot" to exit the program.
"""

POSTERS = "/examples/assets/billboards/portrait"   # Shared with the billboard examples
DWELL = 5.0                         # How long a poster faces out before the loop moves on
SCROLL_MS = 4000                    # How long it takes for the next one to come up

# How much of a move ramps at each end, 0 jolting at both and 0.5 all ramp
RAMP = 0.2


# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# The loop, every PNG in the folder in name order. Two posters are held at a time, so it can be any length
try:
    posters = [f"{POSTERS}/{name}" for name in sorted(os.listdir(POSTERS)) if name.lower().endswith(".png")]
except OSError:
    posters = []
if not posters:
    mighty.shutdown()
    raise RuntimeError(f"'{POSTERS}' is missing or holds no PNGs! Check it is on the board")

# Two posters tall, so the scroll is the driver reading further down this canvas
WIDTH, HEIGHT = screen.width, screen.height
canvas = image(WIDTH, HEIGHT * 2)
spare = image(WIDTH, HEIGHT)


def read_into(where, path):
    """
    Read one poster from the board into the top or bottom half of the loop, fitted to the panel.

    A file smaller than the panel arrives at its own size, so it is blitted up to fit.
    """
    try:
        poster = image.load(path, WIDTH, HEIGHT)
    except (ValueError, OSError):
        mighty.shutdown()
        raise RuntimeError(f"'{path}' is missing or corrupt! Check it is on the board") from None

    canvas.blit(poster, rect(0, 0, poster.width, poster.height), rect(0, where, WIDTH, HEIGHT))


def travelled(part):
    """
    How far through the move the loop is, ramping up, coasting and ramping down.

    A shorter RAMP coasts slower and starts sharper.
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
    """
    Bring the lower poster up and read the next behind it while the board stands still.

    The top half then matches the panel, so the loop carries on from offset zero.
    """
    spare.blit(canvas, rect(0, HEIGHT, WIDTH, HEIGHT), rect(0, 0, WIDTH, HEIGHT))
    canvas.blit(spare, 0, 0)
    read_into(HEIGHT, posters[next_index])


print(f"{len(posters)} posters on the loop, two of them held at a time")

# The first poster facing out and the second waiting below it
read_into(0, posters[0])
read_into(HEIGHT, posters[1 % len(posters)])
screen.update(canvas, offset=(0, 0))

behind = 1                          # The poster in the lower half, and so the next one up
scrolling = False
pacer = Pacer(0.01)                 # Its elapsed time counts from the start of the scroll in progress
dwell = Roller(DWELL)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        if scrolling:
            # The panel reads further down the canvas the further through the move it is
            part = min(1.0, pacer.elapsed / SCROLL_MS)

            at = round(HEIGHT * travelled(part))
            screen.update(canvas, offset=(0, -at))

            if part >= 1.0:
                # The move is done, so the poster below becomes the top half and the dwell starts
                behind = (behind + 1) % len(posters)
                advance(behind)
                scrolling = False
                dwell.restart()

        elif dwell.is_due():
            scrolling = True
            pacer.restart()

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
