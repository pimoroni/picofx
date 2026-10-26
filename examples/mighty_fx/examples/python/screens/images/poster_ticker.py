from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import color, font, image, rect, vec2

"""
Scroll a message across a poster read from a file, in lettering matching the poster's own.

load_into() reads a file into an image that already exists, keeping that image's size and
colour. The copy here is full colour, so a palettised poster arrives as colour that can be
drawn over, where image.load() would hand back a palettised image nothing can draw into.
Each frame copies the band the message crosses back from it, then lays the message on.

Press "Boot" to exit the program.
"""

# Constants
POSTER = "/examples/assets/billboards/portrait/scooshers.png"      # A 240x320 picture, the 2.8" panel's own shape
MESSAGE = "Two for one, all weekend."           # What scrolls across the poster
MESSAGE_FONT = "/rom/fonts/PoppinsBlack.af"     # A heavy vector face, close to the poster's own lettering
MESSAGE_SIZE = 60                               # How large the lettering is drawn
STEP = 2                                        # How far the message moves each frame, in whole pixels so every step is even
TEXT_COLOUR = color.rgb(255, 255, 0)            # The poster's own yellow
OUTLINE = color.rgb(23, 17, 5)                  # And the dark edge around its lettering
EDGE = 2                                        # How far the outline reaches past the lettering, in pixels
MARGIN = 6                                      # How far the lettering sits above the foot of the poster, in pixels

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)
canvas = screen.canvas()
canvas.antialias = image.X4
canvas.font = font.load(MESSAGE_FONT)

# A full colour image the size of the panel, which load_into() fills without changing
poster = image(screen.width, screen.height)
try:
    poster.load_into(POSTER)
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{POSTER}' is missing! Check it is on the board") from None

canvas.blit(poster, 0, 0)

# The message is drawn once, outline and all, into an image of its own. An image starts empty, so
# around the lettering it stays transparent and the poster shows through. The outline is the
# lettering drawn in the dark colour all round where the yellow sits
message_w, message_h = canvas.measure_text(MESSAGE, font_size=MESSAGE_SIZE)

# The lettering reaches below its measured height (the comma's tail lowest) and its antialiased
# edge a pixel past its measured width, so the image is made larger than measured to hold both
message = image(int(message_w) + EDGE * 2 + 2, int(message_h * 1.3) + EDGE * 2)

message.antialias = image.X4
message.font = canvas.font
message.pen = OUTLINE
for dx in (-EDGE, 0, EDGE):
    for dy in (-EDGE, 0, EDGE):
        message.text(MESSAGE, vec2(EDGE + dx, EDGE + dy), font_size=MESSAGE_SIZE)
message.pen = TEXT_COLOUR
message.text(MESSAGE, vec2(EDGE, EDGE), font_size=MESSAGE_SIZE)

# Which rows of the message are drawn on, since a face's metrics are not where its lettering lands
# A pixel is four bytes and the fourth is its alpha
pixels = memoryview(message.raw)
drawn_rows = [row for row in range(message.height)
              if any(pixels[row * message.stride + column * 4 + 3] for column in range(message.width))]
top, bottom = drawn_rows[0], drawn_rows[-1]

# The message runs in from the right edge and out past the left, its lettering along the foot of the
# poster below the product. The band is the rows the lettering crosses, all that is copied back each frame
y = screen.height - MARGIN - 1 - bottom
band = rect(0, y + top, screen.width, bottom - top + 1)
travel = screen.width + message.width

frame = 0

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # In from the right edge a step a frame, starting again once it has cleared the left
        x = screen.width - frame * STEP % travel
        frame += 1

        # Copy the band back from the poster over the last frame's message, then lay it one step along
        canvas.blit(poster, band, band)
        canvas.blit(message, x, y)
        screen.update(canvas)

# Turn off the panel and all the outputs
finally:
    mighty.shutdown()
