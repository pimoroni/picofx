import time
import struct
import machine
from collections import OrderedDict
import picovector

MADCTL_ROW_ORDER   = const(0b10000000)
MADCTL_COL_ORDER   = const(0b01000000)
MADCTL_SWAP_XY     = const(0b00100000)
MADCTL_SCAN_ORDER  = const(0b00010000)
MADCTL_RGB_BGR     = const(0b00001000)
MADCTL_HORIZ_ORDER = const(0b00000100)

REG_SWRESET   = const(0x01)
REG_TEOFF     = const(0x34)
REG_TEON      = const(0x35)
REG_MADCTL    = const(0x36)
REG_COLMOD    = const(0x3A)
REG_RAMCTRL   = const(0xB0)
REG_GCTRL     = const(0xB7)
REG_VCOMS     = const(0xBB)
REG_LCMCTRL   = const(0xC0)
REG_VDVVRHEN  = const(0xC2)
REG_VRHS      = const(0xC3)
REG_VDVS      = const(0xC4)
REG_FRCTRL2   = const(0xC6)
REG_PWCTRL1   = const(0xD0)
REG_PORCTRL   = const(0xB2)
REG_GMCTRP1   = const(0xE0)
REG_GMCTRN1   = const(0xE1)
REG_INVOFF    = const(0x20)
REG_SLPOUT    = const(0x11)
REG_DISPON    = const(0x29)
REG_GAMSET    = const(0x26)
REG_DISPOFF   = const(0x28)
REG_RAMWR     = const(0x2C)
REG_INVON     = const(0x21)
REG_CASET     = const(0x2A)
REG_RASET     = const(0x2B)
REG_PWMFRSEL  = const(0xCC)

# Codes for setting screen frame rate
FRAME_RATE_CONTROL = OrderedDict({
    119: 0x00,
    111: 0x01,
    105: 0x02,
    99: 0x03,
    94: 0x04,
    90: 0x05,
    86: 0x06,
    82: 0x07,
    78: 0x08,
    75: 0x09,
    72: 0x0A,
    69: 0x0B,
    67: 0x0C,
    64: 0x0D,
    62: 0x0E,
    60: 0x0F,
    58: 0x10,
    57: 0x11,
    55: 0x12,
    53: 0x13,
    52: 0x14,
    50: 0x15,
    49: 0x16,
    48: 0x17,
    46: 0x18,
    45: 0x19,
    44: 0x1A,
    43: 0x1B,
    42: 0x1C,
    41: 0x1D,
    40: 0x1E,
    39: 0x1F
})

# Codes for setting screen bit depth
PIXEL_FORMAT = OrderedDict({
    12: 0x03,   # 12 bits per pixel RGB444
    16: 0x05    # 16 bits per pixel RGB565
    # 18: 0x06    # 18 bits per pixel RGB666 (not implemented)
})


@micropython.viper
def rgba8888_to_rgb565(dst: ptr8, src: ptr8, size: int):
    """
    # Original implmentation: 74ms (measured with 320x240)
    for i in range(size):
        r = src[i * 4 + 0] >> 3
        g = src[i * 4 + 1] >> 2
        b = src[i * 4 + 2] >> 3
        rgb565 = (r << 11) | (g << 5) | b
        dst[i * 2 + 0] = (rgb565 >> 8) & 0xff
        dst[i * 2 + 1] = rgb565 & 0xff
    """

    # Fastest implementation so far: 59.2ms (measured with 320x240)
    di = 0
    for si in range(0, size << 2, 4):
        g = src[si + 1]
        dst[di] =     (src[si] & 0xF8)  | (g >> 5)              # R5, G3
        dst[di + 1] = ((g << 3) & 0xE0) | (src[si + 2] >> 3)    # G3, B5
        di += 2

@micropython.viper
def rgba8888_to_rgb565_mirror_y(dst: ptr8, src: ptr8, width: int, height: int):
    """
    # Original implmentation: 93.8ms (measured with 320x240)
    for x in range(width):
        for y in range(height):
            si = ((y * width) + x) * 4
            r = src[si + 0] >> 3
            g = src[si + 1] >> 2
            b = src[si + 2] >> 3
            rgb565 = (r << 11) | (g << 5) | b

            di = (((height - y - 1) * width) + x) * 2
            dst[di + 0] = (rgb565 >> 8) & 0xff
            dst[di + 1] = rgb565 & 0xff
    """

    # Fastest implementation so far: 62.4ms (measured with 320x240)
    for y in range(height):
        si = (y * width) << 2
        di = ((height - y - 1) * width) << 1

        for _ in range(width):
            g = src[si + 1]
            dst[di] = (src[si] & 0xF8) | (g >> 5)                   # R5, G3
            dst[di + 1] = ((g << 3) & 0xE0) | (src[si + 2] >> 3)    # G3, B5

            si += 4
            di += 2

@micropython.viper
def rgba8888_to_rgb565_mirror_x(dst: ptr8, src: ptr8, width: int, height: int):
    """
    # Original implmentation: 94.4ms (measured with 320x240)
    for x in range(width):
        for y in range(height):
            si = ((y * width) + x) * 4
            r = src[si + 0] >> 3
            g = src[si + 1] >> 2
            b = src[si + 2] >> 3
            rgb565 = (r << 11) | (g << 5) | b

            di = ((y * width) + (width - x - 1)) * 2
            dst[di + 0] = (rgb565 >> 8) & 0xff
            dst[di + 1] = rgb565 & 0xff
    """

    # Fastest implementation so far: 62.4ms (measured with 320x240)
    for y in range(height):
        si = ((y * width) + (width - 1)) << 2
        di = (y * width) << 1

        for _ in range(width):
            g = src[si + 1]
            dst[di] = (src[si] & 0xF8) | (g >> 5)                   # R5, G3
            dst[di + 1] = ((g << 3) & 0xE0) | (src[si + 2] >> 3)    # G3, B5

            si -= 4
            di += 2

@micropython.viper
def rgba8888_to_rgb565_rotate_180(dst: ptr8, src: ptr8, width: int, height: int):
    """
    # Original implmentation: 97.9ms (measured with 320x240)
    for x in range(width):
        for y in range(height):
            si = ((y * width) + x) * 4
            r = src[si + 0] >> 3
            g = src[si + 1] >> 2
            b = src[si + 2] >> 3
            rgb565 = (r << 11) | (g << 5) | b

            di = (((height - y - 1) * width) + (width - x - 1)) * 2
            dst[di + 0] = (rgb565 >> 8) & 0xff
            dst[di + 1] = rgb565 & 0xff
    """

    # Fastest implementation so far: 62.4ms (measured with 320x240)
    for y in range(height):
        si = ((y * width) + (width - 1)) << 2
        di = ((height - y - 1) * width) << 1

        for _ in range(width):
            g = src[si + 1]
            dst[di] = (src[si] & 0xF8) | (g >> 5)                   # R5, G3
            dst[di + 1] = ((g << 3) & 0xE0) | (src[si + 2] >> 3)    # G3, B5

            si -= 4
            di += 2


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


PIXEL_FUNCTIONS = {
    12: (rgba8888_to_rgb444_normal, rgba8888_to_rgb444_mirror, rgba8888_to_rgb444_rotate, rgba8888_to_rgb444_rotate_mirror),
    16: (None, None, None, None)
}

PIXEL_DOUBLE_FUNCTIONS = {
    12: (rgba8888_to_rgb444_double_normal, rgba8888_to_rgb444_double_mirror, rgba8888_to_rgb444_double_rotate, rgba8888_to_rgb444_double_rotate_mirror),
    16: (None, None, None, None)
}



class ST7789:
    def __init__(self, spi, cs, dc, bl, width=240, height=240, bitdepth=16, framerate=60, display=None):
        # When display is a spidisplay.SPIDisplay it owns the SPI bus and the
        # CS/DC pins, and the transform and transfer run in C. Otherwise the
        # Viper path drives a machine.SPI directly.
        self._display = display

        self.spi = spi
        self.CS = cs
        self.DC = dc
        if display is None:
            self.CS.init(machine.Pin.OUT)
            self.DC.init(machine.Pin.OUT)

        self.BL = bl
        self.BL.init(machine.Pin.OUT, value=False)

        self._width = width
        self._height = height
        self._bitdepth = bitdepth

        # Check the selected bit depth is valid and get the code. The Viper path
        # also needs the conversion functions and a full-frame buffer.
        try:
            bd_code = PIXEL_FORMAT[bitdepth]
            if display is None:
                self.__normal, self.__mirror, self.__rotate, self.__rotate_mirror = PIXEL_FUNCTIONS[bitdepth]
                self.__dbl_normal, self.__dbl_mirror, self.__dbl_rotate, self.__dbl_rotate_mirror = PIXEL_DOUBLE_FUNCTIONS[bitdepth]
                self.BUFFER = bytes((self._width * self._height * bitdepth) // 8)

        except KeyError as e:
            items = [str(bd) for bd in PIXEL_FORMAT]
            expected = items[0] if len(items) == 1 else ", ".join(items[:-1]) + f", or {items[-1]}"
            raise ValueError(f"{bitdepth} is not a valid bit depth. Expected {expected}.") from e

        # Check the selected frame rate is valid, and get the code
        try:
            fr_code = FRAME_RATE_CONTROL[framerate]
        except KeyError as e:
            items = [str(fr) for fr in FRAME_RATE_CONTROL]
            expected = items[0] if len(items) == 1 else ", ".join(items[:-1]) + f", or {items[-1]}"
            raise ValueError(f"{framerate} is not a valid frame rate. Expected {expected}.") from e

        self.setup(bd_code, fr_code)

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    def setup(self, bd_code, fr_code):
        self.command(REG_SWRESET)

        time.sleep(0.5)

        self.command(REG_TEON)
        self.command(REG_COLMOD, bd_code)   # 03 = 12-bit, 05 = 16-bit, 06 = 18-bit
        self.command(REG_PORCTRL, b"\x0c\x0c\x00\x33\x33")
        self.command(REG_LCMCTRL, b"\x2c")
        self.command(REG_VDVVRHEN, b"\x01")
        self.command(REG_VRHS, b"\x12")
        self.command(REG_VDVS, b"\x20")
        self.command(REG_PWCTRL1, b"\xa4\xa1")
        self.command(REG_FRCTRL2, fr_code)      # Framerate control
        self.command(REG_RAMCTRL, b"\x00\xc0")

        if self._width == 320 or self._height == 320:
            # 320 x 240
            self.command(REG_GCTRL, b"\x35")
            self.command(REG_VCOMS, b"\x1f")
            self.command(REG_GMCTRP1, b"\xD0\x08\x11\x08\x0C\x15\x39\x33\x50\x36\x13\x14\x29\x2D")
            self.command(REG_GMCTRN1, b"\xD0\x08\x10\x08\x06\x06\x39\x44\x51\x0B\x16\x14\x2F\x31")

        else:
            # 240 x 240
            self.command(REG_GCTRL, b"\x35")
            self.command(REG_VCOMS, b"\x1f")
            self.command(REG_GMCTRP1, b"\xD0\x08\x11\x08\x0C\x15\x39\x33\x50\x36\x13\x14\x29\x2D")
            self.command(REG_GMCTRN1, b"\xD0\x08\x10\x08\x06\x06\x39\x44\x51\x0B\x16\x14\x2F\x31")

        self.command(REG_INVON)
        self.command(REG_SLPOUT)
        self.command(REG_DISPON)

        if self.width == 320 or self.height == 320:
            self.command(REG_CASET, b"\x00\x00\x00\xEF")
            self.command(REG_RASET, b"\x00\x00\x01\x3F")
        else:
            self.command(REG_CASET, b"\x00\x00\x00\xf0")
            self.command(REG_RASET, b"\x00\x00\x00\xf0")

        self.command(REG_MADCTL, MADCTL_HORIZ_ORDER)

    def command(self, command, data=None):
        if self._display is not None:
            self._display.command(command, data)
            return

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
    def update(self, image, rotation=0, mirror=False, v_sync=False, bg_color=picovector.color.black, pixel_double=False):
        bg = bg_color.p & 0xffffffff

        r_index = rotation // 90
        if r_index < 0 or r_index > 3 or rotation % 90:     # Modulo check ensures rotation is exactly a multipe of 90
            raise ValueError(f"{rotation} is not a valid angle. Expected 0, 90, 180, or 270.")

        # Native path: the C module handles the transform, transfer, and TE wait
        if self._display is not None:
            self._display.update(image, self._width, self._height,
                                 bitdepth=self._bitdepth, rotation=rotation,
                                 mirror=1 if mirror else 0,
                                 pixel_double=1 if pixel_double else 0,
                                 bg=bg, ram_write=REG_RAMWR, v_sync=v_sync)
            self.BL.on()
            return

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

    def update_slow(self, image):
        mv = memoryview(image)

        self.DC.low()
        self.CS.low()

        self.spi.write(bytes((REG_RAMWR, )))

        self.DC.high()

        for y in range(image.height):
            for x in range(image.width):
                offset = (y * image.width + x) * 4
                r, g, b, a = mv[offset:offset + 4]
                r >>= 3
                g >>= 2
                b >>= 3
                rgb565 = struct.pack(">H", (r << 11) | (g << 5) | b)
                self.spi.write(rgb565)

        self.CS.high()

        self.BL.on()
