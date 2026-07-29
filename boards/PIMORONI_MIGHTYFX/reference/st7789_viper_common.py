"""ST7789 registers and panel bringup.

Shared by `st7789_viper_rgb444.py` and `st7789_viper_rgb565.py`, which differ only
in how they convert pixels. Bringup is identical between them, so it lives here
along with the register map it drives.

`const()` earns its keep now that `setup()` is in the same module, since the
compiler inlines each address at its point of use. The handful of names a driver
imports, its COLMOD value and `REG_RAMWR`, become ordinary globals on the far side
of the import, which costs one lookup per frame at most.
"""

import time
from collections import OrderedDict

# Command addresses, in address order, each followed by its parameter values where
# this driver family has names for them.
REG_SWRESET = const(0x01)       # Software reset
REG_SLPOUT = const(0x11)        # Sleep out
REG_INVOFF = const(0x20)        # Display inversion off
REG_INVON = const(0x21)         # Display inversion on
REG_GAMSET = const(0x26)        # Gamma set
REG_DISPOFF = const(0x28)       # Display off
REG_DISPON = const(0x29)        # Display on
REG_CASET = const(0x2A)         # Column address set
REG_RASET = const(0x2B)         # Row address set
REG_RAMWR = const(0x2C)         # Memory write
REG_TEOFF = const(0x34)         # Tearing effect line off
REG_TEON = const(0x35)          # Tearing effect line on

REG_MADCTL = const(0x36)        # Memory data access control
MADCTL_ROW_ORDER = const(0b10000000)
MADCTL_COL_ORDER = const(0b01000000)
MADCTL_SWAP_XY = const(0b00100000)
MADCTL_SCAN_ORDER = const(0b00010000)
MADCTL_RGB_BGR = const(0b00001000)
MADCTL_HORIZ_ORDER = const(0b00000100)

REG_COLMOD = const(0x3A)        # Interface pixel format
COLMOD_RGB444 = const(0x03)     # 12 bits per pixel
COLMOD_RGB565 = const(0x05)     # 16 bits per pixel
# COLMOD_RGB666 = const(0x06)   # 18 bits per pixel, no conversion kernels for it

REG_RAMCTRL = const(0xB0)       # RAM control
REG_PORCTRL = const(0xB2)       # Porch control
REG_GCTRL = const(0xB7)         # Gate control
REG_VCOMS = const(0xBB)         # VCOM setting
REG_LCMCTRL = const(0xC0)       # LCM control
REG_VDVVRHEN = const(0xC2)      # VDV and VRH command enable
REG_VRHS = const(0xC3)          # VRH set
REG_VDVS = const(0xC4)          # VDV set

REG_FRCTRL2 = const(0xC6)       # Frame rate control in normal mode
# Parameter values keyed by the frame rate they select. Only these rates are
# reachable, and only the lower nibble is set, so the dot inversion field keeps
# its reset value.
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

REG_PWMFRSEL = const(0xCC)      # PWM frequency selection
REG_PWCTRL1 = const(0xD0)       # Power control 1
REG_GMCTRP1 = const(0xE0)       # Positive voltage gamma control
REG_GMCTRN1 = const(0xE1)       # Negative voltage gamma control


def setup(display, colmod, framerate):
    """Bring a panel up, ready for pixel writes.

    display supplies command() plus width and height, so either driver can be
    passed straight in. colmod is one of the COLMOD_ values above, and framerate
    is a key of FRAME_RATE_CONTROL.

    Rotation and mirroring are left to the conversion kernels: MADCTL is set to
    MADCTL_HORIZ_ORDER only, so the panel stays in its native orientation.
    """
    try:
        fr_code = FRAME_RATE_CONTROL[framerate]
    except KeyError as e:
        items = [str(fr) for fr in FRAME_RATE_CONTROL]
        expected = items[0] if len(items) == 1 else ", ".join(items[:-1]) + f", or {items[-1]}"
        raise ValueError(f"{framerate} is not a valid frame rate. Expected {expected}.") from e

    display.command(REG_SWRESET)

    time.sleep(0.5)

    display.command(REG_TEON)
    display.command(REG_COLMOD, colmod)
    display.command(REG_PORCTRL, b"\x0c\x0c\x00\x33\x33")
    display.command(REG_LCMCTRL, b"\x2c")
    display.command(REG_VDVVRHEN, b"\x01")
    display.command(REG_VRHS, b"\x12")
    display.command(REG_VDVS, b"\x20")
    display.command(REG_PWCTRL1, b"\xa4\xa1")
    display.command(REG_FRCTRL2, fr_code)
    display.command(REG_RAMCTRL, b"\x00\xc0")

    display.command(REG_GCTRL, b"\x35")
    display.command(REG_VCOMS, b"\x1f")
    display.command(REG_GMCTRP1, b"\xD0\x08\x11\x08\x0C\x15\x39\x33\x50\x36\x13\x14\x29\x2D")
    display.command(REG_GMCTRN1, b"\xD0\x08\x10\x08\x06\x06\x39\x44\x51\x0B\x16\x14\x2F\x31")

    display.command(REG_INVON)
    display.command(REG_SLPOUT)
    display.command(REG_DISPON)

    # TODO: the 240 branch is off by one. These are inclusive end addresses, so a
    # 240 pixel panel wants 0xEF for a 0-based last index of 239, as the 320
    # branch correctly uses. Fix in step with visible_libs/st7789.py, which
    # carries the same values.
    if display.width == 320 or display.height == 320:
        display.command(REG_CASET, b"\x00\x00\x00\xEF")
        display.command(REG_RASET, b"\x00\x00\x01\x3F")
    else:
        display.command(REG_CASET, b"\x00\x00\x00\xf0")
        display.command(REG_RASET, b"\x00\x00\x00\xf0")

    display.command(REG_MADCTL, MADCTL_HORIZ_ORDER)
