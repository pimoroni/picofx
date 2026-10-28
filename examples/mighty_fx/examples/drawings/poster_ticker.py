from picovector import color, font, image, rect, vec2

"""
Drawing: Poster ticker
A message scrolling across a poster, in lettering matching the poster's own.
Section: Billboards and panels
"""

# Entry: screenA: graphics file=poster_ticker.py   (a 2.8" screen)

# Constants
POSTER = "/examples/assets/billboards/portrait/scooshers.png"      # A 240x320 picture
MESSAGE = "Two for one, all weekend."
MESSAGE_FONT = "/rom/fonts/PoppinsBlack.af"
MESSAGE_SIZE = 60
STEP = 2
TEXT_COLOUR = color.rgb(255, 255, 0)
OUTLINE = color.rgb(23, 17, 5)
EDGE = 2
MARGIN = 6

message_font = font.load(MESSAGE_FONT)

# The message drawn once, outline and all, into an image of its own
ruler = image(8, 8)
ruler.font = message_font
message_w, message_h = ruler.measure_text(MESSAGE, font_size=MESSAGE_SIZE)
message = image(int(message_w) + EDGE * 2 + 2, int(message_h * 1.3) + EDGE * 2)
message.antialias = image.X4
message.font = message_font
message.pen = OUTLINE
for dx in (-EDGE, 0, EDGE):
    for dy in (-EDGE, 0, EDGE):
        message.text(MESSAGE, vec2(EDGE + dx, EDGE + dy), font_size=MESSAGE_SIZE)
message.pen = TEXT_COLOUR
message.text(MESSAGE, vec2(EDGE, EDGE), font_size=MESSAGE_SIZE)

pixels = memoryview(message.raw)
drawn_rows = [row for row in range(message.height)
              if any(pixels[row * message.stride + column * 4 + 3] for column in range(message.width))]
top, bottom = drawn_rows[0], drawn_rows[-1]
del pixels, ruler

# The poster and the band the message crosses, set on the first call from the canvas's size
poster = None
band = None
y = travel = 0
frame = 0


def draw(canvas, _elapsed):
    global poster, band, y, travel, frame
    if poster is None:
        poster = image(canvas.width, canvas.height)
        try:
            poster.load_into(POSTER)
        except OSError:
            raise RuntimeError(f"'{POSTER}' is missing! Check it is on the drive") from None
        canvas.blit(poster, 0, 0)
        y = canvas.height - MARGIN - 1 - bottom
        band = rect(0, y + top, canvas.width, bottom - top + 1)
        travel = canvas.width + message.width

    x = canvas.width - frame * STEP % travel
    frame += 1

    canvas.blit(poster, band, band)
    canvas.blit(message, x, y)
