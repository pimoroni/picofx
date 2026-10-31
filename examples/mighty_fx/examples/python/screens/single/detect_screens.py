import sys
from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import image, color, font

"""
Show which screen sits on each SP/CE port. Every screen is painted its port's colour, with its
letter in the top left over one bar for A or two for B. The console lists the same for both
ports, including one where no screen answered.

Press "Boot" to exit the program.

Args: Screen A size, Screen B size
"""

# Constants for drawing
MARGIN = 14             # The gap at the screen's left and top, under the letter and between one bar and the next
LETTER_SIZE = 240       # The size given to text() for the letter
BAR_WIDTH = 14          # The bars counting out the port, in screen pixels
BAR_HEIGHT = 44
VECTOR_FACE = "/rom/fonts/PoppinsBlack.af"
CAPITAL_TOP = 0.71      # Where this face's capitals start below the y given to text(), as a fraction of the size
CAPITAL_HEIGHT = 0.29   # And how tall they stand, the same way

# The gap this face leaves before each letter as a fraction of the size, taken off so it sits flush with the bars
LEFT_BEARINGS = {"A": 0.004, "B": 0.021}

# The letter's capitals start a margin down, and the bars a margin below them
LETTER_Y = MARGIN - CAPITAL_TOP * LETTER_SIZE
BARS_TOP = round(MARGIN + CAPITAL_HEIGHT * LETTER_SIZE + MARGIN)

# Each port's colour, A then B, with its name for the console
PORT_COLOURS = (("red", color.rgb(255, 0, 0)),
                ("green", color.rgb(0, 220, 0)))

# Which screen is on each port, "2.8" or "1.54". The effects file can pass one for both
# ports, or one each, the ports being free to differ where a pair is not
SCREEN_SIZES = ("2.8", "2.8") if not sys.argv[1:] else (sys.argv[1], sys.argv[-1])

# Create a MightyFX object with both SP/CE ports set up for screens
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# Build a screen on each port, holding None where no screen answers so the list follows the ports
screens = []
for port, size in zip((mighty.spce_a, mighty.spce_b), SCREEN_SIZES):
    try:
        screens.append(SCREEN_TYPES[size](port))
    except ValueError:
        screens.append(None)

if not any(screens):
    mighty.shutdown()
    raise RuntimeError("No screens answered! Check one is plugged into SP/CE A or B")

face = font.load(VECTOR_FACE)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    print("  Port      Colour    Bars")
    for position, screen in enumerate(screens):
        letter = "AB"[position]
        name, colour = PORT_COLOURS[position]
        if screen is None:
            print(f"  {letter:<9} no screen")
            continue

        # A canvas each, as the two screens may differ in size
        canvas = image(screen.width, screen.height)
        canvas.antialias = image.X4
        canvas.font = face

        # Fill the canvas with this port's colour, then letter it and count it out in black bars
        canvas.pen = colour
        canvas.clear()
        canvas.pen = color.black
        canvas.text(letter, MARGIN - LEFT_BEARINGS[letter] * LETTER_SIZE, LETTER_Y, font_size=LETTER_SIZE)
        for bar in range(position + 1):
            canvas.rectangle(MARGIN + bar * (BAR_WIDTH + MARGIN), BARS_TOP, BAR_WIDTH, BAR_HEIGHT)

        screen.update(canvas)
        print(f"  {letter:<9} {name:<9} {position + 1}")

    # Nothing moves, so every screen holds its frame and this only waits
    while not mighty.boot_pressed():
        pass

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
