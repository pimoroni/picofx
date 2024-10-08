# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import CyclingAction


# Derived from maltheim's example: https://forums.pimoroni.com/t/rgb-led-kit-for-tiny-fx-tutorial/25293/15
class RGBBlinkFX(CyclingAction):
    """
    Blinks the RGB LED according to the speed, phase and duty cycle.

    The colour argument is a single tuple of the form (R,G,B), or a
    list of such tuples. A None colour argument defaults to red.

    :param:   colour  an RGB tuple as the colour or colours of the blink
    :param:   speed   the speed of the blink, where 1.0 is 1 second, 0.5 is 2 seconds, etc.
    :param:   phase   the phase of the blink
    :param:   duty    the duty cycle of the blink
    """
    def __init__(self, colour=None, speed=1, phase=0.0, duty=0.5):
        super().__init__(speed)
        self.phase = phase
        self.duty = duty
        self.__colours = []
        self.__index = 0
        if colour is None:
            self.__colours.append((255, 0, 0))
        elif isinstance(colour, tuple) and len(colour) == 3:
            self.__colours.append(colour)
        elif isinstance(colour, list):
            self.__colours.extend(colour)
        else:
            raise TypeError("colour is not a supported type. Expected a tuple of 3 numbers, a list of tuples, or None.")

    def __call__(self):
        percent = (self.__offset + self.phase) % 1.0
        if percent < self.duty:
            colour = self.__colours[self.__index]
            return int(colour[0]), int(colour[1]), int(colour[2])
        else:
            return 0, 0, 0

    def next(self):
        self.__index = (self.__index + 1) % len(self.__colours)

    def prev(self):
        self.__index = (self.__index - 1) % len(self.__colours)
