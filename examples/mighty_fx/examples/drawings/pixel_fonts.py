from picovector import color, font, image, rect

"""
Drawing: Pixel fonts
A line in every ROM pixel font, smallest first, scrolling, with each one's height beside its name.
Section: Drawing from code
"""

# Entry: screenA: graphics file=pixel_fonts.py

# Constants
MARGIN = 10
LINE_GAP = 2
SCROLL_SPEED = 1.0
HOLD_MS = 1500
LOUPE_TALL = 40
LOUPE_ZOOM = 2
LOUPE_PAD = 3
TAG_FACE = font.winds

fonts = sorted(((name, getattr(font, name)) for name in dir(font)),
               key=lambda pair: (pair[1].height, pair[0]))
content_height = (MARGIN * 2) + sum(face.height + LINE_GAP for _, face in fonts)

TAG = f"top left corner at x{LOUPE_ZOOM}"
ruler = image(8, 8)
ruler.font = TAG_FACE
TAG_WIDE = round(ruler.measure_text(TAG)[0])
del ruler

LOUPE_WIDE = round((TAG_WIDE - LOUPE_PAD * 2) / LOUPE_ZOOM)
LOUPE_SOURCE = rect(0, 0, LOUPE_WIDE, LOUPE_TALL)
lifted = image(LOUPE_WIDE, LOUPE_TALL)

# Placed on the first call, from the canvas's size
travel = 0
LOUPE_BOX = LOUPE_INSIDE = None
scroll_y = 0.0
speed = -SCROLL_SPEED
due = 0                 # When the list may move again, in elapsed ms


def draw(canvas, elapsed):
    global travel, LOUPE_BOX, LOUPE_INSIDE, scroll_y, speed, due
    now = elapsed * 1000
    if LOUPE_BOX is None:
        travel = max(0, content_height - canvas.height)
        LOUPE_BOX = rect(canvas.width - TAG_WIDE - 1, 0, TAG_WIDE, LOUPE_TALL * LOUPE_ZOOM + LOUPE_PAD * 2)
        LOUPE_INSIDE = rect(LOUPE_BOX.x + LOUPE_PAD, LOUPE_BOX.y + LOUPE_PAD,
                            LOUPE_WIDE * LOUPE_ZOOM, LOUPE_TALL * LOUPE_ZOOM)

    canvas.pen = color.navy
    canvas.clear()
    canvas.pen = color.white

    y = MARGIN + int(scroll_y)
    for name, face in fonts:
        canvas.font = face
        canvas.text(f"{name} {face.height}px", MARGIN, y)
        y += face.height + LINE_GAP

    if travel and now >= due:
        scroll_y += speed
        if scroll_y <= -travel or scroll_y >= 0:
            scroll_y = max(-travel, min(0.0, scroll_y))
            speed = -speed
            due = now + HOLD_MS

    lifted.blit(canvas, LOUPE_SOURCE, LOUPE_SOURCE)
    canvas.pen = color.white
    canvas.rectangle(LOUPE_BOX.x, LOUPE_BOX.y, LOUPE_BOX.w, LOUPE_BOX.h)
    canvas.blit(lifted, LOUPE_SOURCE, LOUPE_INSIDE)

    canvas.font = TAG_FACE
    canvas.text(TAG, LOUPE_BOX.x, LOUPE_BOX.y + LOUPE_BOX.h + 1)
