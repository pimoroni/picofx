import sys

from mighty_fx import MightyFX, SPCE
from timing import Roller
from screens import SCREEN_TYPES
from picovector import color, font, image, rect

"""
Scroll a line in every ROM pixel font, smallest first, with each one's height beside its name.

A pixel font draws only at its designed size. dir(font) names every face and font.<name> loads one.

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
TAG_FACE = font.winds   # The narrowest ROM pixel face, for the tag under the box

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a)

# Create a canvas to draw to
canvas = screen.canvas()

# Every font in ROM, ordered by height and then name
fonts = sorted(((name, getattr(font, name)) for name in dir(font)),
               key=lambda pair: (pair[1].height, pair[0]))

# Measure the whole list, so the scroll knows when it has run out
content_height = (MARGIN * 2) + sum(face.height + LINE_GAP for _, face in fonts)

# How far the list can travel before its last line is on the panel, and which way it is going
travel = max(0, content_height - screen.height)
scroll_y = 0.0
speed = -SCROLL_SPEED
resting = Roller()              # When the list may move again, so each end gets its rest

print(f"{len(fonts)} faces, {fonts[0][1].height}px to {fonts[-1][1].height}px,"
      f" {content_height}px of list on a {screen.height}px panel")

# A box magnifies a copy of the panel's top left, as a pixel face cannot be drawn larger. An image
# cannot be blitted over itself, hence the copy
TAG = f"top left corner at x{LOUPE_ZOOM}"

# The box is as wide as its tag, and lifts what that width holds at LOUPE_ZOOM
canvas.font = TAG_FACE
LOUPE_BOX = rect(0, 0, round(canvas.measure_text(TAG)[0]),
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

        # Turn round at each end after a rest, so the first and last faces can be read
        if travel and resting.is_due():
            scroll_y += speed
            if scroll_y <= -travel or scroll_y >= 0:
                scroll_y = max(-travel, min(0.0, scroll_y))
                speed = -speed
                resting.restart(HOLD)

        # Enlarge the top left corner into the box
        lifted.blit(canvas, LOUPE_SOURCE, LOUPE_SOURCE)

        canvas.pen = color.white
        canvas.rectangle(LOUPE_BOX.x, LOUPE_BOX.y, LOUPE_BOX.w, LOUPE_BOX.h)
        canvas.blit(lifted, LOUPE_SOURCE, LOUPE_INSIDE)

        # Tag the box, or it reads as a second list in larger faces
        canvas.font = TAG_FACE
        canvas.text(TAG, LOUPE_BOX.x, LOUPE_BOX.y + LOUPE_BOX.h + 1)

        # Update the screen with the latest canvas
        screen.update(canvas)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
