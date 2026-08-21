import sys

from mighty_fx import MightyFX, SPCE
from picovector import color, font, image, shape
from screens import SCREEN_TYPES, Reserve, ScreenPair

"""
Turn a test card on each panel of a pair, the second one mirrored against the first.

Every placement setting a screen takes, a pair takes one of per screen, so mirror=(False,
True) is one call that leaves one panel as drawn and flips the other. Set the panels beside
each other and the pair reads as a thing and its reflection, which is what a screen seen
through a mirror or from behind a window needs; MIRRORED = False gives both the same instead,
and nothing else in the file changes.

The cards are the shipped test cards, and each panel takes its own. They are 320 square where
the panel is 240 by 320, so every turn keeps a different part of one: upright it loses the paw
patterns down the sides, turned a quarter it loses the colour bars along the ends. A source is
not obliged to be the panel's shape or the panel's size, and nothing here is letterboxed.

The caption is drawn onto a copy of each card, so the assets are untouched and the caption
turns and flips with the picture it is on. On the mirrored panel it reads backwards, which is
the plainest proof the setting reached that panel and not the other.

Two full-size sources out of the heap at once is the one case that cannot keep up otherwise,
so both screens are built with Reserve.FULL_SIZE_IMAGES. A pair needs the same reserve on
both, a reservation being shared out across it.

Press "Boot" to exit the program.
"""

# Constants
FIRST_CARD = "/examples/assets/gold_macaw_card.png"
SECOND_CARD = "/examples/assets/red_macaw_card.png"
MIRRORED = True          # Whether the second panel mirrors the first, or matches it
HOLD = 44                # Frames each turn is held for, a little under two seconds
CAPTION_FACE = "winds"   # The narrowest ROM pixel face, so the plate can be small
PLATE_TALL = 16          # The plate the caption sits on
PLATE_PAD = 5            # And how far it reaches past the lettering
PLATE_UP = 26            # How far the plate sits above the foot of the uncropped square

PLATE = color.rgb(16, 18, 24)
CAPTION = color.rgb(240, 242, 248)
TURNS = (0, 90, 180, 270)

# Which screens are on the ports, "2.8" or "1.54", or what the effects file passes in args.
# A pair wants two of the same size, each panel holding its own card
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with both SP/CE ports set up for screens, and a panel on each
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# A pair holds both panels to one refresh rate and keeps their scans together
pair = ScreenPair(ScreenType(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES),
                  ScreenType(mighty.spce_b, reserve=Reserve.FULL_SIZE_IMAGES))
first, second = pair.screens

try:
    cards = [image.load(FIRST_CARD), image.load(SECOND_CARD)]
except (ValueError, OSError):
    raise RuntimeError(f"'{FIRST_CARD}' or '{SECOND_CARD}' is missing or corrupt!"
                       " Check both are valid PNGs") from None

# A copy of each to caption, since the caption changes and the cards must not. The heap is
# the place for them: they are only converted, never drawn to again, and one is larger than
# the SRAM canvas region holds anyway
caption_face = getattr(font, CAPTION_FACE)
shown = []
for card in cards:
    copy = image(card.width, card.height)
    copy.font = caption_face
    shown.append(copy)

# The square that no turn crops is the panel's short side, and the caption belongs inside it.
# What lies outside is what each turn keeps or loses
SAFE = min(first.width, first.height)
EDGE_Y = (cards[0].height - SAFE) // 2

print(f"a pair of {cards[0].width}x{cards[0].height} cards on {first.width}x{first.height}"
      f" panels, the second {'mirrored' if MIRRORED else 'matching the first'}")


def draw_card(copy, card, rotation, mirror):
    """One card with the settings its own panel is about to show it under written across it."""
    copy.blit(card, 0, 0)

    caption = f"rotation={rotation} mirror={mirror}"
    wide = copy.measure_text(caption)[0]
    middle = card.width / 2
    foot = EDGE_Y + SAFE - PLATE_UP

    copy.pen = PLATE
    copy.shape(shape.rectangle(middle - wide / 2 - PLATE_PAD, foot,
                               wide + PLATE_PAD * 2, PLATE_TALL))

    # A pixel face draws down from the y it is given, so the lettering is centred on the
    # plate by the difference between the two heights
    copy.pen = CAPTION
    copy.text(caption, middle - wide / 2, foot + (PLATE_TALL - caption_face.height) / 2)


step = -1
frames = 0
rotation = TURNS[0]

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        reached = frames // HOLD % len(TURNS)
        if reached != step:
            step = reached
            rotation = TURNS[step]
            draw_card(shown[0], cards[0], rotation, False)
            draw_card(shown[1], cards[1], rotation, MIRRORED)

        # Two images and one setting per screen, in a single call
        pair.update(shown[0], shown[1], rotation=rotation, mirror=(False, MIRRORED))
        frames += 1

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
