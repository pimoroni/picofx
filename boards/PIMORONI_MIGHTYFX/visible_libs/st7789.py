# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# The ST7789 controller: register codes, the tables a panel is tuned from, and the
# bringup sequence. A second controller is a new module of the same shape.

import time
from collections import OrderedDict

MADCTL_ROW_ORDER   = const(0b10000000)
MADCTL_COL_ORDER   = const(0b01000000)
MADCTL_SWAP_XY     = const(0b00100000)
MADCTL_SCAN_ORDER  = const(0b00010000)
MADCTL_RGB_BGR     = const(0b00001000)
MADCTL_HORIZ_ORDER = const(0b00000100)

REG_SWRESET   = const(0x01)
REG_TEOFF     = const(0x34)
REG_TEON      = const(0x35)
REG_TESCAN    = const(0x44)
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
REG_SLPIN     = const(0x10)
REG_SLPOUT    = const(0x11)
REG_DISPON    = const(0x29)
REG_GAMSET    = const(0x26)
REG_DISPOFF   = const(0x28)
REG_RAMWR     = const(0x2C)
REG_INVON     = const(0x21)
REG_CASET     = const(0x2A)
REG_RASET     = const(0x2B)
REG_PWMFRSEL  = const(0xCC)

# The memory-write opcode a frame is streamed behind
RAM_WRITE = REG_RAMWR

# The TE opcodes the frame path drives itself, for a screen sharing its DC line. TE_MODE
# is TEON's parameter, V-blank only, sent since TEON alone leaves the mode bit as it was.
TE_ON = REG_TEON
TE_OFF = REG_TEOFF
TE_MODE = 0x00

# Scan rows a refresh spends whatever the panel shows, so a 240-row panel scans these too
CONTROLLER_ROWS = const(320)

# Memory columns the controller holds; with CONTROLLER_ROWS, the window covering any panel
CONTROLLER_COLUMNS = const(240)

# What setup() writes, back then front, in scan lines
PORCH = (12, 12)

# Scan slots per refresh at those porches; a screen whose porch has moved holds its own count
LINE_SLOTS = const(344)

# PSEN off, then the idle and partial porches, which normal mode never reads
PORCH_TAIL = b"\x00\x33\x33"


def set_porch(screen, back, front):
    # One porch line is one line time. The controller reads these as it enters blanking,
    # so a write lands on the frame after it and cannot truncate the one in flight.
    screen.command(REG_PORCTRL, bytes((back, front)) + PORCH_TAIL)

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

# Codes for setting screen bit depth. The controller also offers 18-bit RGB666 as
# 0x06, which the converter does not implement.
PIXEL_FORMAT = OrderedDict({
    12: 0x03,   # 12 bits per pixel RGB444
    16: 0x05    # 16 bits per pixel RGB565
})


def reset(screen):
    # Apart from setup() so several panels can be reset through one broadcast, the
    # settle paid once
    screen.command(REG_SWRESET)

    time.sleep(0.5)


def stop(screen):
    # The panel keeps its memory; left scanning, the frame would come back the moment
    # anything drove the backlight. Construction resets a panel, which wakes it.
    screen.command(REG_DISPOFF)
    screen.command(REG_SLPIN)


def setup(screen, width, height, bitdepth_code, framerate_code, te=True):
    # Takes a panel already through reset(). te sends TEON so the panel drives its
    # tearing-effect line; panels sharing a DC line take te=False, since TEOFF still
    # drives the line low and panels on one line would divide it.
    screen.command(REG_TEON if te else REG_TEOFF)
    screen.command(REG_COLMOD, bitdepth_code)   # 03 = 12-bit, 05 = 16-bit, 06 = 18-bit
    set_porch(screen, *PORCH)
    screen.command(REG_LCMCTRL, b"\x2c")
    screen.command(REG_VDVVRHEN, b"\x01")
    screen.command(REG_VRHS, b"\x12")
    screen.command(REG_VDVS, b"\x20")
    screen.command(REG_PWCTRL1, b"\xa4\xa1")
    screen.command(REG_FRCTRL2, framerate_code)
    screen.command(REG_RAMCTRL, b"\x00\xc0")

    if width == 320 or height == 320:
        # 320 x 240
        screen.command(REG_GCTRL, b"\x35")
        screen.command(REG_VCOMS, b"\x1f")
        screen.command(REG_GMCTRP1, b"\xD0\x08\x11\x08\x0C\x15\x39\x33\x50\x36\x13\x14\x29\x2D")
        screen.command(REG_GMCTRN1, b"\xD0\x08\x10\x08\x06\x06\x39\x44\x51\x0B\x16\x14\x2F\x31")

    else:
        # 240 x 240
        screen.command(REG_GCTRL, b"\x35")
        screen.command(REG_VCOMS, b"\x1f")
        screen.command(REG_GMCTRP1, b"\xD0\x08\x11\x08\x0C\x15\x39\x33\x50\x36\x13\x14\x29\x2D")
        screen.command(REG_GMCTRN1, b"\xD0\x08\x10\x08\x06\x06\x39\x44\x51\x0B\x16\x14\x2F\x31")

    screen.command(REG_INVON)
    screen.command(REG_SLPOUT)
    screen.command(REG_DISPON)

    # Inclusive end addresses; a window shorter than the frame wraps to the top of the panel
    last_column, last_row = width - 1, height - 1
    screen.command(REG_CASET, bytes((0, 0, last_column >> 8, last_column & 0xff)))
    screen.command(REG_RASET, bytes((0, 0, last_row >> 8, last_row & 0xff)))

    screen.command(REG_MADCTL, MADCTL_HORIZ_ORDER)
