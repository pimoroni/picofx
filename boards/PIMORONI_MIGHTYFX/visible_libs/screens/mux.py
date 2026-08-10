# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# Panels addressed through a switch rather than a pin each, which is how a port
# reaches more screens than it has CS lines.

from machine import Pin


class ScreenMux:
    """Panels addressed by index through switched CS, and optionally DC, lines.

    select is the GPIOs driving the switch, least significant first, so three lines
    reach eight channels. count defaults to all of them, and is worth setting when
    fewer are wired.

    switch_dc needs an analog mux, since TE travels back along that line, and is
    what makes v_sync available. With CS alone switched a plain decoder serves, but
    DC stays shared and v_sync does not.
    """

    def __init__(self, select, switch_dc=False, count=None):
        self.__select = tuple(select)
        if not self.__select:
            raise ValueError("a selector needs at least one select line")

        for pin in self.__select:
            pin.init(Pin.OUT, value=False)

        self.__switch_dc = switch_dc

        channels = 1 << len(self.__select)
        if count is None:
            count = channels
        elif not 1 <= count <= channels:
            raise ValueError(f"{len(self.__select)} select lines address 1 to {channels} channels, not {count}.")

        self.__count = count
        self.__channel = None

    @property
    def count(self):
        return self.__count

    @property
    def switch_dc(self):
        return self.__switch_dc

    def select_channel(self, index):
        """Point the switch at one channel, which holds until the next call."""
        if not 0 <= index < self.__count:
            raise ValueError(f"{index} is not a valid channel. Expected 0 to {self.__count - 1}.")

        if index != self.__channel:
            for bit, pin in enumerate(self.__select):
                pin.value((index >> bit) & 1)
            self.__channel = index
