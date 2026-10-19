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
        # does for the effects that travel one way and wrap. In microseconds, since a
        # slow speed moves less than a millisecond a tick
        self.__offset_us = 0
        self.__held_us = 0
        self.__head = 0.0

    def __hold_us(self, end):
        """The dwell owed at an end, which is every million of the offset."""
        hold = self.hold
        if isinstance(hold, (tuple, list)):
            # The far end is the odd million, the near end the even one
            hold = hold[0] if (end // 1_000_000) % 2 else hold[1]
        return int(hold * 1_000_000)

    def tick(self, delta_ms):
        elapsed_us = delta_ms * 1000
        if self.__held_us > 0:
            self.__held_us -= elapsed_us
            if self.__held_us > 0:
                return
            # The hold ended partway through this tick, which moves for what is left of it
            elapsed_us = -self.__held_us
            self.__held_us = 0

        step = int(elapsed_us * self.speed)
        offset = self.__offset_us + step

        # The end this step is heading for, and whether it arrives. Nothing is clamped
        # where no dwell is set, so a sweep without one travels exactly as it always did
        reached = False
        if step > 0:
            end = (self.__offset_us // 1_000_000 + 1) * 1_000_000
            reached = offset >= end
        elif step < 0:
            end = ((self.__offset_us + 999_999) // 1_000_000 - 1) * 1_000_000
            reached = offset <= end

        if reached:
            # The hold starts as the end is reached, partway through this tick, so the
            # time spent past the end counts towards it
            held = self.__hold_us(end) - elapsed_us * abs(offset - end) // abs(step)
            if held > 0:
                offset = end
                self.__held_us = held

        self.__offset_us = offset % 2_000_000
        # Whole milliseconds, so the product below stays a small int on a long strip
        travel = self.__offset_us // 1000
        if travel > 1000:
            travel = 2000 - travel
        self.__head = (travel * (self.length - 1)) / 1000

    def reset(self):
        self.__offset_us = 0
        self.__held_us = 0
        self.__head = 0.0

    def __call__(self, pos):
        def fx():
            nonlocal pos
            return max(0.0, 1.0 - abs(pos - self.__head) / self.extent)
        return self, fx
