import sys

from mighty_fx import MightyFX, SPCE
from picovector import color, font, image, rect, shape
from screens import SCREEN_TYPES

"""
Fill the panel from a source a quarter of its size, doubling every pixel.

pixel_double= draws every source pixel as a two by two block, so an image half the panel's width
and half its height covers all of it, for a quarter of the memory and of the pixels to convert.

Three states go round, a full-size card, the small card at its own size, then the small card
doubled. The cost shows wherever the drawing is finer than a two pixel block.

Press "Boot" to exit the program.
"""

# Constants
ROTATION = 90            # Quarter turn, to suit how the screen is mounted
HOLD = 66                # Frames each state is held for, about three seconds
FACE_PATH = "/rom/fonts/Oswald.af"   # A vector face, so the lettering can be drawn at either size
INSET = 3                # Border to card edge, in small-source pixels
RING = 27                # Radius of the outlined circle, the curve doubling shows up in
CORE = 10                # And of the filled one inside it
SPOKES = 9               # Hairlines fanning from the corner, the diagonals it shows up in
CAPTION_SIZE = 13        # Smaller lettering is unreadable once doubled
CAPTION_LINE = 17        # Line pitch, with room for a descender

BACKGROUND = color.rgb(16, 20, 28)
BAND = color.rgb(52, 46, 38)          # Around the small card where it is shown at its own size
EDGE = color.rgb(64, 84, 104)
CURVE = color.rgb(96, 216, 208)
FAN = color.rgb(236, 176, 64)
TEXT_COLOUR = color.rgb(236, 240, 248)

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a, rotation=ROTATION)

# The quarter turn swaps the panel's sides, so this is the picture as it is mounted
PANEL_W, PANEL_H = screen.height, screen.width
CARD_W, CARD_H = PANEL_W // 2, PANEL_H // 2

# The small card that pixel_double is for, and the full-size one on the screen's canvas
small = image(CARD_W, CARD_H)
sharp = screen.canvas(PANEL_W, PANEL_H)
face = font.load(FACE_PATH)
for card in (small, sharp):
    card.antialias = image.X4
    card.font = face

print(f"a {CARD_W}x{CARD_H} card doubled onto {PANEL_W}x{PANEL_H},"
      f" {CARD_W * CARD_H * 4 // 1024}KB against {PANEL_W * PANEL_H * 4 // 1024}KB")


def draw_card(canvas, scale, size_line, setting_line):
    """Draw the card at either scale, every measurement multiplied so the two match on the panel."""
    canvas.pen = BACKGROUND
    canvas.clear()

    canvas.pen = EDGE
    canvas.shape(shape.rectangle(INSET * scale, INSET * scale,
                                 canvas.width - INSET * 2 * scale,
                                 canvas.height - INSET * 2 * scale).stroke(scale))

    # A circle is where doubling shows first, its edge having to step in twos
    middle_x, middle_y = canvas.width * 0.32, canvas.height * 0.36
    canvas.pen = CURVE
    canvas.shape(shape.circle(middle_x, middle_y, RING * scale).stroke(scale))
    canvas.shape(shape.circle(middle_x, middle_y, CORE * scale))

    # Hairlines from the far corner, at every angle but the ones a block can hold
    canvas.pen = FAN
    from_x, from_y = canvas.width - INSET * 3 * scale, INSET * 3 * scale
    for spoke in range(SPOKES):
        reach = (spoke + 1) / SPOKES
        canvas.shape(shape.line(from_x, from_y,
                                from_x - canvas.width * 0.5 * reach,
                                from_y + canvas.height * 0.52 * (1 - reach) + 6 * scale,
                                scale))

    # Lettering goes last, in rects taller than the type since text() clips a descender to its rect
    canvas.pen = TEXT_COLOUR
    wide = canvas.width - INSET * 4 * scale
    foot = canvas.height - (INSET * 2 + CAPTION_LINE * 2) * scale
    for line, words in enumerate((size_line, setting_line)):
        canvas.text(words, rect(INSET * 2 * scale, foot + line * CAPTION_LINE * scale,
                                wide, CAPTION_LINE * scale),
                    align=(image.CENTER, image.MIDDLE), font_size=CAPTION_SIZE * scale)


SHARP_LINES = (f"{PANEL_W}x{PANEL_H} source", "pixel_double=False")
SMALL_LINES = (f"{CARD_W}x{CARD_H} source", "pixel_double=False")
DOUBLED_LINES = (f"{CARD_W}x{CARD_H} source", "pixel_double=True")

# The full-size card never changes, so it is drawn once at twice the small card's scale
draw_card(sharp, 2, *SHARP_LINES)

state = -1
frames = 0

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Count frames, so every state has the same time on the panel. The small card is
        # redrawn only as its caption changes
        reached = frames // HOLD % 3
        if reached != state:
            state = reached
            if state == 1:
                draw_card(small, 1, *SMALL_LINES)
            elif state == 2:
                draw_card(small, 1, *DOUBLED_LINES)

        if state == 0:
            screen.update(sharp)
        elif state == 1:
            # At its own size and centred, which is the whole of what the source holds
            screen.update(small, bg_color=BAND)
        else:
            screen.update(small, pixel_double=True)
        frames += 1

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
