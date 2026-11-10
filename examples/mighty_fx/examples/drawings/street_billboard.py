from picovector import brush, color, image, rect, shape, vec2

"""
Show a folder of posters as if each stood in a case behind glass.

A canvas lets a case and light across the glass go over the poster, and only the poster changes.

The pane is drawn once into an image of its own and blitted over each poster, its window cut with
brush.erase(). The case is opaque, as a translucent one reads only over flat or dark art.

Drawing: Street billboard
Defaults: Rotation = 0 or 180, Pixel double = false
Section: Billboards and panels
"""

# Constants
POSTERS = "/examples/pictures/billboards/portrait"   # Shared with the billboard showcases
# The posters shown from the folder, in turn. A drawing cannot list a folder, so one added to it
# is shown once its name is added here
POSTER_NAMES = ("amityville", "comedy", "crunchweet", "falconmouse", "jk7", "radical",
                "scooshers", "travel", "vitaminy", "weevil", "zeropoint")
DWELL = 3.0                      # Seconds a poster is up for
LEVEL = 17                       # One of the 16 levels the screens drive a channel at, the least that shows
CASE_WIDE = 4                    # How far the case reaches over the poster
CASE_ROUND = 10                  # The window's corner, which hides the poster's square one
GLASS = color.rgb(28, 44, 66)    # What a sheet of glass takes out of what is behind it
SKY = color.rgb(225, 242, 255)   # And what it gives back
CASE = color.rgb(150, 150, 150)
CASE_LIT = color.rgb(215, 220, 230)  # Four levels above the case, so the lit edge reads as one
LEAN = 150                       # How far a band slides over the poster's height, which sets its angle

# Each band's middle, half width, edge ramp, strength in levels, and whether it is the window reflected
# or the room. Both are wanted, since light cannot lighten a pale poster
BANDS = ((30, 26, 10, 2.0, True), (96, 9, 6, 3.5, True), (150, 34, 14, 1.6, False),
         (206, 14, 8, 2.2, True), (232, 30, 12, 1.4, False))

# The canvas is the size of the screen, as the effects file turns it
WIDE, TALL = canvas.width, canvas.height

# The sizes above are in pixels of a 2.8 inch panel, and scale with a canvas pixel doubled
SCALE = min(1, min(WIDE, TALL) / 240)
CASE_WIDE, CASE_ROUND, LEAN = round(CASE_WIDE * SCALE), CASE_ROUND * SCALE, LEAN * SCALE
BANDS = tuple((across * SCALE, half * SCALE, round(feather * SCALE), levels, lit)
              for across, half, feather, levels, lit in BANDS)

pane = image(WIDE, TALL)
pane.antialias = image.X4


def poster(index):
    """Load one of the posters, read from the drive as it comes up, as a sequence reads its frames."""
    path = f"{POSTERS}/{POSTER_NAMES[index]}.png"
    try:
        return image.load(path)
    except (ValueError, OSError):
        raise RuntimeError(f"'{path}' is missing or corrupt! Check it is on the board") from None


def band(across, half, feather, levels, tone):
    """
    A diagonal band whose edges fade, as a stack of narrower bands over one another.

    Each band is translucent, so the middle, covered most often, comes out strongest.
    """
    passes = max(1, feather // 2)
    unit = max(4, round(levels * LEVEL / passes))
    pane.pen = tone.with_alpha(unit)
    for step in range(passes):
        reach = half - step * (feather / passes) / 2
        pane.shape(shape.custom([vec2(across - reach, 0), vec2(across + reach, 0),
                                 vec2(across + reach - LEAN, TALL), vec2(across - reach - LEAN, TALL)]))


def case():
    """Cut the window out of the case so the pane's light shows through, then lay the case on the pane."""
    frame = image(WIDE, TALL)
    frame.antialias = image.X4
    frame.pen = CASE
    frame.clear()

    frame.pen = brush.erase()
    frame.shape(shape.rounded_rectangle(CASE_WIDE, CASE_WIDE, WIDE - CASE_WIDE * 2,
                                        TALL - CASE_WIDE * 2, CASE_ROUND))
    pane.blit(frame, 0, 0)

    # The glass sits proud of the case, so its inside edge catches a little light
    pane.pen = CASE_LIT
    pane.shape(shape.rounded_rectangle(CASE_WIDE, CASE_WIDE, WIDE - CASE_WIDE * 2,
                                       TALL - CASE_WIDE * 2, CASE_ROUND).stroke(1))


# Create a light reflection across the glass, then the case laid over it
for across, half, feather, levels, lit in BANDS:
    band(across, half, feather, levels, SKY if lit else GLASS)
case()

shown = None                     # The poster up now


def draw():
    """Draw the poster due for the time the drawing has played, only when it changes."""
    global shown
    up = int(ticks // (DWELL * 1000)) % len(POSTER_NAMES)
    # Is this the poster the screen already shows?
    if up == shown:
        return False                # Nothing new, so no frame is sent

    # A poster and the pane over it, which is two blits
    picture = poster(up)
    if picture.width == WIDE and picture.height == TALL:
        canvas.blit(picture, 0, 0)
    else:
        # A canvas pixel doubled is smaller than the poster, so it is blitted to fit
        canvas.blit(picture, rect(0, 0, picture.width, picture.height), rect(0, 0, WIDE, TALL), image.BILINEAR)
    canvas.blit(pane, 0, 0)
    shown = up
