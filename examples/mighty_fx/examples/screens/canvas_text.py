from mighty_fx import MightyFX, SPCE
from picovector import color, font

"""
Scrolls a line of text in every pixel font the board has in ROM
"""

# Constants
MARGIN = 10             # How far the text sits from the screen's left and top edges, in pixels
LINE_GAP = 2            # The gap between each line of text, in pixels
SCROLL_SPEED = 1.0      # How far the text scrolls up each frame, in pixels

# Create a MightyFX object with a screen set on SP/CE port A
mighty = MightyFX(spce_a=SPCE.SCREEN_280)
screen = mighty.screen_a

# Access the screen and create a canvas to draw to. canvas() places it in SRAM,
# which the screen converts from about twice as fast as the regular heap
canvas = screen.canvas()


# Load every font in ROM. dir(font) lists them by name, and font.<name> loads and caches each one
fonts = [(name, getattr(font, name)) for name in sorted(dir(font))]

# Measure the whole list, so the scroll knows when it has run out
content_height = (MARGIN * 2) + sum(f.height + LINE_GAP for _, f in fonts)

scroll_y = 0.0  # Tracks the current scroll position, for smooth rendering


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():

        # Clear the canvas to navy, and draw in white
        canvas.pen = color.navy
        canvas.clear()
        canvas.pen = color.white

        # Draw a line in each font, spacing them out by their own glyph heights
        y = MARGIN + int(scroll_y)
        for name, f in fonts:
            canvas.font = f
            canvas.text(f"this is {name}", MARGIN, y)
            y += f.height + LINE_GAP

        # Scroll up, but only if there is more text than the screen can show at once
        if content_height > screen.height:
            scroll_y -= SCROLL_SPEED

            # Jump back to the start once the last line has scrolled off
            if scroll_y <= screen.height - content_height:
                scroll_y = 0.0

        # Update the screen with the latest canvas
        screen.update(canvas, v_sync=True)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
