import math
import random
import spidisplay
from picovector import color, font, image, mat3, rect, shape

"""
A number drum for the hub clock, set in a brass plate, rolling on to its next digit when it changes.
A colon is a pair of black rivets in the plate beside the drum. showcase/odometer.py is the fuller
version, and draws the drum the same way.

Each place has a drum carrying the digits it needs in the order they come round, so every change is
one step forward. The two hour drums turn together, a position an hour, as one wheel would.
"""

DIGIT_FONT = "/rom/fonts/Oswald.af"
ANTIALIAS = image.X4
CHANGE_STEPS = 3                    # Frames through a roll of one digit
COLON_BLINKS = False                # The rivets are fixed in the plate, so the colon never goes out
WRITE_BUDGET = None                 # Every frame of a roll shows, however long a wrap's cascade takes

# What each drum carries, by what it shows. A drum with more positions is larger round, so its digits
# stay the size of the others and it curves away less
SEQUENCES = {
    "units": "0123456789",
    "tens": "012345" * 2,           # Twice round, so it is near the units drum's size
    "hour tens": "0" * 10 + "1" * 10 + "2" * 4,
    "hour units": "0123456789" * 2 + "0123",
}

VIEW = 27                           # How far round the units drum shows above and below its middle, in degrees
DIGIT_FILL = 0.7                    # How much of a digit's place on the drum its lettering fills
SIDE = 24                           # Panel pixels from the opening to the panel's side, where a colon goes
END = 36                            # And from the opening to the panel's top and bottom, where the screws go

# The screens drive the panel at 12 bit, 16 levels a channel in steps of 17, so the colours below sit
# on those levels
FACE = (221, 221, 204)              # The drum's face
DIGIT = color.rgb(17, 17, 17)       # And the digits printed on it
INSIDE = color.rgb(17, 17, 17)      # The dark inside the opening, round the drum
DRUM_FALLOFF = 0.7                  # How dark the units drum gets at the top and bottom of what shows, 1 being black

# The brass plate
BRASS = color.rgb(170, 136, 68)
BRIGHTER = color.rgb(221, 187, 119).with_alpha(30)  # A brush mark catching the light, faint so the brass reads as metal
DARKER = color.rgb(119, 85, 34).with_alpha(30)      # And one in shadow
STREAKS = 4                         # Brush marks a row of the brass carries
EDGE_LIT = color.rgb(238, 204, 136) # An edge facing up and to the left, the light being above
EDGE_SHADED = color.rgb(68, 51, 17) # And one facing away from it
OPENING_PAD = 6                     # Panel pixels between the drum and the opening's edge
CORNER = 6                          # How far the opening's corners are rounded
SCREW = 9                           # A screw head's radius, in panel pixels
SCREW_INSET = 16                    # From the panel's edge to a screw's middle
SCREW_RIM = color.rgb(238, 238, 238)  # The steel head's edge, catching the light
SCREW_HEAD = color.rgb(153, 153, 170) # And its dome
SCREW_SLOT = color.rgb(51, 51, 51)
SLOTS = (30, 110, 165, 75)          # Each screw's slot, in degrees, tightened by hand so no two alike
RIVET = 6                           # A colon rivet's radius
RIVET_RIM = color.rgb(85, 85, 85)   # Its black head's edge, catching the light
RIVET_HEAD = color.rgb(17, 17, 17)  # And its dome, dark to stand out against the brass

# Made by prepare() for the panel's size, and kept
strip = None                        # The ten digits drawn flat, one above the next, that every drum reads from
shade = None                        # The darkening over a drum, the same on every drum
drum = None                         # Where a drum is put together before it goes into a frame
drums = {}                          # Each drum's digits as rows of the strip, its rows, length round and repeat
plates = {}                         # The plate with the opening cut, by whether it carries the colon's rivets
plated = {}                         # Which plate each frame already holds, by the frame's id
drum_w = drum_h = left = top = cell_h = 0
source = rect(0, 0, 0, 1)
target = rect(0, 0, 0, 1)
colon_area = rect(0, 0, 0, 0)       # Where the rivets sit on the plate


def shows(reading, place):
    """Find the drum a place of HHMMSS takes and its position, the hour drums both going by the hour."""
    if place < 2:
        return ("hour tens" if place == 0 else "hour units", int(reading[:2]))
    return ("tens" if place % 2 == 0 else "units", int(reading[place]))


def change_steps(previous, showing):
    """
    Count the frames through a roll, CHANGE_STEPS where it is one position. A longer roll, as from the
    lamp test, takes a frame a position, as every panel's frames share the hub's wire.
    """
    positions = (showing[1] - previous[1]) % drums[showing[0]][3]
    return CHANGE_STEPS if positions == 1 else positions


def digit_rows(face, size):
    """Measure the first and last rows a digit fills below the y it is drawn at, a row counting where half covered."""
    probe = image(round(size) * 2, round(size) * 2)
    probe.raw[:] = bytes(len(probe.raw))
    probe.font = face
    probe.antialias = ANTIALIAS
    probe.pen = color.white
    probe.text("0", 0, 0, size)

    # The lettering is white, so a covered pixel's colour bytes are as high as its alpha
    raw, stride = probe.raw, probe.stride
    filled = [y for y in range(probe.height) if max(raw[y * stride:(y + 1) * stride]) >= 128]
    return filled[0], filled[-1]


def brushed(width, height):
    """Draw the brass plate, brush marks running along the rows a few to each, seeded so it is the same every time."""
    plate = image(width, height)
    plate.pen = BRASS
    plate.clear()
    random.seed(1)
    for y in range(height):
        for _ in range(STREAKS):
            plate.pen = BRIGHTER if random.getrandbits(1) else DARKER
            # A mark can start up to its own length off the left edge, so the marks are as dense there
            length = random.randrange(20, 120)
            plate.hspan(random.randrange(-length, width), y, length)
    return plate


def dome(plate, x, y, radius, rim, head):
    """Draw a domed head on the plate, casting a shadow on the brass."""
    plate.pen = EDGE_SHADED
    plate.shape(shape.circle(x + 1, y + 1, radius))
    plate.pen = rim
    plate.shape(shape.circle(x, y, radius))
    plate.pen = head
    plate.shape(shape.circle(x + 0.5, y + 0.5, radius - 1))


def shaded():
    """
    Make the shade over a drum, darkening as the units drum turns away from the panel and leaving its
    middle row the brightest. Every drum takes it, so they all read alike whatever their size round.

    A row's brightness falls between two of the panel's levels, so its pixels are spread between both in
    a fixed 4x4 pattern, an ordered dither, where one level to a row would show as bands. The pattern
    repeats every four pixels, so a row is four pixels of black written out across the drum, each with
    just enough alpha to bring the face down to its level.
    """
    dither = (0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5)
    shade = image(drum_w, drum_h)
    shade.raw[:] = bytes(len(shade.raw))
    raw, stride = memoryview(shade.raw), shade.stride
    radius = drum_h / 2 / math.sin(math.radians(VIEW))
    for row in range(drum_h):
        angle = math.asin((row + 0.5 - drum_h / 2) / radius)
        darkened = DRUM_FALLOFF * (1 - math.cos(angle)) / (1 - math.cos(math.radians(VIEW)))
        brightness = FACE[0] * (1 - darkened)
        below = int(brightness // 17) * 17
        pattern = bytearray(16)
        for x in range(4):
            level = below + 17 if (dither[row % 4 * 4 + x] + 0.5) / 16 < (brightness - below) / 17 else below
            pattern[x * 4 + 3] = max(0, round(255 * (1 - level / FACE[0])))
        # Written through a view of the row alone, as a slice assignment moves everything after the slice
        # even where its length is unchanged
        raw[row * stride:row * stride + drum_w * 4][:] = (bytes(pattern) * (drum_w // 4 + 1))[:drum_w * 4]
    return shade


def prepare(width, height):
    """Build the strip, each drum and the plate, sized to fill a panel this size."""
    global strip, shade, drum, drum_w, drum_h, left, top, cell_h
    drum_w = width - (SIDE + OPENING_PAD) * 2
    drum_h = height - (END + OPENING_PAD) * 2
    left, top = (width - drum_w) // 2, (height - drum_h) // 2
    source.w = target.w = drum_w

    # A digit's place on a drum is set by the units drum, its radius following from how much of it shows
    cell_h = round(2 * math.pi * drum_h / 2 / math.sin(math.radians(VIEW)) / 10)

    # The digits are sized on their drawn height, a face's size being its em box, measured once and scaled
    face = font.load(DIGIT_FONT)
    first, last = digit_rows(face, 100)
    size = 100 * cell_h * DIGIT_FILL / (last - first + 1)
    ink_top, ink_bottom = first * size / 100, (last + 1) * size / 100 - 1
    strip = image(drum_w, cell_h * 10)
    strip.antialias = ANTIALIAS
    strip.pen = color.rgb(*FACE)
    strip.clear()
    strip.font = face
    strip.pen = DIGIT
    for digit in range(10):
        wide = strip.measure_text(str(digit), font_size=size)[0]
        y = digit * cell_h + (cell_h - (ink_bottom - ink_top + 1)) / 2 - ink_top
        strip.text(str(digit), (drum_w - wide) / 2, y, size)

    # A row at a distance from a drum's middle sees it at the angle whose sine is that distance over the
    # radius, and looks at the strip that far round. Drums the same size round share their rows
    made = {}
    for name, sequence in SEQUENCES.items():
        length = len(sequence) * cell_h
        if length not in made:
            radius = length / 2 / math.pi
            made[length] = [round(radius * math.asin((row + 0.5 - drum_h / 2) / radius)) for row in range(drum_h)]
        # A drum carrying its digits twice round comes back to the same look halfway
        repeat = min(step for step in range(1, len(sequence) + 1) if sequence[step:] + sequence[:step] == sequence)
        drums[name] = ([int(digit) * cell_h for digit in sequence], made[length], length, repeat)
    shade = shaded()

    # The drum is put together in SRAM, where blits run faster than in the frames in PSRAM, and goes
    # into a frame in one blit. In PSRAM where the panels leave SRAM no room for it
    try:
        drum = image(drum_w, drum_h, spidisplay.buffer(drum_w * drum_h * spidisplay.PIXEL_BYTES))
    except ValueError:
        drum = image(drum_w, drum_h)

    # The opening is cut into the plate, so its edge is shaded along the top and lit along the bottom
    plate = brushed(width, height)
    opening = rect(left - OPENING_PAD, top - OPENING_PAD, drum_w + OPENING_PAD * 2, drum_h + OPENING_PAD * 2)
    plate.pen = EDGE_SHADED
    plate.shape(shape.rounded_rectangle(rect(opening.x - 2, opening.y - 2, opening.w + 2, opening.h + 2),
                                        CORNER, CORNER, CORNER, CORNER))
    plate.pen = EDGE_LIT
    plate.shape(shape.rounded_rectangle(rect(opening.x, opening.y, opening.w + 2, opening.h + 2),
                                        CORNER, CORNER, CORNER, CORNER))
    plate.pen = INSIDE
    plate.shape(shape.rounded_rectangle(opening, CORNER, CORNER, CORNER, CORNER))

    # A screw in each corner
    corners = [(x, y) for x in (SCREW_INSET, width - SCREW_INSET) for y in (SCREW_INSET, height - SCREW_INSET)]
    for (x, y), slot_angle in zip(corners, SLOTS):
        dome(plate, x, y, SCREW, SCREW_RIM, SCREW_HEAD)
        slot = shape.rectangle(-SCREW + 1, -1, SCREW * 2 - 2, 2)
        slot.transform = mat3().translate(x, y).rotate(slot_angle)
        plate.pen = SCREW_SLOT
        plate.shape(slot)

    # Laid over black once, as its blended pixels fall a little short of opaque, so a frame can take its
    # bytes whole
    plates[False] = image(width, height)
    plates[False].pen = color.black
    plates[False].clear()
    plates[False].blit(plate, 0, 0)

    # The colon, two rivets midway between the opening and the panel's right edge
    middle = (opening.x + opening.w + width) / 2
    for y in (top + drum_h / 3, top + drum_h * 2 / 3):
        dome(plate, middle, y, RIVET, RIVET_RIM, RIVET_HEAD)
    # Round both, with their shadows, the only part of the plate that differs between a panel with the
    # colon and one without
    reach = RIVET + 3
    colon_area.x, colon_area.y = round(middle - reach), round(top + drum_h / 3 - reach)
    colon_area.w, colon_area.h = reach * 2 + 1, round(drum_h / 3) + reach * 2 + 1
    plates[True] = image(width, height)
    plates[True].pen = color.black
    plates[True].clear()
    plates[True].blit(plate, 0, 0)


def draw(frame, showing, colon_lit, previous=None, progress=1.0):
    """
    Draw a whole panel into the frame, the plate with the drum in it.

    showing is a drum and its position, from shows(). colon_lit is None on a panel without a colon. On
    the way from a previous position the drum is part way through its roll, by progress from 0 to 1.

    Only the drum changes from frame to frame, and covers its place whole, so a frame takes the plate
    once and after that only the drum is drawn into it.
    """
    rivets = colon_lit is not None
    held = plated.get(id(frame))
    if held is None:
        frame.raw[:] = plates[rivets].raw
        plated[id(frame)] = rivets
    elif held != rivets:
        # Last drawn for a panel with the colon or without it, so only the rivets change
        frame.blit(plates[rivets], colon_area, colon_area)
        plated[id(frame)] = rivets

    name, turned = showing
    digit_rows_at, facing, length, repeat = drums[name]
    if previous is not None and progress < 1:
        turned = previous[1] + progress * ((turned - previous[1]) % repeat)

    # Each row of the drum copies the row of the strip that faces it on the curve, from the digit at that
    # place round the drum
    middle = round(turned * cell_h + cell_h / 2)
    start = strip_y = 0
    for row in range(drum_h):
        round_by = (middle + facing[row]) % length
        index = round_by // cell_h
        y = digit_rows_at[index] + round_by - index * cell_h
        # A row reading on from the one above joins its run, as one blit of many rows costs little more
        # than one of a single row
        if row > start and y == strip_y + row - start:
            continue
        if row > start:
            copy_rows(frame, strip_y, start, row - start)
        start, strip_y = row, y
    copy_rows(frame, strip_y, start, drum_h - start)
    drum.blit(shade, 0, 0)
    frame.blit(drum, left, top)


def copy_rows(frame, strip_y, row, rows):
    """Copy a run of rows from the strip onto the drum, from strip_y on the strip to row on the drum."""
    source.y, source.h = strip_y, rows
    target.y, target.h = row, rows
    drum.blit(strip, source, target)
