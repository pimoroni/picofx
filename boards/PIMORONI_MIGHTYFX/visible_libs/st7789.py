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

#FR_119HZ      = const(0x00)
#FR_111HZ      = const(0x01)
#FR_105HZ      = const(0x02)
#FR_99HZ       = const(0x03)
#FR_94HZ       = const(0x04)
FR_90HZ       = const(0x05)
#FR_86HZ       = const(0x06)
#FR_82HZ       = const(0x07)
#FR_78HZ       = const(0x08)
FR_75HZ       = const(0x09)
#FR_72HZ       = const(0x0A)
#FR_69HZ       = const(0x0B)
#FR_67HZ       = const(0x0C)
#FR_64HZ       = const(0x0D)
#FR_62HZ       = const(0x0E)
FR_60HZ       = const(0x0F)
#FR_58HZ       = const(0x10)
#FR_57HZ       = const(0x11)
#FR_55HZ       = const(0x12)
#FR_53HZ       = const(0x13)
#FR_52HZ       = const(0x14)
FR_50HZ       = const(0x15)
#FR_49HZ       = const(0x16)
#FR_48HZ       = const(0x17)
#FR_46HZ       = const(0x18)
#FR_45HZ       = const(0x19)
#FR_44HZ       = const(0x1A)
#FR_43HZ       = const(0x1B)
#FR_42HZ       = const(0x1C)
#FR_41HZ       = const(0x1D)
FR_40HZ       = const(0x1E)
#FR_39HZ       = const(0x1F)

@micropython.viper
def rgba8888_to_rgb565(dst: ptr8, src: ptr8, size: int):
    """
    # Original implmentation: 74ms
    for i in range(size):
        r = src[i * 4 + 0] >> 3
        g = src[i * 4 + 1] >> 2
        b = src[i * 4 + 2] >> 3
        rgb565 = (r << 11) | (g << 5) | b
        dst[i * 2 + 0] = (rgb565 >> 8) & 0xff
        dst[i * 2 + 1] = rgb565 & 0xff
    """

    # Fastest implementation so far: 59.2ms
    di = 0
    for si in range(0, size << 2, 4):
        g = src[si + 1]
        dst[di] =     (src[si] & 0xF8)  | (g >> 5)              # R5, G3
        dst[di + 1] = ((g << 3) & 0xE0) | (src[si + 2] >> 3)    # G3, B5
        di += 2

@micropython.viper
def rgba8888_to_rgb565_mirror_y(dst: ptr8, src: ptr8, width: int, height: int):
    """
    # Original implmentation: 93.8ms
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

    # Fastest implementation so far: 62.4ms
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
    # Original implmentation: 94.4ms
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

    # Fastest implementation so far: 62.4ms
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
    # Original implmentation: 97.9ms
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

    # Fastest implementation so far: 62.4ms
    for y in range(height):
        si = ((y * width) + (width - 1)) << 2
        di = ((height - y - 1) * width) << 1

        for _ in range(width):
            g = src[si + 1]
            dst[di] = (src[si] & 0xF8) | (g >> 5)                   # R5, G3
            dst[di + 1] = ((g << 3) & 0xE0) | (src[si + 2] >> 3)    # G3, B5

            si -= 4
            di += 2

@micropython.viper
def rgba8888_to_rgb444(dst: ptr8, src: ptr8, size: int):
    """
    # Original implmentation: 75ms
    for i in range(0, size, 2):
        i2 = i + 1

        r1 = src[i * 4 + 0] >> 4
        g1 = src[i * 4 + 1] >> 4
        b1 = src[i * 4 + 2] >> 4
        r2 = src[i2 * 4 + 0] >> 4
        g2 = src[i2 * 4 + 1] >> 4
        b2 = src[i2 * 4 + 2] >> 4

        rgb444_a = (r1 << 8) | (g1 << 4) | b1
        rgb444_b = (r2 << 8) | (g2 << 4) | b2
        i_2 = (i * 3) // 2
        dst[i_2 + 0] = (rgb444_a >> 4) & 0xff
        dst[i_2 + 1] = ((rgb444_a & 0xff) << 4) | (rgb444_b >> 8) & 0xff
        dst[i_2 + 2] = rgb444_b & 0xff
    """

    # Fastest implementation so far: 45.9ms
    di = 0
    for si in range(0, size << 2, 8):
        dst[di] = (src[si] & 0xf0) | (src[si + 1] >> 4)             # R1 | G1
        dst[di + 1] = (src[si + 2] & 0xf0) | (src[si + 4] >> 4)     # B1 | R2
        dst[di + 2] = (src[si + 5] & 0xf0) | (src[si + 6] >> 4)     # G2 | B2
        di += 3

@micropython.viper
def rgba8888_to_rgb444_mirror_y(dst: ptr8, src: ptr8, width: int, height: int):
    # Fastest implementation so far: 47.6ms
    for y in range(height):
        si = (y * width) << 2
        di = ((height - y - 1) * width) // 2 * 3

        for _ in range(0, width, 2):
            dst[di] = (src[si] & 0xf0) | (src[si + 1] >> 4)             # R1 | G1
            dst[di + 1] = (src[si + 2] & 0xf0) | (src[si + 4] >> 4)     # B1 | R2
            dst[di + 2] = (src[si + 5] & 0xf0) | (src[si + 6] >> 4)     # G2 | B2

            si += 8
            di += 3

@micropython.viper
def rgba8888_to_rgb444_mirror_x(dst: ptr8, src: ptr8, width: int, height: int):
    # Fastest implementation so far: 55.5ms
    for y in range(height):
        y_width = y * width
        di = (y_width) // 2 * 3

        for x in range(0, width, 2):
            x0 = width - 1 - x
            x1 = x0 - 1

            b0 = ((y_width + x0) << 2)
            b1 = ((y_width + x1) << 2)

            dst[di] = (src[b0] & 0xf0) | (src[b0 + 1] >> 4)             # R1 | G1
            dst[di + 1] = (src[b0 + 2] & 0xf0) | (src[b1] >> 4)         # B1 | R2
            dst[di + 2] = (src[b1 + 1] & 0xf0) | (src[b1 + 2] >> 4)     # G2 | B2

            di += 3

@micropython.viper
def rgba8888_to_rgb444_rotate_180(dst: ptr8, src: ptr8, width: int, height: int):
    # Fastest implementation so far: 55.6ms
    for y in range(height):
        src_y = height - 1 - y
        di = (y * width) // 2 * 3
        src_y_width = src_y * width

        for x in range(0, width, 2):
            x0 = width - 1 - x
            x1 = x0 - 1

            b0 = ((src_y_width + x0) << 2)
            b1 = ((src_y_width + x1) << 2)

            dst[di] =     (src[b0] & 0xf0)     | (src[b0 + 1] >> 4)
            dst[di + 1] = (src[b0 + 2] & 0xf0) | (src[b1] >> 4)
            dst[di + 2] = (src[b1 + 1] & 0xf0) | (src[b1 + 2] >> 4)

            di += 3


class ST7789:
    def __init__(self, spi, cs, dc, bl, width=240, height=240, bitdepth=16, framerate=40):
        self.spi = spi
        self.CS = cs
        self.CS.init(machine.Pin.OUT)

        self.DC = dc
        self.DC.init(machine.Pin.OUT)

        self.BL = bl
        self.BL.init(machine.Pin.OUT, value=False)

        self._width = width
        self._height = height

        if bitdepth == 12:
            bd_code = 0x03
            self.BUFFER = bytes(self._width * self._height * 3 // 2)    # * 2 for 16 bit
            self.__rgb_copy = rgba8888_to_rgb444
            self.__rgb_mirror_x = rgba8888_to_rgb444_mirror_x
            self.__rgb_mirror_y = rgba8888_to_rgb444_mirror_y
            self.__rgb_rotate_180 = rgba8888_to_rgb444_rotate_180
        else:
            bd_code = 0x05
            self.BUFFER = bytes(self._width * self._height * 2)     # 16 bit
            self.__rgb_copy = rgba8888_to_rgb565
            self.__rgb_mirror_x = rgba8888_to_rgb565_mirror_x
            self.__rgb_mirror_y = rgba8888_to_rgb565_mirror_y
            self.__rgb_rotate_180 = rgba8888_to_rgb565_rotate_180

        rates = {
            90: FR_90HZ,
            75: FR_75HZ,
            60: FR_60HZ,
            50: FR_50HZ,
            40: FR_40HZ
        }

        try:
            fr_code = rates[framerate]
        except KeyError as e:
            raise ValueError("{framerate} is not a valid framerate. Expected, 40, 50, 60, 75, or 90") from e

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
    def update(self, image, mirror_x=False, mirror_y=False, v_sync=False):
        if mirror_x:
            if mirror_y:
                # start = time.ticks_us()
                self.__rgb_rotate_180(memoryview(self.BUFFER), memoryview(image), self._width, self._height)
                # dt = time.ticks_diff(time.ticks_us(), start)
                # print("rgba8888_to_rgb444_rotate_180:", dt)
            else:
                # start = time.ticks_us()
                self.__rgb_mirror_x(memoryview(self.BUFFER), memoryview(image), self._width, self._height)
                # dt = time.ticks_diff(time.ticks_us(), start)
                # print("rgba8888_to_rgb444_mirror_x:", dt)
        else:
            if mirror_y:
                # start = time.ticks_us()
                self.__rgb_mirror_y(memoryview(self.BUFFER), memoryview(image), self._width, self._height)
                # dt = time.ticks_diff(time.ticks_us(), start)
                # print("rgba8888_to_rgb444_mirror_y:", dt)
            else:
                # start = time.ticks_us()
                self.__rgb_copy(memoryview(self.BUFFER), memoryview(image), self._width * self._height)
                # dt = time.ticks_diff(time.ticks_us(), start)
                # print("rgba8888_to_rgb444:", dt)

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
