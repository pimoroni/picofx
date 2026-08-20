# Shows a folder of posters as if each were in a case behind glass, laid over the picture as it goes.
#
# This is what a canvas is for. A poster sent straight to the panel is what the file says and nothing more;
# drawn into a canvas first, anything can go over it, and here that is a case around the edge and light across
# the glass. The poster changes and the case does not, which is what makes it read as a case rather than as
# part of the art.
#
# The pane is the same for every poster, so it is drawn once into an image of its own and blitted over each
# one. That is the difference between a startup cost and a per poster one: it is some thirty antialiased
# polygons. Laying it over in one pass gives the same pixels as drawing it on top would, source-over
# compositing being associative, and costs a blit.
#
# An image starts empty, so the pane needs no cutout: what is not drawn stays transparent and the poster shows
# through. There is no cutout to be had in any case, checked both ways round under both fill rules, since
# shapes() draws each shape on its own and the rule does not span them.
#
# Two things about drawing over a picture on this panel, and they are the transferable part:
#
#   A level is 17 of 255. The panel resolves 16 levels a channel, so anything fainter than one of them is not
#   there at all: a wash at alpha 26 over a bright poster moves it by five and disappears.
#
#   Opaque marks read over any art, translucent ones only over art that is flat or dark. The case is opaque and
#   always reads; the glass is a wash, so it shows on the dark posters while the busy bright ones swallow it.
#   Darkening a bright poster to rescue it only makes a murkier poster, which is why nothing here does.

import math
import time

from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280
from picovector import color, image, rect, shape, vec2

# Constants
POSTERS = "/examples/assets/billboards/portrait"   # Shared with the billboard showcases
ROTATION = 0                     # Portrait, which is the shape these posters are
DWELL = 3.0                      # Seconds a poster is up for
LEVEL = 17                       # One of the panel's 16 levels a channel, which is the least that shows
CASE_WIDE = 4                    # How far the case reaches over the poster
CASE_ROUND = 10                  # The window's corner, which is what hides the poster's square one
GLASS = color.rgb(28, 44, 66)    # What a sheet of glass takes out of what is behind it
SKY = color.rgb(225, 242, 255)   # And what it gives back
CASE = color.rgb(150, 150, 150)
CASE_LIT = color.rgb(215, 220, 230)  # Four levels above the case, so the lit edge reads as one
LEAN = 150                       # How far a band slides over the poster's height, which sets its angle

# Each band: where its middle sits, its half width, how far its edges ramp, how strong its middle is, and
# whether it is the window reflected or the room. Both are wanted, light being unable to lighten a pale poster
BANDS = ((30, 26, 10, 2.0, True), (96, 9, 6, 3.5, True), (150, 34, 14, 1.6, False),
         (206, 14, 8, 2.2, True), (232, 30, 12, 1.4, False))

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)
canvas = screen.canvas(screen.width, screen.height)
WIDE, TALL = canvas.width, canvas.height

# The pane lives in the heap, the screen's fast region holding the canvas
pane = image(WIDE, TALL)
pane.antialias = image.X4

# fps names the rate, the filenames carrying no delays of their own
player = SequencePlayer(POSTERS, fps=1 / DWELL)
print(f"{player.frames} posters, {DWELL}s each")


def band(across, half, feather, levels, tone):
    """A diagonal band whose edges fade, as a stack of narrower bands over one another.

    There is no gradient fill, so the ramp comes from covering the middle more times than the edges.
    """
    passes = max(1, feather // 2)
    unit = max(4, round(levels * LEVEL / passes))
    pane.pen = tone.with_alpha(unit)
    for step in range(passes):
        reach = half - step * (feather / passes) / 2
        pane.shape(shape.custom([vec2(across - reach, 0), vec2(across + reach, 0),
                                 vec2(across + reach - LEAN, TALL), vec2(across - reach - LEAN, TALL)]))


def case():
    """Everything outside a rounded window: four bars, then each corner less its quarter circle.

    A thick stroked rounded rectangle will not do it. Its outer edge is rounded too, so the panel's own corners
    are left bare, and a square big enough to cover those reaches into the window.
    """
    pane.pen = CASE
    pane.rectangle(0, 0, WIDE, CASE_WIDE)
    pane.rectangle(0, TALL - CASE_WIDE, WIDE, CASE_WIDE)
    pane.rectangle(0, 0, CASE_WIDE, TALL)
    pane.rectangle(WIDE - CASE_WIDE, 0, CASE_WIDE, TALL)

    for across, down, out_x, out_y in ((CASE_WIDE, CASE_WIDE, -1, -1),
                                       (WIDE - CASE_WIDE, CASE_WIDE, 1, -1),
                                       (CASE_WIDE, TALL - CASE_WIDE, -1, 1),
                                       (WIDE - CASE_WIDE, TALL - CASE_WIDE, 1, 1)):
        middle = (across - out_x * CASE_ROUND, down - out_y * CASE_ROUND)
        points = [vec2(across, down)]
        for step in range(9):
            angle = step / 8 * math.pi / 2
            points.append(vec2(middle[0] + out_x * CASE_ROUND * math.cos(angle),
                               middle[1] + out_y * CASE_ROUND * math.sin(angle)))

        pane.shape(shape.custom(points))

    # The glass sits proud of the case, so its inside edge catches a little light
    pane.pen = CASE_LIT
    pane.shape(shape.rounded_rectangle(CASE_WIDE, CASE_WIDE, WIDE - CASE_WIDE * 2,
                                       TALL - CASE_WIDE * 2, CASE_ROUND).stroke(1))


marked = time.ticks_ms()
for across, half, feather, levels, lit in BANDS:
    band(across, half, feather, levels, SKY if lit else GLASS)

case()
print(f"the pane drawn once in {time.ticks_diff(time.ticks_ms(), marked)}ms")

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # A poster and the pane over it, which is two blits
        if player.has_advanced():
            marked = time.ticks_ms()
            poster = player.image
            canvas.blit(poster, rect(0, 0, poster.width, poster.height), rect(0, 0, WIDE, TALL))
            canvas.blit(pane, 0, 0)
            laid = time.ticks_diff(time.ticks_ms(), marked)
            screen.update(canvas, rotation=ROTATION)
            print(f"poster {player.frame} laid under the pane in {laid}ms")

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
