# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import Updateable


class SweepFX(Updateable):
    """A light that sweeps across the outputs and bounces back at each end. """

    NAME = "sweep"
    CALLED = "position"
    TAKES = ("speed", "length", "extent", "hold")

    def __init__(self, speed=1, length=1, extent=1.0, hold=0):
        self.speed = speed
        self.length = length
        self.extent = extent
        # Seconds of dwell at each end, one value for both or a (far, near) pair.
        # Counted in real time, so it does not shrink as the speed rises, which is
        # what lets it be set against a trail the outputs are leaving
        self.hold = hold
        # Counts a pass out and a pass back, so a speed means the same here as it
        # does for the effects that travel one way and wrap
        self.__offset_ms = 0
        self.__held_ms = 0
        self.__head = 0.0

    def __hold_ms(self, end):
        """The dwell owed at an end, which is every thousand of the offset."""
        hold = self.hold
        if isinstance(hold, (tuple, list)):
            # The far end is the odd thousand, the near end the even one
            hold = hold[0] if (end // 1000) % 2 else hold[1]
        return int(hold * 1000)

    def tick(self, delta_ms):
        if self.__held_ms > 0:
            self.__held_ms -= delta_ms
            if self.__held_ms > 0:
                return
            self.__held_ms = 0

        step = int(delta_ms * self.speed)
        offset = self.__offset_ms + step

        # The end this step is heading for, and whether it arrives. Nothing is clamped
        # where no dwell is set, so a sweep without one travels exactly as it always did
        reached = False
        if step > 0:
            end = (self.__offset_ms // 1000 + 1) * 1000
            reached = offset >= end
        elif step < 0:
            end = ((self.__offset_ms + 999) // 1000 - 1) * 1000
            reached = offset <= end

        if reached:
            held = self.__hold_ms(end)
            if held > 0:
                offset = end
                self.__held_ms = held

        self.__offset_ms = offset % 2000
        travel = self.__offset_ms
        if travel > 1000:
            travel = 2000 - travel
        self.__head = (travel * (self.length - 1)) / 1000

    def reset(self):
        self.__offset_ms = 0
        self.__held_ms = 0
        self.__head = 0.0

    def __call__(self, pos):
        def fx():
            nonlocal pos
            return max(0.0, 1.0 - abs(pos - self.__head) / self.extent)
        return self, fx
