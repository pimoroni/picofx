# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# Holding a loop to a rate, and knowing when a thing is next due. Both carry a deadline
# forward with ticks_add rather than measuring a duration from now, which is what stops
# one pass's cost being paid again on the next.

import time


def rate_ms(interval, fps):
    """One rate, given as seconds between or as a count per second, in milliseconds.

    Floored at a millisecond, so a rate too fast to hold becomes the fastest that can
    be rather than no wait at all. None for both is no rate.
    """
    if interval is not None and fps is not None:
        raise ValueError("an interval and an fps are two ways to say one rate: name one of them")

    if fps is not None:
        if fps <= 0:
            raise ValueError("an fps must be positive")
        interval = 1.0 / fps
    elif interval is None:
        return None

    if interval <= 0:
        raise ValueError("an interval must be positive")

    return max(1, int(1000.0 * interval + 0.5))


class Pacer:
    """A loop's clock: how long it has been running, and how fast it may go round.

    An interval in seconds or an fps holds the loop to that rate, hold() spending
    whatever is left of each pass. Neither waits for anything, which suits a loop
    drawing its motion from elapsed rather than stepping it per frame.

    Where a pass overruns, whole intervals are dropped rather than sprinted, so the
    rate asked for is never exceeded to make up time. delta is the pass just ended,
    its wait included, so a delta above the interval is the loop saying it cannot hold
    what it was given.

    Measured at about ten milliseconds of jitter on a loaded board, sleep_ms being
    what it waits with. Under that a hardware Timer holds a rate better, which is what
    EffectPlayer uses.
    """

    def __init__(self, interval=None, fps=None):
        self.__interval_ms = None
        self.restart(interval, fps)

    def restart(self, interval=None, fps=None):
        """Begin again, as if the loop had just been entered, on a new rate if given."""
        if interval is not None or fps is not None:
            self.__interval_ms = rate_ms(interval, fps)

        now = time.ticks_ms()
        self.__started = now
        self.__last = now
        self.__delta_ms = 0
        self.__measured_ms = 0
        if self.__interval_ms is not None:
            self.__due = time.ticks_add(now, self.__interval_ms)

    @property
    def elapsed(self):
        """Milliseconds since the loop began, or since the last restart()."""
        return time.ticks_diff(time.ticks_ms(), self.__started)

    @property
    def delta(self):
        """Milliseconds the pass is counted as having taken, for scaling movement by.

        Whole intervals where a rate was named, so it holds steady while the rate does
        and steps where a pass overran, and movement driven by it never jitters on the
        wander a real reading carries. With no rate named there is no grid to count, so
        it is the measured time.
        """
        return self.__delta_ms

    def measured_ms(self):
        """Milliseconds the pass that just ended really took, its wait included."""
        return self.__measured_ms

    def measured_fps(self):
        """The rate the loop is holding, from the last pass."""
        return 1000 / self.__measured_ms if self.__measured_ms > 0 else float("inf")

    def hold(self):
        """Close the pass, waiting out the rest of the interval if there is one."""
        consumed = 1
        if self.__interval_ms is not None:
            behind = time.ticks_diff(time.ticks_ms(), self.__due)
            if behind < 0:
                time.sleep_ms(-behind)
                self.__due = time.ticks_add(self.__due, self.__interval_ms)
            else:
                # Counted rather than stepped through: a pass that stalled for seconds
                # against a millisecond interval would otherwise advance thousands of times
                consumed = behind // self.__interval_ms + 1
                self.__due = time.ticks_add(self.__due, consumed * self.__interval_ms)

        now = time.ticks_ms()
        self.__measured_ms = time.ticks_diff(now, self.__last)
        self.__last = now

        if self.__interval_ms is None:
            self.__delta_ms = self.__measured_ms
        else:
            self.__delta_ms = consumed * self.__interval_ms


class Roller:
    """When one thing is next due. A loop holds a Pacer, and one of these per thing.

    An interval in seconds, or an fps, is the length it works in. advance() carries the
    deadline on from itself, so a thing due on a beat stays evenly spaced however late
    it is read; restart() starts the length again from now, for a hold that runs from
    where the last one ended. reached() asks, and changes nothing.
    """

    def __init__(self, interval=None, fps=None):
        self.__interval_ms = None
        self.restart(interval, fps)

    def restart(self, interval=None, fps=None):
        """Start the length again from now, on a new one if given.

        With no length to work in the deadline goes to now, so it is due at once.
        """
        if interval is not None or fps is not None:
            self.__interval_ms = rate_ms(interval, fps)

        self.__ticks = time.ticks_ms()
        if self.__interval_ms is not None:
            self.advance_ms(self.__interval_ms)

    def advance(self, seconds=None):
        """Move the deadline on, by a length in seconds or by the one it works in.

        The length it works in carries it to the next moment still ahead, so beats a
        stall went past are dropped rather than fired off in a burst to catch up, as a
        Pacer drops the passes it missed. A named length is added as it is given.
        """
        if seconds is not None:
            self.advance_ms(1000.0 * seconds + 0.5)
            return

        if self.__interval_ms is None:
            raise ValueError("this roller works in no length, so advance() needs one: advance(seconds), or restart(seconds) to set it")

        behind = time.ticks_diff(time.ticks_ms(), self.__ticks)
        beats = behind // self.__interval_ms + 1 if behind >= 0 else 1
        self.advance_ms(beats * self.__interval_ms)

    def advance_ms(self, ms):
        """Move the deadline on by a length in milliseconds."""
        if ms < 0:
            raise ValueError("advance length must be non-negative")

        self.__ticks = time.ticks_add(self.__ticks, int(ms))

    def reached(self):
        """Whether the deadline has arrived, leaving it where it is."""
        return time.ticks_diff(time.ticks_ms(), self.__ticks) >= 0
