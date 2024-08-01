# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import Cycling


class FlashFX(Cycling):
    def __init__(self, speed=1, flashes=2, window=0.5, phase=0.0, duty=0.5):
        super().__init__(speed)
        self.flashes = flashes
        self.window = window
        self.phase = phase
        self.duty = duty

    @property
    def flashes(self):
        return self.__flashes

    @flashes.setter
    def flashes(self, flashes):
        if not isinstance(flashes, int) or flashes <= 0:
            raise ValueError("flashes must be an integer greater than zero")

        self.__flashes = int(flashes)

    def __call__(self):
        offset = (self.__offset + self.phase) % 1.0
        if offset < self.window:
            percent = ((offset * self.__flashes) / self.window) % 1.0
            return 1.0 if percent < self.duty else 0.0
        return 0.0


class FlashSequenceFX(Cycling):
    def __init__(self, speed=1, length=1, flashes=1, window=1, phase=0.0, duty=0.5):
        super().__init__(speed)
        self.length = length
        self.flashes = flashes
        self.window = window
        self.phase = phase
        self.duty = duty

    @property
    def flashes(self):
        return self.__flashes

    @flashes.setter
    def flashes(self, flashes):
        if not isinstance(flashes, int) or flashes <= 0:
            raise ValueError("flashes must be an integer greater than zero")

        self.__flashes = int(flashes)

    def __call__(self, pos):
        def fx():
            nonlocal pos
            phase = pos / self.length
            offset = (self.__offset + self.phase + phase) % 1.0
            if offset < self.window:
                percent = ((offset * self.__flashes) / self.window) % 1.0
                return 1.0 if percent < self.duty else 0.0
            return 0.0
        return self, fx
