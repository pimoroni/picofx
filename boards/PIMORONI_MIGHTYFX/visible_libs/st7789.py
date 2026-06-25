import time
import struct
import machine

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

@micropython.viper
def rgba8888_to_rgb565(dst: ptr8, src: ptr8, size: int):
    for i in range(size):
        r = src[i * 4 + 0] >> 3
        g = src[i * 4 + 1] >> 2
        b = src[i * 4 + 2] >> 3
        rgb565 = (r << 11) | (g << 5) | b
        dst[i * 2 + 0] = (rgb565 >> 8) & 0xff
        dst[i * 2 + 1] = rgb565 & 0xff


class ST7789:
    def __init__(self, spi, cs, dc, bl, width=240, height=240):
        self.spi = spi
        self.CS = cs
        self.CS.init(machine.Pin.OUT)

        self.DC = dc
        self.DC.init(machine.Pin.OUT)

        self.BL = bl
        self.BL.init(machine.Pin.OUT, value=False)

        self._width = width
        self._height = height
        self.BUFFER = bytes(width * height * 2)

        self.setup()

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    def setup(self):
        self.command(REG_SWRESET)

        time.sleep(0.5)

        self.command(REG_TEON)
        self.command(REG_COLMOD, b"\x05")
        self.command(REG_PORCTRL, b"\x0c\x0c\x00\x33\x33")
        self.command(REG_LCMCTRL, b"\x2c")
        self.command(REG_VDVVRHEN, b"\x01")
        self.command(REG_VRHS, b"\x12")
        self.command(REG_VDVS, b"\x20")
        self.command(REG_PWCTRL1, b"\xa4\xa1")
        self.command(REG_FRCTRL2, b"\x0f")
        self.command(REG_RAMCTRL, b"\x00\xc0")

        if self.width == 320 or self.height == 320:
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
    def update(self, image):
        rgba8888_to_rgb565(memoryview(self.BUFFER), memoryview(image), self._width * self._height)

        self.DC.low()
        self.CS.low()

        self.spi.write(bytes((REG_RAMWR, )))

        self.DC.high()

        self.spi.write(self.BUFFER)

        self.CS.high()

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
