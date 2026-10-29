import sys
from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import image, color, font

"""
Show which panel sits at each position of a screen hub. Every panel is painted its position's
colour, with its letter in the top left over one bar for A up to six for F. The console lists
the same for every position, including those where no panel answered.

Press "Boot" to exit the program.
"""

# Constants for drawing
MARGIN = 14             # The gap at the panel's left and top, under the letter and between one bar and the next
LETTER_SIZE = 240       # The size given to text() for the letter
BAR_WIDTH = 14          # The bars counting out the position, in panel pixels
BAR_HEIGHT = 44
VECTOR_FACE = "/rom/fonts/PoppinsBlack.af"
CAPITAL_TOP = 0.71      # Where this face's capitals start below the y given to text(), as a fraction of the size
CAPITAL_HEIGHT = 0.29   # And how tall they stand, the same way

# The gap this face leaves before each letter as a fraction of the size, taken off so it sits flush with the bars
LEFT_BEARINGS = {"A": 0.004, "B": 0.021, "C": 0.013, "D": 0.021, "E": 0.021, "F": 0.021}

# The letter's capitals start a margin down, and the bars a margin below them
LETTER_Y = MARGIN - CAPITAL_TOP * LETTER_SIZE
BARS_TOP = round(MARGIN + CAPITAL_HEIGHT * LETTER_SIZE + MARGIN)

# Each hub position's colour from A to F, with its name for the console
POSITION_COLOURS = (("red", color.rgb(255, 0, 0)),
                    ("green", color.rgb(0, 220, 0)),
                    ("blue", color.rgb(60, 110, 255)),
                    ("yellow", color.rgb(255, 200, 0)),
                    ("magenta", color.rgb(255, 0, 190)),
                    ("cyan", color.rgb(0, 220, 220)))

# Which screen is on every hub position, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object driving a screen hub, which takes SP/CE port B for extra chip selects
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.HUB_SELECTS)

# Build a screen on every hub port, holding None where no panel answers so the list follows the hub's positions
screens = []
for port in mighty.hub.ports:
    try:
        screens.append(ScreenType(port))
    except ValueError:
        screens.append(None)

panels = [screen for screen in screens if screen is not None]
if not panels:
    # Release the hub first, as one of its chip selects is a panel's backlight pin
    mighty.shutdown()
    raise RuntimeError("No panels answered! Check the hub is plugged into SP/CE A, with its panels on the hub rather than on the board")

print(f"{len(panels)} of {len(mighty.hub.ports)} hub positions answered\n")

# One canvas serves every panel, as they are all the same size
canvas = image(panels[0].width, panels[0].height)
canvas.antialias = image.X4
canvas.font = font.load(VECTOR_FACE)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    print("  Position  Colour    Bars")
    for position, screen in enumerate(screens):
        letter = "ABCDEF"[position]
        name, colour = POSITION_COLOURS[position]
        if screen is None:
            print(f"  {letter:<9} no panel")
            continue

        # Fill the canvas with this position's colour, then letter it and count it out in black bars
        canvas.pen = colour
        canvas.clear()
        canvas.pen = color.black
        canvas.text(letter, MARGIN - LEFT_BEARINGS[letter] * LETTER_SIZE, LETTER_Y, font_size=LETTER_SIZE)
        for bar in range(position + 1):
            canvas.rectangle(MARGIN + bar * (BAR_WIDTH + MARGIN), BARS_TOP, BAR_WIDTH, BAR_HEIGHT)

        screen.update(canvas)
        print(f"  {letter:<9} {name:<9} {position + 1}")

    # Nothing moves, so every panel holds its frame and this only waits
    while not mighty.boot_pressed():
        pass

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
