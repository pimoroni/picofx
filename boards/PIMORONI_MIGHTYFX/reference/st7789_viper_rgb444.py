"""ST7789 driver for 12-bit panels, converting pixels in pure MicroPython.

Reference implementation. MightyFX drives its panels through the spidisplay C
module instead, so this is not shipped to the board and nothing in the firmware
imports it. It is kept as a worked example of `@micropython.viper`, and as the
starting point for a board that has no spidisplay module built in.
`st7789_viper_rgb565.py` is the 16-bit sibling, with a narrower feature set.

It depends on nothing outside the standard MicroPython library: `machine.SPI`,
three GPIOs, and a source object exposing the buffer protocol plus `width` and
`height`. So it drops onto any board with an ST7789 panel. Conversion runs on the
CPU into a full-frame staging buffer, which is then written in one blocking
`spi.write()`.

The eight kernels below are the complete feature set: all four rotations, mirror,
pixel doubling, and a source of any size placed against a background fill. That
is why this is the one to start from, and why the 16-bit version is a poor
substitute.

Its one real limit is that conversion and transfer are strictly sequential, so a
frame costs convert plus transfer. The C module overlaps them and is roughly twice
as fast for the same panel.

Tearing effect is read on the DC line, as MightyFX wires it. A panel with a
dedicated TE pin needs `v_sync` changing to poll that pin instead.
"""

import machine
from st7789_viper_common import COLMOD_RGB444, REG_RAMWR, setup


"""
@micropython.viper
def rgb444_padding(dst: ptr8, length: int, di: int, d0: int, d1: int, d2: int) -> int:
    # Usage:  di = int(rgb444_padding(dst, y_padding_w_width, 0, 0xf0, 0xff, 0xff))
    # Note:   Not using it because function calls add overhead
    for _ in range(0, length, 2):
        # Convert the two pixels into RGB444 packed into 3 bytes
        dst[di] = d0
        dst[di + 1] = d1
        dst[di + 2] = d2

        di += 3     # Move along to the next pixel pair
    return di
"""


# RGB444 kernels, the wired set. Four placements times single or doubled pixels,
# each handling centring, background padding and an odd source width, and each
# splitting on flip_y so the y loop direction is fixed outside the inner loop.


@micropython.viper
def rgba8888_to_rgb444_normal(dst: ptr8, src: ptr8, dst_width: int, dst_height: int, src_width: int, src_height: int, bg: int, flip_y: int):
    # Fastest implementation so far: 49.6ms (measured with 320x240)

    di = 0          # Index of the pixel pair being worked on

    # The padding to apply around the image to centre it
    y_padding = (dst_height - src_height) >> 1
    x_padding = (dst_width - src_width) >> 1

    start_y = -y_padding if y_padding < 0 else 0
    end_y = src_height - start_y

    src_width <<= 2     # Scale the width up by the number of bytes per src pixel, to save some computation

    start_x = -(x_padding << 2) if x_padding < 0 else 0
    end_x = src_width - start_x
    row_bytes = end_x - start_x     # This is not always src_width

    #  Calculate padding for images smaller than the screen
    y_padding_pairs = y_padding * (dst_width >> 1)  # dst_width / 2
    x_pad_left_pairs = (x_padding + 1) >> 1         # ceil(x_padding / 2)
    x_pad_right_pairs = x_padding >> 1              # floor(x_padding / 2)

    # Calculate the rgb444 background colour
    bg0 = (bg & 0xf0) | ((bg >> 12) & 0x0f)         # R1 | G1
    bg1 = ((bg >> 16) & 0xf0) | ((bg >> 4) & 0x0f)  # B1 | R2
    bg2 = ((bg >> 8) & 0xf0) | ((bg >> 20) & 0x0f)  # G2 | B2

    # Pre-padding rows
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    if flip_y == 0:
        for y in range(start_y, end_y):
            y_width = y * src_width

            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(start_x, end_x - 4, 8):  # Sub 4 so we can handle the last pixel separately, if src is odd width
                # Calc the two pixel coordinates to sample
                p0 = y_width + x
                p1 = p0 + 4         # Next pixel

                # Convert the two pixels into RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p1] >> 4)         # B1 | R2
                dst[di + 2] = (src[p1 + 1] & 0xf0) | (src[p1 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Handle the last pixel if src has an odd width
            if row_bytes & 0x04:
                p0 = y_width + (end_x - 4)

                # P0 from src, P1 from bg
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | ((bg >> 4) & 0x0f)     # B1 | R2(bg)
                dst[di + 2] = bg2                                           # G2(bg) | B2(bg)
                di += 3

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    else:
        for y in range(end_y - 1, start_y - 1, -1):
            y_width = y * src_width

            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(start_x, end_x - 4, 8):  # Sub 4 so we can handle the last pixel separately, if src is odd width
                # Calc the two pixel coordinates to sample
                p0 = y_width + x
                p1 = p0 + 4         # Next pixel

                # Convert the two pixels into RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p1] >> 4)         # B1 | R2
                dst[di + 2] = (src[p1 + 1] & 0xf0) | (src[p1 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Handle the last pixel if src has an odd width
            if row_bytes & 0x04:
                p0 = y_width + (end_x - 4)

                # P0 from src, P1 from bg
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | ((bg >> 4) & 0x0f)     # B1 | R2(bg)
                dst[di + 2] = bg2                                           # G2(bg) | B2(bg)
                di += 3

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    # Post-padding rows
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3


@micropython.viper
def rgba8888_to_rgb444_double_normal(dst: ptr8, src: ptr8, dst_width: int, dst_height: int, src_width: int, src_height: int, bg: int, flip_y: int):
    # Fastest implementation so far: 49.6ms (measured with 320x240)

    di = 0          # Index of the pixel pair being worked on

    # The padding to apply around the image to centre it
    y_padding = (dst_height - (src_height << 1)) >> 1
    x_padding = (dst_width - (src_width << 1)) >> 1

    start_y = -y_padding if y_padding < 0 else 0
    end_y = (src_height << 1) - start_y

    # src_width <<= 2     # Removed as it causes numbers to go out of bounds later

    start_x = -(x_padding) if x_padding < 0 else 0
    end_x = (src_width << 1) - start_x
    start_x >>= 1
    end_x >>= 1

    #  Calculate padding for images smaller than the screen
    y_padding_pairs = y_padding * (dst_width >> 1)  # dst_width / 2
    x_pad_left_pairs = (x_padding + 1) >> 1         # ceil(x_padding / 2)
    x_pad_right_pairs = x_padding >> 1              # floor(x_padding / 2)

    # Calculate the rgb444 background colour
    bg0 = (bg & 0xf0) | ((bg >> 12) & 0x0f)         # R1 | G1
    bg1 = ((bg >> 16) & 0xf0) | ((bg >> 4) & 0x0f)  # B1 | R2
    bg2 = ((bg >> 8) & 0xf0) | ((bg >> 20) & 0x0f)  # G2 | B2

    # Pre-padding rows
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    if flip_y == 0:
        for y in range(start_y, end_y):
            y_width = (y >> 1) * src_width

            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(start_x, end_x, 1):
                # Calc the pixel coordinate to sample
                p0 = (y_width + x) << 2

                # Convert the pixel into 2 x RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p0] >> 4)         # B1 | R2
                dst[di + 2] = (src[p0 + 1] & 0xf0) | (src[p0 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    else:
        for y in range(end_y - 1, start_y - 1, -1):
            y_width = (y >> 1) * src_width

            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(start_x, end_x, 1):
                # Calc the pixel coordinate to sample
                p0 = (y_width + x) << 2

                # Convert the pixel into 2 x RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p0] >> 4)         # B1 | R2
                dst[di + 2] = (src[p0 + 1] & 0xf0) | (src[p0 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    # Post-padding row
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3


@micropython.viper
def rgba8888_to_rgb444_mirror(dst: ptr8, src: ptr8, dst_width: int, dst_height: int, src_width: int, src_height: int, bg: int, flip_y: int):
    # Fastest implementation so far: 49.6ms (measured with 320x240)

    di = 0          # Index of the pixel pair being worked on

    # The padding to apply around the image to centre it
    y_padding = (dst_height - src_height) >> 1
    x_padding = (dst_width - src_width) >> 1

    start_y = -y_padding if y_padding < 0 else 0
    end_y = src_height - start_y

    src_width <<= 2     # Scale the width up by the number of bytes per src pixel, to save some computation

    start_x = -(x_padding << 2) if x_padding < 0 else 0
    end_x = src_width - start_x
    row_bytes = end_x - start_x     # This is not always src_width

    #  Calculate padding for images smaller than the screen
    y_padding_pairs = y_padding * (dst_width >> 1)  # dst_width / 2
    x_pad_left_pairs = (x_padding + 1) >> 1         # ceil(x_padding / 2)
    x_pad_right_pairs = x_padding >> 1              # floor(x_padding / 2)

    # Calculate the rgb444 background colour
    bg0 = (bg & 0xf0) | ((bg >> 12) & 0x0f)         # R1 | G1
    bg1 = ((bg >> 16) & 0xf0) | ((bg >> 4) & 0x0f)  # B1 | R2
    bg2 = ((bg >> 8) & 0xf0) | ((bg >> 20) & 0x0f)  # G2 | B2

    # Pre-padding rows
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    if flip_y == 0:
        for y in range(start_y, end_y):
            y_width = y * src_width

            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(end_x - 4, start_x - 4 + 4, -8):  # Add 4 so we can handle the last pixel separately, if src is odd width
                # Calc the two pixel coordinates to sample
                p0 = y_width + x
                p1 = p0 - 4     # Prev pixel

                # Convert the two pixels into RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p1] >> 4)         # B1 | R2
                dst[di + 2] = (src[p1 + 1] & 0xf0) | (src[p1 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Handle the last pixel if src has an odd width
            if row_bytes & 0x04:
                p0 = y_width + start_x

                # P0 from src, P1 from bg
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | ((bg >> 4) & 0x0f)     # B1 | R2(bg)
                dst[di + 2] = bg2                                           # G2(bg) | B2(bg)
                di += 3

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3
    else:
        for y in range(end_y - 1, start_y - 1, -1):
            y_width = y * src_width

            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(end_x - 4, start_x - 4 + 4, -8):  # Add 4 so we can handle the last pixel separately, if src is odd width
                # Calc the two pixel coordinates to sample
                p0 = y_width + x
                p1 = p0 - 4     # Prev pixel

                # Convert the two pixels into RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p1] >> 4)         # B1 | R2
                dst[di + 2] = (src[p1 + 1] & 0xf0) | (src[p1 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Handle the last pixel if src has an odd width
            if row_bytes & 0x04:
                p0 = y_width + start_x

                # P0 from src, P1 from bg
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | ((bg >> 4) & 0x0f)     # B1 | R2(bg)
                dst[di + 2] = bg2                                           # G2(bg) | B2(bg)
                di += 3

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    # Post-padding rows
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3


@micropython.viper
def rgba8888_to_rgb444_double_mirror(dst: ptr8, src: ptr8, dst_width: int, dst_height: int, src_width: int, src_height: int, bg: int, flip_y: int):
    # Fastest implementation so far: 49.6ms (measured with 320x240)

    di = 0          # Index of the pixel pair being worked on

    # The padding to apply around the image to centre it
    y_padding = (dst_height - (src_height << 1)) >> 1
    x_padding = (dst_width - (src_width << 1)) >> 1

    start_y = -y_padding if y_padding < 0 else 0
    end_y = (src_height << 1) - start_y

    # src_width <<= 2     # Removed as it causes numbers to go out of bounds later

    start_x = -(x_padding) if x_padding < 0 else 0
    end_x = (src_width << 1) - start_x
    start_x >>= 1
    end_x >>= 1

    #  Calculate padding for images smaller than the screen
    y_padding_pairs = y_padding * (dst_width >> 1)  # dst_width / 2
    x_pad_left_pairs = (x_padding + 1) >> 1         # ceil(x_padding / 2)
    x_pad_right_pairs = x_padding >> 1              # floor(x_padding / 2)

    # Calculate the rgb444 background colour
    bg0 = (bg & 0xf0) | ((bg >> 12) & 0x0f)         # R1 | G1
    bg1 = ((bg >> 16) & 0xf0) | ((bg >> 4) & 0x0f)  # B1 | R2
    bg2 = ((bg >> 8) & 0xf0) | ((bg >> 20) & 0x0f)  # G2 | B2

    # Pre-padding rows
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    if flip_y == 0:
        for y in range(start_y, end_y):
            y_width = (y >> 1) * src_width

            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(end_x - 1, start_x - 1, -1):
                # Calc the pixel coordinate to sample
                p0 = (y_width + x) << 2

                # Convert the pixel into 2 x RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p0] >> 4)         # B1 | R2
                dst[di + 2] = (src[p0 + 1] & 0xf0) | (src[p0 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3
    else:
        for y in range(end_y - 1, start_y - 1, -1):
            y_width = (y >> 1) * src_width

            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(end_x - 1, start_x - 1, -1):
                # Calc the pixel coordinate to sample
                p0 = (y_width + x) << 2

                # Convert the pixel into 2 x RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p0] >> 4)         # B1 | R2
                dst[di + 2] = (src[p0 + 1] & 0xf0) | (src[p0 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    # Post-padding rows
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3


@micropython.viper
def rgba8888_to_rgb444_rotate(dst: ptr8, src: ptr8, dst_width: int, dst_height: int, src_width: int, src_height: int, bg: int, flip_y: int):
    # Fastest implementation so far: 60.0ms (measured with 320x240)

    di = 0          # Index of the pixel pair being worked on

    # The padding to apply around the image to centre it
    y_padding = (dst_height - src_width) >> 1
    x_padding = (dst_width - src_height) >> 1

    src_width <<= 2     # Scale the width up by the number of bytes per src pixel, to save some computation

    # We're rotated 90 degrees, so height is width and width is height!
    start_y = -(y_padding << 2) if y_padding < 0 else 0
    end_y = src_width - start_y

    start_x = -x_padding if x_padding < 0 else 0
    end_x = src_height - start_x
    row_pixels = end_x - start_x     # This is not always src_height

    #  Calculate padding for images smaller than the screen
    y_padding_pairs = y_padding * (dst_width >> 1)  # dst_width / 2
    x_pad_left_pairs = (x_padding + 1) >> 1         # ceil(x_padding / 2)
    x_pad_right_pairs = x_padding >> 1              # floor(x_padding / 2)

    # Calculate the rgb444 background colour
    bg0 = (bg & 0xf0) | ((bg >> 12) & 0x0f)         # R1 | G1
    bg1 = ((bg >> 16) & 0xf0) | ((bg >> 4) & 0x0f)  # B1 | R2
    bg2 = ((bg >> 8) & 0xf0) | ((bg >> 20) & 0x0f)  # G2 | B2

    # Pre-padding rows
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    if flip_y == 0:
        for y in range(start_y, end_y, 4):
            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(end_x - 1, start_x - 1 + 1, -2):  # Add 1 so we can handle the last pixel separately, if src is odd width
                # Calc the two pixel coordinates to sample
                p0 = (x * src_width) + y
                p1 = p0 - src_width     # Prev pixel

                # Convert the two pixels into RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p1] >> 4)         # B1 | R2
                dst[di + 2] = (src[p1 + 1] & 0xf0) | (src[p1 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Handle the last pixel if src has an odd width
            if row_pixels & 0x01:
                p0 = (start_x * src_width) + y

                # P0 from src, P1 from bg
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | ((bg >> 4) & 0x0f)     # B1 | R2(bg)
                dst[di + 2] = bg2                                           # G2(bg) | B2(bg)
                di += 3

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3
    else:
        for y in range(end_y - 4, start_y - 4, -4):
            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(end_x - 1, start_x - 1 + 1, -2):  # Add 1 so we can handle the last pixel separately, if src is odd width
                # Calc the two pixel coordinates to sample
                p0 = (x * src_width) + y
                p1 = p0 - src_width     # Prev pixel

                # Convert the two pixels into RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p1] >> 4)         # B1 | R2
                dst[di + 2] = (src[p1 + 1] & 0xf0) | (src[p1 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Handle the last pixel if src has an odd width
            if row_pixels & 0x01:
                p0 = (start_x * src_width) + y

                # P0 from src, P1 from bg
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | ((bg >> 4) & 0x0f)     # B1 | R2(bg)
                dst[di + 2] = bg2                                           # G2(bg) | B2(bg)
                di += 3

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    # Post-padding rows
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3


@micropython.viper
def rgba8888_to_rgb444_double_rotate(dst: ptr8, src: ptr8, dst_width: int, dst_height: int, src_width: int, src_height: int, bg: int, flip_y: int):
    # Fastest implementation so far: 60.0ms (measured with 320x240)

    di = 0          # Index of the pixel pair being worked on

    # The padding to apply around the image to centre it
    y_padding = (dst_height - (src_width << 1)) >> 1
    x_padding = (dst_width - (src_height << 1)) >> 1

    # src_width <<= 2     # Removed as it causes numbers to go out of bounds later

    # We're rotated 90 degrees, so height is width and width is height!
    start_y = -(y_padding) if y_padding < 0 else 0
    end_y = (src_width << 1) - start_y

    start_x = -x_padding if x_padding < 0 else 0
    end_x = (src_height << 1) - start_x
    start_x >>= 1
    end_x >>= 1

    #  Calculate padding for images smaller than the screen
    y_padding_pairs = y_padding * (dst_width >> 1)  # dst_width / 2
    x_pad_left_pairs = (x_padding + 1) >> 1         # ceil(x_padding / 2)
    x_pad_right_pairs = x_padding >> 1              # floor(x_padding / 2)

    # Calculate the rgb444 background colour
    bg0 = (bg & 0xf0) | ((bg >> 12) & 0x0f)         # R1 | G1
    bg1 = ((bg >> 16) & 0xf0) | ((bg >> 4) & 0x0f)  # B1 | R2
    bg2 = ((bg >> 8) & 0xf0) | ((bg >> 20) & 0x0f)  # G2 | B2

    # Pre-padding rows
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    if flip_y == 0:
        for y in range(start_y, end_y):
            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(end_x - 1, start_x - 1, -1):
                # Calc the pixel coordinate to sample
                p0 = ((x * src_width) + (y >> 1)) << 2

                # Convert the pixel into 2 x RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p0] >> 4)         # B1 | R2
                dst[di + 2] = (src[p0 + 1] & 0xf0) | (src[p0 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3
    else:
        for y in range(end_y - 1, start_y - 1, -1):
            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(end_x - 1, start_x - 1, -1):
                # Calc the pixel coordinate to sample
                p0 = ((x * src_width) + (y >> 1)) << 2

                # Convert the pixel into 2 x RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p0] >> 4)         # B1 | R2
                dst[di + 2] = (src[p0 + 1] & 0xf0) | (src[p0 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    # Post-padding rows
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3


@micropython.viper
def rgba8888_to_rgb444_rotate_mirror(dst: ptr8, src: ptr8, dst_width: int, dst_height: int, src_width: int, src_height: int, bg: int, flip_y: int):
    # Fastest implementation so far: 60.0ms (measured with 320x240)

    di = 0          # Index of the pixel pair being worked on

    # The padding to apply around the image to centre it
    y_padding = (dst_height - src_width) >> 1
    x_padding = (dst_width - src_height) >> 1

    src_width <<= 2     # Scale the width up by the number of bytes per src pixel, to save some computation

    # We're rotated 90 degrees, so height is width and width is height!
    start_y = -(y_padding << 2) if y_padding < 0 else 0
    end_y = src_width - start_y

    start_x = -x_padding if x_padding < 0 else 0
    end_x = src_height - start_x
    row_pixels = end_x - start_x     # This is not always src_height

    #  Calculate padding for images smaller than the screen
    y_padding_pairs = y_padding * (dst_width >> 1)  # dst_width / 2
    x_pad_left_pairs = (x_padding + 1) >> 1         # ceil(x_padding / 2)
    x_pad_right_pairs = x_padding >> 1              # floor(x_padding / 2)

    # Calculate the rgb444 background colour
    bg0 = (bg & 0xf0) | ((bg >> 12) & 0x0f)         # R1 | G1
    bg1 = ((bg >> 16) & 0xf0) | ((bg >> 4) & 0x0f)  # B1 | R2
    bg2 = ((bg >> 8) & 0xf0) | ((bg >> 20) & 0x0f)  # G2 | B2

    # Pre-padding rows
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    if flip_y == 0:
        for y in range(start_y, end_y, 4):
            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(start_x, end_x - 1, 2):  # Sub 1 so we can handle the last pixel separately, if src is odd width
                # Calc the two pixel coordinates to sample
                p0 = (x * src_width) + y
                p1 = p0 + src_width     # Next pixel

                # Convert the two pixels into RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p1] >> 4)         # B1 | R2
                dst[di + 2] = (src[p1 + 1] & 0xf0) | (src[p1 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Handle the last pixel if src has an odd width
            if row_pixels & 0x01:
                p0 = ((end_x - 1) * src_width) + y

                # P0 from src, P1 from bg
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | ((bg >> 4) & 0x0f)     # B1 | R2(bg)
                dst[di + 2] = bg2                                           # G2(bg) | B2(bg)
                di += 3

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3
    else:
        for y in range(end_y - 4, start_y - 4, -4):
            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(start_x, end_x - 1, 2):  # Sub 1 so we can handle the last pixel separately, if src is odd width
                # Calc the two pixel coordinates to sample
                p0 = (x * src_width) + y
                p1 = p0 + src_width     # Next pixel

                # Convert the two pixels into RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p1] >> 4)         # B1 | R2
                dst[di + 2] = (src[p1 + 1] & 0xf0) | (src[p1 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Handle the last pixel if src has an odd width
            if row_pixels & 0x01:
                p0 = ((end_x - 1) * src_width) + y

                # P0 from src, P1 from bg
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | ((bg >> 4) & 0x0f)     # B1 | R2(bg)
                dst[di + 2] = bg2                                           # G2(bg) | B2(bg)
                di += 3

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    # Post-padding rows
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3


@micropython.viper
def rgba8888_to_rgb444_double_rotate_mirror(dst: ptr8, src: ptr8, dst_width: int, dst_height: int, src_width: int, src_height: int, bg: int, flip_y: int):
    # Fastest implementation so far: 60.0ms (measured with 320x240)

    di = 0          # Index of the pixel pair being worked on

    # The padding to apply around the image to centre it
    y_padding = (dst_height - (src_width << 1)) >> 1
    x_padding = (dst_width - (src_height << 1)) >> 1

    # src_width <<= 2     # Removed as it causes numbers to go out of bounds later

    # We're rotated 90 degrees, so height is width and width is height!
    start_y = -(y_padding) if y_padding < 0 else 0
    end_y = (src_width << 1) - start_y

    start_x = -x_padding if x_padding < 0 else 0
    end_x = (src_height << 1) - start_x
    start_x >>= 1
    end_x >>= 1

    #  Calculate padding for images smaller than the screen
    y_padding_pairs = y_padding * (dst_width >> 1)  # dst_width / 2
    x_pad_left_pairs = (x_padding + 1) >> 1         # ceil(x_padding / 2)
    x_pad_right_pairs = x_padding >> 1              # floor(x_padding / 2)

    # Calculate the rgb444 background colour
    bg0 = (bg & 0xf0) | ((bg >> 12) & 0x0f)         # R1 | G1
    bg1 = ((bg >> 16) & 0xf0) | ((bg >> 4) & 0x0f)  # B1 | R2
    bg2 = ((bg >> 8) & 0xf0) | ((bg >> 20) & 0x0f)  # G2 | B2

    # Pre-padding rows
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    if flip_y == 0:
        for y in range(start_y, end_y):
            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(start_x, end_x):
                # Calc the pixel coordinate to sample
                p0 = ((x * src_width) + (y >> 1)) << 2

                # Convert the pixel into 2 x RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p0] >> 4)         # B1 | R2
                dst[di + 2] = (src[p0 + 1] & 0xf0) | (src[p0 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3
    else:
        for y in range(end_y - 1, start_y - 1, -1):
            # Pre-padding columns
            for _ in range(x_pad_left_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

            for x in range(start_x, end_x):
                # Calc the pixel coordinate to sample
                p0 = ((x * src_width) + (y >> 1)) << 2

                # Convert the pixel into 2 x RGB444 packed into 3 bytes
                dst[di] = (src[p0] & 0xf0) | (src[p0 + 1] >> 4)             # R1 | G1
                dst[di + 1] = (src[p0 + 2] & 0xf0) | (src[p0] >> 4)         # B1 | R2
                dst[di + 2] = (src[p0 + 1] & 0xf0) | (src[p0 + 2] >> 4)     # G2 | B2

                di += 3     # Move along to the next pixel pair

            # Post-padding columns
            for _ in range(x_pad_right_pairs):
                dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3

    # Post-padding rows
    for _ in range(y_padding_pairs):
        dst[di] = bg0; dst[di + 1] = bg1; dst[di + 2] = bg2; di += 3


# Indexed by placement: normal, mirror, rotate, rotate and mirror
PIXEL_FUNCTIONS = (rgba8888_to_rgb444_normal, rgba8888_to_rgb444_mirror,
                   rgba8888_to_rgb444_rotate, rgba8888_to_rgb444_rotate_mirror)

PIXEL_DOUBLE_FUNCTIONS = (rgba8888_to_rgb444_double_normal, rgba8888_to_rgb444_double_mirror,
                          rgba8888_to_rgb444_double_rotate, rgba8888_to_rgb444_double_rotate_mirror)


class ST7789_RGB444:
    def __init__(self, spi, cs, dc, bl, width=240, height=240, framerate=60):
        self.spi = spi
        self.CS = cs
        self.DC = dc
        self.CS.init(machine.Pin.OUT)
        self.DC.init(machine.Pin.OUT)

        self.BL = bl
        self.BL.init(machine.Pin.OUT, value=False)

        self._width = width
        self._height = height

        self.__normal, self.__mirror, self.__rotate, self.__rotate_mirror = PIXEL_FUNCTIONS
        self.__dbl_normal, self.__dbl_mirror, self.__dbl_rotate, self.__dbl_rotate_mirror = PIXEL_DOUBLE_FUNCTIONS

        # Two pixels pack into three bytes
        self.BUFFER = bytearray((self._width * self._height * 3) // 2)

        setup(self, COLMOD_RGB444, framerate)

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    def command(self, command, data=None):
        self.DC.low()
        self.CS.low()

        if isinstance(command, int):
            command = bytes((command, ))

        self.spi.write(command)

        if data:
            if isinstance(data, int):
                data = bytes((data, ))
            self.DC.high()
            self.spi.write(data)

        self.CS.high()

    @micropython.native
    def update(self, image, rotation=0, mirror=False, v_sync=False, bg=0, pixel_double=False):
        """Convert an image and write it to the panel.

        image is anything supporting the buffer protocol with width and height
        attributes, holding RGBA8888 pixels. A picovector image works, as does a
        bytearray wrapped in a class exposing those two attributes.

        bg fills the area an undersized image does not cover, packed the same way
        as the source: 0xAABBGGRR, so (a << 24) | (b << 16) | (g << 8) | r. Alpha
        is ignored. From picovector, pass a colour's .p attribute.
        """
        bg = bg & 0xffffffff

        r_index = rotation // 90
        if r_index < 0 or r_index > 3 or rotation % 90:     # Modulo check ensures rotation is exactly a multipe of 90
            raise ValueError(f"{rotation} is not a valid angle. Expected 0, 90, 180, or 270.")

        r_half = r_index >> 1          # Zero for 0 or 90. One for 180 or 270

        if r_index & 0x1:     # Is the rotation 90 or 270 degrees?
            flip_x = r_half
            flip_y = (1 - r_half) if mirror else r_half

            # start = time.ticks_us()
            if flip_x:
                if pixel_double:
                    self.__dbl_rotate_mirror(memoryview(self.BUFFER), memoryview(image),
                                             self._width, self._height, image.width, image.height, bg, flip_y)
                else:
                    self.__rotate_mirror(memoryview(self.BUFFER), memoryview(image),
                                         self._width, self._height, image.width, image.height, bg, flip_y)
            else:
                if pixel_double:
                    self.__dbl_rotate(memoryview(self.BUFFER), memoryview(image),
                                      self._width, self._height, image.width, image.height, bg, flip_y)
                else:
                    self.__rotate(memoryview(self.BUFFER), memoryview(image),
                                  self._width, self._height, image.width, image.height, bg, flip_y)
            # dt = time.ticks_diff(time.ticks_us(), start)
            # print("rgba8888_to_rgb444_rotate_90:", dt)
        else:
            flip_x = (1 - r_half) if mirror else r_half
            flip_y = r_half

            # start = time.ticks_us()
            if flip_x:
                if pixel_double:
                    self.__dbl_mirror(memoryview(self.BUFFER), memoryview(image),
                                      self._width, self._height, image.width, image.height, bg, flip_y)
                else:
                    self.__mirror(memoryview(self.BUFFER), memoryview(image),
                                  self._width, self._height, image.width, image.height, bg, flip_y)
            else:
                if pixel_double:
                    self.__dbl_normal(memoryview(self.BUFFER), memoryview(image),
                                      self._width, self._height, image.width, image.height, bg, flip_y)
                else:
                    self.__normal(memoryview(self.BUFFER), memoryview(image),
                                  self._width, self._height, image.width, image.height, bg, flip_y)
            # dt = time.ticks_diff(time.ticks_us(), start)
            # print("rgba8888_to_rgb444_rotate_90:", dt)

        if v_sync:
            self.DC.init(machine.Pin.IN)
            while self.DC.value() == 0:
                pass
            while self.DC.value() == 1:
                pass
            self.DC.init(machine.Pin.OUT)

        # start = time.ticks_us()
        self.DC.low()
        self.CS.low()

        self.spi.write(bytes((REG_RAMWR, )))

        self.DC.high()

        self.spi.write(self.BUFFER)

        self.CS.high()
        # dt = time.ticks_diff(time.ticks_us(), start)
        # print("spi.write:", dt)

        self.BL.on()
