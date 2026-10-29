from picovector import color, font, image, rect, shape

"""
A nixie tube digit for the hub clock, ten cathodes bent into digits and stacked in a glass cylinder,
the one carrying current glowing through the anode mesh. A colon is a pair of small neon lamps beside
the tube. showcase/nixie_tube.py is the fuller version.
"""

TUBE_FONT = "/rom/fonts/AlumniSansPinstripe.af"
ANTIALIAS = image.X4                # A vector face needs it, and a line a pixel wide is all edge
NEON = color.rgb(255, 102, 34)      # The red-orange a nixie's neon glows. rgb(120, 190, 255) is an argon tube
CORE = color.rgb(255, 170, 102)     # And the paler middle of it, along the wire itself
BACKGROUND = color.black            # Behind the tube
CHANGE_STEPS = 1                    # Frames between one digit and the next, the cathode losing the current still glowing

# An unlit cathode is bare metal, drawn opaque so crossing digits never build up to the lit colour
CATHODE_FRONT = (51, 43, 36)        # At the front of the stack, warmed by the neon behind it
CATHODE_BACK = (22, 20, 18)         # And at the back, further into the dark

# The stack, front cathode first, in an order tubes commonly use so the ones in front hide the lit one
# least. One further back shows smaller and a little higher, the tube being seen from just above
ORDER = (6, 7, 5, 8, 4, 3, 9, 2, 0, 1)
DEPTH_SCALE = 0.978
DEPTH_Y = 1
LIT = 255                           # The cathode carrying current
REF = 200                           # A size to measure the face at, its em box inside the scratch

# The tube's measures on a panel 320 pixels tall, scaled to the panel it is drawn for
DIGIT_H = 185                       # The drawn height of the front cathode's digit
TUBE_W = 130
TUBE_TOP = 6
TUBE_FOOT = 292                     # Where the glass ends and the pins begin
FOOT_CORNER = 8
TINT = color.rgb(34, 17, 0)         # The glass, warmed by what is inside it
RIM = color.rgb(255, 221, 170)      # What catches the light on the glass
SHADE = 18                          # How far in from the wall the glass darkens, which rounds the cylinder
SHADE_DARK = 170                    # How dark it is at the wall itself, of 255
PINS = 11
PIN = color.rgb(119, 102, 85)
BOARD = color.rgb(17, 17, 17)       # What the tube is stood in
ROD = color.rgb(68, 60, 52)         # The supports down either side of the stack
MICA = color.rgb(102, 94, 85)       # The spacers the stack is held between

# What the glow reaches besides the cathode itself
ENVELOPE = 60                       # The glass down either side of the tube, catching a little of it
BASE_GLOW = 110                     # The gas low in the tube, where the cathodes' leads gather
BASE_ROWS = 34                      # How far up that reaches, falling away over the distance
SHEATH = 2                          # How far the neon's sheath reaches past the wire, in panel pixels
SHEATH_LEVEL = 0.28                 # Its brightness against the core's

# The colon's lamps, small neon bulbs standing beside the tube
LAMP_W = 12                         # A bulb's width
LAMP_H = 22                         # And its height
LAMP_GLASS = color.rgb(255, 221, 170).with_alpha(60)
LAMP_OFF = 50                       # How much a lamp's electrodes show while it is off, of 255

# The filters over the whole frame, the neon's glow, the anode mesh in front of it, and the glass
GLOW_FROM = 100                     # The brightness a pixel glows from, well above an unlit cathode's
GLOW = 220                          # How much of the halo is added back, 255 being all of it
GLOW_SPREAD = 10                    # How far it reaches, in panel pixels
MESH = 4                            # Every this many rows and columns is darkened
MESH_DARK = 30                      # By this much, of 255
CURVE = 80                          # How far the picture falls away at the edges

CATHODES = len(ORDER)
DEPTH_OF = {digit: depth for depth, digit in enumerate(ORDER)}
# Each depth's unlit colour, stepped from the front cathode's to the back one's
UNLIT = tuple(color.rgb(*(round(front + (back - front) * depth / (CATHODES - 1))
                          for front, back in zip(CATHODE_FRONT, CATHODE_BACK)))
              for depth in range(CATHODES))
# The eight places round the digit its sheath is drawn at
SHEATH_AT = tuple((dx, dy) for dx in (-SHEATH, 0, SHEATH) for dy in (-SHEATH, 0, SHEATH) if dx or dy)

# Made by prepare() for the panel's size, and kept
face = None
stack = None                        # The tube with its unlit stack and the glow beyond the cathodes
front = []                          # The front of the glass, drawn over everything else
lamps = []                          # The colon's bulbs, each its glass and the glow in it
width = height = 0
size = digit_h = lettering_down = 0
advance = {}


def lettering_rows(letters, at):
    """
    Measure the first and last rows these characters fill, drawn at REF on the stack as a scratch.

    A face's metrics are not where its lettering lands.
    """
    stack.raw[:] = bytes(len(stack.raw))
    stack.pen = color.white
    stack.text(letters, at, at, REF)

    filled = bytes(stack.raw)
    return ((len(filled) - len(filled.lstrip(b"\0"))) // stack.stride,
            (len(filled.rstrip(b"\0")) - 1) // stack.stride)


def place(digit):
    """Find where a cathode's digit is drawn and at what size, for its depth, centred so the count does not walk across the tube."""
    depth = DEPTH_OF[digit]
    drawn = size * DEPTH_SCALE ** depth
    return ((width - advance[digit] * drawn / size) / 2,
            (height - digit_h * drawn / size) / 2 - lettering_down * drawn - DEPTH_Y * depth, drawn)


def prepare(panel_width, panel_height):
    """Build the tube, sized to a panel this size, and draw the background every frame starts from."""
    global face, stack, width, height, size, digit_h, lettering_down
    width, height = panel_width, panel_height
    scale = height / 320
    face = font.load(TUBE_FONT)
    stack = image(width, height)
    stack.antialias = ANTIALIAS
    stack.font = face

    digit_h = round(DIGIT_H * scale)
    top, bottom = lettering_rows("8", 0)
    size = REF * digit_h / (bottom - top + 1)
    lettering_down = top / REF          # How far below the y it is drawn at a digit's lettering starts, per unit of size
    for digit in ORDER:
        advance[digit] = stack.measure_text(str(digit), font_size=size)[0]

    tube_w, tube_top, tube_foot, corner = TUBE_W * scale, TUBE_TOP * scale, TUBE_FOOT * scale, FOOT_CORNER * scale
    tube_x = (width - tube_w) / 2
    radius = tube_w / 2
    middle = width / 2
    dome = tube_top + radius
    side = tube_foot - dome             # The length of the straight wall, under the dome
    glass = shape.rounded_rectangle(tube_x, tube_top, tube_w, tube_foot - tube_top, radius, radius, corner, corner)

    front.extend((
        # The outline, and a fainter line just inside it where the wall's thickness shows
        (RIM.with_alpha(80), shape.rounded_rectangle(tube_x, tube_top, tube_w, tube_foot - tube_top,
                                                     radius, radius, corner, corner).stroke(1.5)),
        (RIM.with_alpha(30), shape.rounded_rectangle(tube_x + 3, tube_top + 3, tube_w - 6, tube_foot - tube_top - 5,
                                                     radius - 3, radius - 3, corner - 2, corner - 2).stroke(1)),
        # A streak down the lit side, a faint wide one with a bright narrow one in it, and a thinner one opposite
        (RIM.with_alpha(22), shape.rounded_rectangle(tube_x + 8, dome - 6, 7, side - 20, 3.5)),
        (RIM.with_alpha(150), shape.rounded_rectangle(tube_x + 10.5, dome + 24, 2, side - 80, 1)),
        (RIM.with_alpha(55), shape.rounded_rectangle(tube_x + tube_w - 11, dome + 40, 2, side - 120, 1)),
        # The dome catching the light on both shoulders, and the foot where the glass turns under
        (RIM.with_alpha(110), shape.arc(middle, dome, radius - 9, radius - 6, -62, -24)),
        (RIM.with_alpha(40), shape.arc(middle, dome, radius - 9, radius - 7, 30, 52)),
        (RIM.with_alpha(60), shape.rounded_rectangle(tube_x + 10, tube_foot - 3, tube_w - 20, 1.5, 0.75)),
    ))

    # The colon's bulbs stand midway between the tube and the panel's right edge
    lamp_x = (tube_x + tube_w + width) / 2
    for lamp_y in (height * 0.38, height * 0.62):
        lamps.append((shape.rounded_rectangle(lamp_x - LAMP_W / 2, lamp_y - LAMP_H / 2, LAMP_W, LAMP_H, LAMP_W / 2).stroke(1),
                      shape.rounded_rectangle(lamp_x - LAMP_W / 4, lamp_y - LAMP_H / 4, LAMP_W / 2, LAMP_H / 2, LAMP_W / 4)))

    stack.pen = BACKGROUND
    stack.clear()

    # The pins, from the foot of the glass into the board, and the board
    board_y = round(tube_foot + 16 * scale)
    stack.pen = PIN
    for pin in range(PINS):
        stack.vspan(round(tube_x + 14 + pin * (tube_w - 28) / (PINS - 1)), round(tube_foot), board_y - round(tube_foot))
    stack.pen = BOARD
    stack.rectangle(rect(0, board_y, width, height - board_y))

    # The glass, darkening towards its walls as a cylinder does
    stack.pen = TINT
    stack.shape(glass)
    wall = round(tube_foot - dome)
    left, right = round(tube_x), round(tube_x + tube_w) - 1
    for step in range(SHADE):
        stack.pen = BACKGROUND.with_alpha(round(SHADE_DARK * (1 - step / SHADE) ** 2))
        stack.vspan(left + step, round(dome), wall - round(corner) // 2)
        stack.vspan(right - step, round(dome), wall - round(corner) // 2)
        stack.shape(shape.arc(middle, dome, radius - step - 1, radius - step, -90, 90))

    # And the light of the gas held in it, down the walls and gathered at the foot
    stack.pen = NEON.with_alpha(ENVELOPE)
    stack.vspan(left + 1, round(dome), wall - round(corner))
    stack.vspan(right - 1, round(dome), wall - round(corner))
    for row in range(BASE_ROWS):
        stack.pen = NEON.with_alpha(round(BASE_GLOW * (1 - row / BASE_ROWS) ** 2))
        stack.hspan(left + 3, round(tube_foot) - 2 - row, round(tube_w) - 6)

    # The supports down either side of the stack, and the spacers it is held between, each a disc seen from
    # just above, so its top shows as a thin ellipse
    top = (height - digit_h) // 2 - 12
    bottom = (height + digit_h) // 2 + 8
    stack.pen = ROD
    stack.vspan(left + 18, top, round(tube_foot) - top)
    stack.vspan(right - 18, top, round(tube_foot) - top)
    for y in (top - 2, bottom + 2):
        stack.pen = MICA.with_alpha(150)
        stack.shape(shape.ellipse(middle, y, radius - 12, 3))
        stack.pen = MICA
        stack.shape(shape.ellipse(middle, y, radius - 12, 3).stroke(1))

    # The tip on top of the dome, where the tube was sealed, dark glass with the light on one side of it
    tip = shape.rounded_rectangle(middle - 9, tube_top - 5, 18, 13, 8, 8, 3, 3)
    for pen, part in ((color.rgb(68, 51, 34), tip), (RIM.with_alpha(80), tip.stroke(1)),
                      (RIM.with_alpha(140), shape.rounded_rectangle(middle - 5, tube_top - 3, 3, 7, 1.5))):
        stack.pen = pen
        stack.shape(part)

    # Back to front, so a nearer cathode crosses over those behind it
    for depth in range(CATHODES - 1, -1, -1):
        x, y, drawn = place(ORDER[depth])
        stack.pen = UNLIT[depth]
        stack.text(str(ORDER[depth]), x, y, drawn)

    stack = settled(stack)


def settled(drawn):
    """
    Make the background every frame is copied from, opaque and with the edges' fall-off already in it.

    Its blended pixels fall a little short of opaque, so it is laid over black once here, and a frame can
    then take its bytes whole. The fall-off is at the edges, where nothing a frame adds reaches.
    """
    opaque = image(width, height)
    opaque.pen = BACKGROUND
    opaque.clear()
    opaque.blit(drawn, 0, 0)
    opaque.vignette(CURVE)
    return opaque


def cathode(frame, digit, level):
    """Light a cathode over the whole stack, its sheath the digit around the wire and its core the digit on it."""
    x, y, drawn = place(digit)
    frame.pen = NEON.with_alpha(round(level * SHEATH_LEVEL))
    for dx, dy in SHEATH_AT:
        frame.text(str(digit), x + dx, y + dy, drawn)
    frame.pen = CORE.with_alpha(level)
    frame.text(str(digit), x, y, drawn)


def draw(frame, digit, colon_lit, previous=None, progress=1.0):
    """
    Draw a whole panel into the frame, the tube with the digit's cathode lit, the filters and the glass.

    colon_lit is None on a panel without a colon, and otherwise says whether it is lit. On the way from
    a previous digit its cathode keeps the glow the new one has yet to take, by progress from 0 to 1.
    """
    frame.antialias = ANTIALIAS
    frame.font = face
    frame.raw[:] = stack.raw

    if previous is not None and previous != " " and progress < 1:
        cathode(frame, int(previous), round(LIT * (1 - progress)))
    if digit != " ":
        cathode(frame, int(digit), round(LIT * progress))

    if colon_lit is not None:
        for glass, glow in lamps:
            frame.pen = LAMP_GLASS
            frame.shape(glass)
            frame.pen = NEON if colon_lit else NEON.with_alpha(LAMP_OFF)
            frame.shape(glow)

    # The bloom goes on the opaque frame, as on a transparent one it lifts channels past their alpha
    frame.bloom(GLOW_FROM, GLOW, GLOW_SPREAD)
    frame.grid(MESH, MESH_DARK)
    for pen, glass in front:
        frame.pen = pen
        frame.shape(glass)
