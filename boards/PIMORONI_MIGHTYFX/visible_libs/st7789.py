import time
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


class ST7789:
    def __init__(self, display, bl, width=240, height=240, bitdepth=16, framerate=60):
        # display is a spidisplay.SPIDisplay. It owns the SPI bus and the CS/DC
        # pins, and the transform and transfer run in C.
        self._display = display

        self.BL = bl
        self.BL.init(machine.Pin.OUT, value=False)

        self._width = width
        self._height = height
        self._bitdepth = bitdepth

        # Check the selected bit depth is valid and get the code
        try:
            bd_code = PIXEL_FORMAT[bitdepth]
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

    def canvas(self, offset=0):
        """An SRAM-backed image sized to this screen.

        The GC heap is PSRAM, so a plain image() is read over XIP and conversion
        costs about twice as much per pixel. offset places the canvas within the
        SRAM region, for a second buffer that has to coexist with the first.
        """
        import spidisplay
        nbytes = self._width * self._height * 4    # RGBA8888
        return picovector.image(self._width, self._height,
                                spidisplay.buffer(nbytes, offset))

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

        # TODO: the 240 branch is off by one. These are inclusive end addresses, so
        # a 240 pixel panel wants 0xEF for a 0-based last index of 239, as the 320
        # branch correctly uses. Fix in step with
        # reference/st7789_viper_common.py, which carries the same values.
        if self.width == 320 or self.height == 320:
            self.command(REG_CASET, b"\x00\x00\x00\xEF")
            self.command(REG_RASET, b"\x00\x00\x01\x3F")
        else:
            self.command(REG_CASET, b"\x00\x00\x00\xf0")
            self.command(REG_RASET, b"\x00\x00\x00\xf0")

        self.command(REG_MADCTL, MADCTL_HORIZ_ORDER)

    def command(self, command, data=None):
        self._display.command(command, data)

    @micropython.native
    def update(self, image, rotation=0, mirror=False, v_sync=False, bg_color=picovector.color.black, pixel_double=False, offset=None):
        bg = bg_color.p & 0xffffffff

        r_index = rotation // 90
        if r_index < 0 or r_index > 3 or rotation % 90:     # Modulo check ensures rotation is exactly a multipe of 90
            raise ValueError(f"{rotation} is not a valid angle. Expected 0, 90, 180, or 270.")

        # The C module handles the transform, transfer, and TE wait
        self._display.update(image, self._width, self._height,
                             rotation=rotation,
                             mirror=1 if mirror else 0,
                             pixel_double=1 if pixel_double else 0,
                             bg=bg, offset=offset, v_sync=v_sync)
        self.BL.on()
