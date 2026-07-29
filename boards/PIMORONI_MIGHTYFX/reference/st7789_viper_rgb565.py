"""ST7789 driver for 16-bit panels, converting pixels in pure MicroPython.

Reference implementation. MightyFX drives its panels through the spidisplay C
module instead, so this is not shipped to the board and nothing in the firmware
imports it. It is kept as a worked example of `@micropython.viper`, and as the
starting point for a board that has no spidisplay module built in.

It depends on nothing outside the standard MicroPython library: `machine.SPI`,
three GPIOs, and a source object exposing the buffer protocol plus `width` and
`height`. So it drops onto any board with an ST7789 panel. Conversion runs on the
CPU into a full-frame staging buffer, which is then written in one blocking
`spi.write()`.

**Start from `st7789_viper_rgb444.py` unless you specifically need 16-bit
colour.** These four kernels are the earlier, narrower set, and the gap is not
worth closing at this point:

| | this driver | the RGB444 driver |
| --- | --- | --- |
| rotation | 0 and 180 | 0, 90, 180 and 270 |
| mirror | yes | yes |
| pixel doubling | no | yes |
| source smaller than the panel | no, sizes must match | yes, centred or placed |
| background fill | no | yes |
| odd source width | no | yes |

They are kept because they are the clearest reading of the technique: one packing
expression, no placement arithmetic, and each carrying the plain-Python form it
replaces plus its measured timing. Read these first, then the RGB444 set.

Its other limit, shared with the RGB444 driver, is that conversion and transfer
are strictly sequential, so a frame costs convert plus transfer. The C module
overlaps them and is roughly twice as fast for the same panel.

Tearing effect is read on the DC line, as MightyFX wires it. A panel with a
dedicated TE pin needs `v_sync` changing to poll that pin instead.
"""

import machine
from st7789_viper_common import COLMOD_RGB565, REG_RAMWR, setup


# The four kernels. Each takes a source that matches the destination size, so
# there is no placement arithmetic and no background fill. Every one carries the
# plain-Python form it replaces plus its measured timing.


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


class ST7789_RGB565:
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

        # One pixel per two bytes
        self.BUFFER = bytearray(self._width * self._height * 2)

        setup(self, COLMOD_RGB565, framerate)

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
    def update(self, image, rotation=0, mirror=False, v_sync=False):
        """Convert an image and write it to the panel.

        image is anything supporting the buffer protocol with width and height
        attributes, holding RGBA8888 pixels. A picovector image works, as does a
        bytearray wrapped in a class exposing those two attributes. It must be
        exactly the size of the panel: these kernels have no placement or
        background fill, so there is nothing sensible to do with a mismatch.

        rotation is 0 or 180 only, and mirror flips horizontally. For 90 and 270,
        pixel doubling, or a source of any other size, use the RGB444 driver.
        """
        if image.width != self._width or image.height != self._height:
            raise ValueError(f"image is {image.width}x{image.height}, "
                             f"expected {self._width}x{self._height}.")

        mv_dst = memoryview(self.BUFFER)
        mv_src = memoryview(image)

        # start = time.ticks_us()
        if rotation == 0:
            if mirror:
                rgba8888_to_rgb565_mirror_x(mv_dst, mv_src, self._width, self._height)
            else:
                rgba8888_to_rgb565(mv_dst, mv_src, self._width * self._height)
        elif rotation == 180:
            # 180 degrees reverses both axes, so mirroring it leaves only the
            # vertical flip
            if mirror:
                rgba8888_to_rgb565_mirror_y(mv_dst, mv_src, self._width, self._height)
            else:
                rgba8888_to_rgb565_rotate_180(mv_dst, mv_src, self._width, self._height)
        else:
            raise ValueError(f"{rotation} is not a valid angle. Expected 0 or 180.")
        # dt = time.ticks_diff(time.ticks_us(), start)
        # print("convert:", dt)

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
