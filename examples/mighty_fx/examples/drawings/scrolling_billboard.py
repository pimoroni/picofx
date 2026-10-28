from picovector import image, rect

"""
Drawing: Scrolling billboard
A scrolling billboard, its posters carried on a loop and read from the drive one at a time.
Section: Billboards and panels
"""

# Entry: screenA: graphics file=scrolling_billboard.py fps=100   (a 2.8" screen)

POSTERS = "/examples/assets/billboards/portrait"
# The loop, in name order. A drawing cannot list a folder, so the names are written out
NAMES = ("amityville.png", "comedy.png", "crunchweet.png", "falconmouse.png", "jk7.png",
         "radical.png", "scooshers.png", "travel.png", "vitaminy.png", "weevil.png",
         "zeropoint.png")
DWELL_MS = 5000
SCROLL_MS = 4000
RAMP = 0.2

# The canvas this drawing expects, a 2.8" screen at rotation 0, stated as the posters are
# fitted to it as they load
WIDTH, HEIGHT = 240, 320

posters = [f"{POSTERS}/{name}" for name in NAMES]


def read_into(where, path):
    """Read one poster from the drive into an image the size of the panel, fitted to it."""
    try:
        poster = image.load(path, WIDTH, HEIGHT)
    except (ValueError, OSError):
        raise RuntimeError(f"'{path}' is missing or corrupt! Check it is on the drive") from None

    where.blit(poster, rect(0, 0, poster.width, poster.height), rect(0, 0, WIDTH, HEIGHT))


def travelled(part):
    """How far through the move the loop is, ramping up, coasting and ramping down."""
    if RAMP <= 0:
        return part

    coasting = 1 / (1 - RAMP)
    if part < RAMP:
        return coasting * part * part / (2 * RAMP)
    if part < 1 - RAMP:
        return coasting * (part - RAMP / 2)

    return 1 - coasting * (1 - part) * (1 - part) / (2 * RAMP)


# The poster facing out and the one waiting below it, each a panel-sized image. The entry's
# offset is fixed, so the scroll is a window over the two, blitted into the canvas
upper = image(WIDTH, HEIGHT)
lower = image(WIDTH, HEIGHT)
read_into(upper, posters[0])
read_into(lower, posters[1 % len(posters)])

# Two rects of each pair moved and never made, so a frame allocates nothing
upper_from = rect(0, 0, WIDTH, HEIGHT)
upper_to = rect(0, 0, WIDTH, HEIGHT)
lower_from = rect(0, 0, WIDTH, 0)
lower_to = rect(0, 0, WIDTH, 0)

behind = 1                  # The poster in the lower image, and so the next one up
scrolling = False
scroll_from = 0             # When the scroll in progress began, in elapsed ms
due = None                  # When the loop next moves, in elapsed ms


def window(canvas, at):
    """Draw the panel's view of the two posters, `at` rows into the lower one."""
    upper_from.y, upper_from.h = at, HEIGHT - at
    upper_to.h = HEIGHT - at
    if upper_to.h > 0:
        canvas.blit(upper, upper_from, upper_to)

    lower_from.h = at
    lower_to.y, lower_to.h = HEIGHT - at, at
    if at > 0:
        canvas.blit(lower, lower_from, lower_to)


def draw(canvas, elapsed):
    global upper, lower, behind, scrolling, scroll_from, due
    now = elapsed * 1000
    if due is None:
        if (canvas.width, canvas.height) != (WIDTH, HEIGHT):
            raise ValueError(f'this drawing is laid out for {WIDTH}x{HEIGHT}, a 2.8" screen at '
                             f"rotation 0, and was given {canvas.width}x{canvas.height}")
        window(canvas, 0)
        due = now + DWELL_MS

    if scrolling:
        part = min(1.0, (now - scroll_from) / SCROLL_MS)
        window(canvas, round(HEIGHT * travelled(part)))

        if part >= 1.0:
            # The lower poster faces out now, so the images swap and the next is read behind it
            behind = (behind + 1) % len(posters)
            upper, lower = lower, upper
            read_into(lower, posters[behind])
            scrolling = False
            due = now + DWELL_MS

    elif now >= due:
        scrolling = True
        scroll_from = now
