import random
import micropython
import spidisplay
from mighty_fx import MightyFX, SPCE
from timing import Pacer
from screens import Screen280

"""
Draw a fire, and light Mighty FX's RGB outputs with it, so whatever the outputs light flickers with
the flames as a room does round a fire.

The fire is a grid of heat. Hot spots flare at random along its bed, bunched towards the middle,
and at each step every cell takes the average of itself and the cells below it. A smooth field of
cooling rises with the heat and takes a little from each cell, so the flames burn out unevenly and
break into tongues, as in Hugo Elias's fire. Each output flickers with the hot spots flaring in its
share of the bed.

Press "Boot" to exit the program.
"""

# Constants for drawing
FRAME_RATE = 9                                      # Frames a second, which the board all but holds at STEPS steps a frame
STEPS = 3                                           # Rows the flames climb each frame, more for livelier flames
FLARES = 48                                         # Hot spots flaring along the fire's bed each step, more for taller flames
COOLING = 3                                         # The most heat the cooling takes from a cell each step, of 255
SMOOTHING = 4                                       # Passes smoothing the cooling, more for broader tongues
GLOW = (255, 96, 16)                                # The colour the outputs glow, a fire's orange
GLOW_FLOOR = 0.15                                   # How lit an output stays with no hot spot in its share of the bed

# The fire's colours as its heat rises from cold, mostly orange to yellow with a pale yellow only where hottest
STOPS = ((0.0, (0, 0, 0)), (0.28, (0, 0, 0)), (0.34, (170, 34, 0)), (0.45, (240, 110, 0)),
         (0.62, (255, 190, 40)), (0.85, (255, 240, 170)), (1.0, (255, 250, 210)))

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# Drawn landscape at half the panel's size and turned a quarter onto it at each update. pixel_double=
# shows each pixel as a block of four, which suits a fire's soft shapes and leaves fewer cells to calculate
canvas = screen.canvas(screen.height // 2, screen.width // 2)
WIDTH, HEIGHT = canvas.width, canvas.height
pixels = canvas.raw

# The fire burns on below the panel's bottom edge, so the hot spots flaring in its two lowest rows are
# out of sight and the flames come up into view already formed
BELOW = 4                                           # Rows of heat below the panel
BURNING = HEIGHT + BELOW - 2                        # Rows the heat rises through, all but the two the hot spots flare in
FOOT = BURNING * WIDTH                              # The first cell of those two rows

# The fire's bed, the columns the hot spots flare across, an eighth of the width in from either side
BED_LEFT, BED_WIDTH = WIDTH // 8, WIDTH * 3 // 4

# The heat, a byte a cell, claimed from the screens' SRAM as the canvas is. It and the cooling are read
# for every cell several times a frame, which runs much faster there than from the heap
heat = spidisplay.buffer(WIDTH * (HEIGHT + BELOW))
heat[:] = bytes(len(heat))


def colour_of(warmth):
    """Calculate the colour of a heat from 0 to 1, between the STOPS."""
    for (low, cold), (high, hot) in zip(STOPS, STOPS[1:]):
        if warmth <= high:
            part = (warmth - low) / (high - low)
            return tuple(round(a + (b - a) * part) for a, b in zip(cold, hot))
    return STOPS[-1][1]


# Every heat's colour calculated once, four bytes each as the canvas holds a pixel
palette = bytearray(channel for warmth in range(256) for channel in colour_of(warmth / 255) + (255,))


@micropython.viper
def smooth(values: ptr8, spare: ptr8, width: int, height: int):
    """Set every value to the average of itself and the eight round it, the field wrapping at its edges."""
    for y in range(height):
        for x in range(width):
            total = 0
            for down in range(3):
                row = (y + down - 1 + height) % height * width
                for across in range(3):
                    total += values[row + (x + across - 1 + width) % width]
            spare[y * width + x] = total // 9
    for cell in range(width * height):
        values[cell] = spare[cell]


# The cooling, a smooth random field as tall as the rows the heat rises through, scaled to 0 to COOLING.
# It wraps top to bottom, so it can scroll up with the heat for ever
field = bytearray(random.getrandbits(8) for _ in range(WIDTH * BURNING))
spare = bytearray(len(field))
for _ in range(SMOOTHING):
    smooth(field, spare, WIDTH, BURNING)
lowest, highest = min(field), max(field)
for cell in range(len(field)):
    field[cell] = (field[cell] - lowest) * COOLING // (highest - lowest)
cooling = spidisplay.buffer(len(field))
cooling[:] = field
del field, spare


@micropython.viper
def rise(cells: ptr8, width: int, height: int, cool: ptr8, scroll: int):
    """
    Set every cell to the average heat of itself and the four cells below it,
    less the cooling, scrolled up as far as the heat has risen.

    Each row takes the rows below it before they change, so the heat climbs a row each time. Compiled by
    viper, as this runs for every cell several times a frame.
    """
    # Find the highest hot cell. A row heats only from the two rows below it, so only the two over that cell can warm
    first = 0
    while first < height * width and cells[first] == 0:
        first += 1
    top = first // width - 2
    if top < 0:
        top = 0
    for y in range(top, height):
        row = y * width
        cool_row = (y + scroll) % height * width
        for x in range(1, width - 1):
            cell = row + x
            below = cell + width
            total = cells[cell] + cells[below] + cells[below + width] + cells[below - 1] + cells[below + 1]
            # Just under a fifth by a multiply and shift, which is quicker than viper's call out to divide
            cooled = (total * 13107 >> 16) - cool[cool_row + x]
            cells[cell] = cooled if cooled > 0 else 0


@micropython.viper
def paint(cells: ptr8, pixels: ptr32, count: int, colours: ptr32):
    """Colour every pixel by its cell's heat, each pixel written and palette entry read as one word."""
    for cell in range(count):
        pixels[cell] = colours[cells[cell]]


@micropython.viper
def flare(cells: ptr8, foot: int, width: int, low: int, span: int, count: int, generator: ptr32):
    """
    Flare count= hot spots at random in the fire's two bottom rows, cleared first, each three cells
    wide and within the span= columns from low=.

    Random numbers come from a linear congruential generator held in generator=, as viper calls the random module slowly.
    """
    for cell in range(foot, foot + 2 * width):
        cells[cell] = 0
    state = generator[0]
    for _ in range(count):
        # Average two draws, so the hot spots bunch towards the middle of the bed
        state = state * 1664525 + 1013904223
        first = (state >> 16 & 0xFFFF) % span
        state = state * 1664525 + 1013904223
        second = (state >> 16 & 0xFFFF) % span
        spot = foot + low + (first + second) // 2
        for row in range(2):
            cell = spot + row * width
            cells[cell - 1] = 255
            cells[cell] = 255
            cells[cell + 1] = 255
    generator[0] = state


# The random number generator's state, a word flare() reads and writes
generator = bytearray(random.getrandbits(8) for _ in range(4))
OUTPUTS = len(mighty.outputs)

# Each output's share of the bed, its first column and the one past its last
SHARES = [(BED_LEFT + output * BED_WIDTH // OUTPUTS, BED_LEFT + (output + 1) * BED_WIDTH // OUTPUTS)
          for output in range(OUTPUTS)]


def light_outputs():
    """
    Light each output from the hot spots flaring in its share of the bed.

    Fresh hot spots each step make the outputs flicker, and their bunching makes the middle ones brightest.
    """
    for (left, right), rgb in zip(SHARES, mighty.outputs):
        warmth = sum(heat[FOOT + left:FOOT + right]) / (right - left) / 255
        level = GLOW_FLOOR + (1 - GLOW_FLOOR) * warmth
        rgb.set_rgb(*(round(channel * level) for channel in GLOW))


scroll = 0                          # How many rows the cooling has scrolled up, wrapping at its height


def draw():
    """Draw one frame, the fire risen STEPS rows and coloured, and the outputs lit."""
    global scroll
    for _ in range(STEPS):
        flare(heat, FOOT, WIDTH, BED_LEFT, BED_WIDTH, FLARES, generator)
        rise(heat, WIDTH, BURNING, cooling, scroll)
        scroll = (scroll + 1) % BURNING
    paint(heat, pixels, WIDTH * HEIGHT, palette)
    light_outputs()


pacer = Pacer(fps=FRAME_RATE)       # The fire's clock, holding each frame to the rate

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        draw()
        screen.update(canvas, rotation=90, pixel_double=True)
        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
