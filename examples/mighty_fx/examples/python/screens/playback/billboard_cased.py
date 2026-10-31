import time

from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280
from picovector import brush, color, image, shape, vec2

"""
Show a folder of posters as if each stood in a case behind glass.

A canvas lets a case and light across the glass go over the poster, and only the poster changes.

The pane is drawn once into an image of its own and blitted over each poster, its window cut with
brush.erase(). The case is opaque, as a translucent one reads only over flat or dark art.

Press "Boot" to exit the program.
"""

# Constants
POSTERS = "/examples/assets/billboards/portrait"   # Shared with the billboard showcases
ROTATION = 0                     # Portrait, which is the shape these posters are
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

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a, rotation=ROTATION)
canvas = screen.canvas()
WIDE, TALL = canvas.width, canvas.height

pane = image(WIDE, TALL)
pane.antialias = image.X4

# fps names the rate, the filenames carrying no delays of their own
try:
    player = SequencePlayer(POSTERS, fps=1 / DWELL)
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{POSTERS}' is missing! Check it is on the board") from None

print(f"{player.frames} posters, {DWELL}s each")


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
    """Cut the case's window away from the pane so its light survives, then lay the case on it."""
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
            canvas.blit(player.image, 0, 0)
            canvas.blit(pane, 0, 0)
            laid = time.ticks_diff(time.ticks_ms(), marked)
            screen.update(canvas)
            print(f"poster {player.frame} laid under the pane in {laid}ms")

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
