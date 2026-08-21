import sys
import time

from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import color, font, image, rect

"""
Scroll a line in every pixel font the board has in ROM, smallest first, with each one's height
beside its name.

A pixel font draws at the one size it was designed at, and that size is its height, so the
list is ordered by it and reads from the smallest face to the largest. dir(font) names them
all and font.<name> loads and caches each one.

The scroll runs to the end of the list and comes back rather than jumping to the start, so
every face passes the middle of the panel twice and nothing is missed at a wrap.

Press "Boot" to exit the program.
"""

# Constants
MARGIN = 10             # How far the text sits from the screen's left and top edges, in pixels
LINE_GAP = 2            # The gap between each line of text, in pixels
SCROLL_SPEED = 1.0      # How far the text scrolls each frame, in pixels
HOLD = 1.5              # Seconds the list rests at each end before turning round
LOUPE_TALL = 40         # How deep a patch of the panel's top left corner the box enlarges
LOUPE_ZOOM = 2          # And how much larger it is drawn
LOUPE_PAD = 3           # Between the enlargement and its border
TAG_FACE = "winds"      # The narrowest ROM pixel face, for the tag under the box

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a)

# Access the screen and create a canvas to draw to. canvas() places it in SRAM,
# which the screen converts from about twice as fast as the regular heap
canvas = screen.canvas()

# Every font in ROM, ordered by the size it draws at and then by name, so faces that share a
# height stay in a settled order
fonts = sorted(((name, getattr(font, name)) for name in dir(font)),
               key=lambda pair: (pair[1].height, pair[0]))

# Measure the whole list, so the scroll knows when it has run out
content_height = (MARGIN * 2) + sum(face.height + LINE_GAP for _, face in fonts)

# How far the list can travel before its last line is on the panel, and which way it is going
travel = max(0, content_height - screen.height)
scroll_y = 0.0
speed = -SCROLL_SPEED
moving_at = time.ticks_ms()     # When the list may move again, so each end gets its rest

print(f"{len(fonts)} faces, {fonts[0][1].height}px to {fonts[-1][1].height}px,"
      f" {content_height}px of list on a {screen.height}px panel")

# A pixel face has one size and no other, so the only way to look closer at one is to magnify
# the pixels it drew. The corner holds a copy of the panel's own top left corner, taken after
# the list is drawn and blitted back at LOUPE_ZOOM, which is why the source is copied out
# first: an image cannot be blitted over itself where the two overlap
tag_face = getattr(font, TAG_FACE)
TAG = f"top left corner at x{LOUPE_ZOOM}"

# The box is as wide as its own tag, and the patch it lifts is whatever that leaves at this
# magnification, so the two always agree however the tag is worded
asker = image(8, 8)
asker.font = tag_face
LOUPE_BOX = rect(0, 0, round(asker.measure_text(TAG)[0]),
                 LOUPE_TALL * LOUPE_ZOOM + LOUPE_PAD * 2)
LOUPE_BOX.x = canvas.width - LOUPE_BOX.w - 1

LOUPE_WIDE = round((LOUPE_BOX.w - LOUPE_PAD * 2) / LOUPE_ZOOM)   # A rect reports floats
LOUPE_SOURCE = rect(0, 0, LOUPE_WIDE, LOUPE_TALL)
lifted = image(LOUPE_WIDE, LOUPE_TALL)
LOUPE_INSIDE = rect(LOUPE_BOX.x + LOUPE_PAD, LOUPE_BOX.y + LOUPE_PAD,
                    LOUPE_WIDE * LOUPE_ZOOM, LOUPE_TALL * LOUPE_ZOOM)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():

        # Clear the canvas to navy, and draw in white
        canvas.pen = color.navy
        canvas.clear()
        canvas.pen = color.white

        # Draw a line in each font, spacing them out by their own glyph heights
        y = MARGIN + int(scroll_y)
        for name, face in fonts:
            canvas.font = face
            canvas.text(f"{name} {face.height}px", MARGIN, y)
            y += face.height + LINE_GAP

        # Turn round at each end rather than jumping back to the start, resting there first
        # so the faces at the top and bottom of the list can be read
        if travel and time.ticks_diff(time.ticks_ms(), moving_at) >= 0:
            scroll_y += speed
            if scroll_y <= -travel or scroll_y >= 0:
                scroll_y = max(-travel, min(0.0, scroll_y))
                speed = -speed
                moving_at = time.ticks_add(time.ticks_ms(), int(HOLD * 1000))

        # The corner enlargement, over the list rather than in place of it: the faces below
        # stay at the size they draw at, and this only says what the smallest ones look like
        lifted.blit(canvas, LOUPE_SOURCE, rect(0, 0, LOUPE_WIDE, LOUPE_TALL))

        canvas.pen = color.white
        canvas.rectangle(LOUPE_BOX.x, LOUPE_BOX.y, LOUPE_BOX.w, LOUPE_BOX.h)
        canvas.blit(lifted, rect(0, 0, LOUPE_WIDE, LOUPE_TALL), LOUPE_INSIDE)

        # Said in words under the box, since the corner otherwise reads as a second list drawn
        # in larger faces rather than as the same corner seen closer
        canvas.font = tag_face
        canvas.pen = color.white
        canvas.text(TAG, LOUPE_BOX.x, LOUPE_BOX.y + LOUPE_BOX.h + 1)

        # Update the screen with the latest canvas
        screen.update(canvas)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
