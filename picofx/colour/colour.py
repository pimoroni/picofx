# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import rgb_from_hsv


class RGBFX:
    NAME = "rgb"
    CHROMATIC = True
    CALLED = None
    TAKES = ("red", "green", "blue")

    def __init__(self, red=255, green=255, blue=255):
        # Set through the properties, each of which reads the other two, so all
        # three exist before the first is written
        self.__red = self.__green = self.__blue = 0
        self.red = red
        self.green = green
        self.blue = blue

    @property
    def red(self):
        return self.__red

    @red.setter
    def red(self, value):
        self.__red = int(max(min(value, 255), 0))
        self.__rgb = (self.__red, self.__green, self.__blue)

    @property
    def green(self):
        return self.__green

    @green.setter
    def green(self, value):
        self.__green = int(max(min(value, 255), 0))
        self.__rgb = (self.__red, self.__green, self.__blue)

    @property
    def blue(self):
        return self.__blue

    @blue.setter
    def blue(self, value):
        self.__blue = int(max(min(value, 255), 0))
        self.__rgb = (self.__red, self.__green, self.__blue)

    def __call__(self):
        return self.__rgb


class HSVFX:
    NAME = "hsv"
    CHROMATIC = True
    CALLED = None
    TAKES = ("hue", "sat", "val")

    def __init__(self, hue=0.0, sat=1.0, val=1.0):
        self.__hue = hue
        self.__sat = sat
        self.__val = val
        self.__mix()

    def __mix(self):
        """Mix HSV into RGB, calculated whenever a setting changes."""
        r, g, b = rgb_from_hsv(self.__hue, self.__sat, self.__val)
        self.__rgb = (int(r * 255), int(g * 255), int(b * 255))

    @property
    def hue(self):
        return self.__hue

    @hue.setter
    def hue(self, value):
        self.__hue = value
        self.__mix()

    @property
    def sat(self):
        return self.__sat

    @sat.setter
    def sat(self, value):
        self.__sat = value
        self.__mix()

    @property
    def val(self):
        return self.__val

    @val.setter
    def val(self, value):
        self.__val = value
        self.__mix()

    def __call__(self):
        return self.__rgb
