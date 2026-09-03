# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# Players that turn a numbered sequence of images into an animation. A picovector
# spritesheet numbers a GIF's frames and keeps no clock, so the clock lives here:
# ImagePlayer holds the timing and a subclass answers only where a frame comes from,
# GIFPlayer from a GIF decoded at construction and SequencePlayer from a folder of
# image files. A player never touches a screen, so one update of a screen pair can
# carry two players' frames.

import logging
import os
import time

import picovector

# What picovector.image.load() decodes. A GIF here has to be a single frame, animated
# ones being GIFPlayer's job.
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif")


def __sized(count):
    """Kilobytes, rounded up, which is how picovector reports a GIF's own limit."""
    return "{}KB".format((count + 1023) // 1024)


def out_of_memory(path, error):
    """A MemoryError from decoding, restated with the sizes a caller can act on."""
    if "allocation failed" not in str(error):
        return error
    import gc
    gc.collect()
    wanted = 0
    for word in reversed(str(error).replace(",", " ").split()):
        if word.isdigit():
            wanted = int(word)
            break
    spare = gc.mem_free()
    if not wanted:
        room = "did not fit in the {} free".format(__sized(spare))
    elif wanted > spare:
        room = "needs {} and {} was free".format(__sized(wanted), __sized(spare))
    else:
        # More free than was asked for, so the total was never the problem: what is
        # left is in pieces smaller than the one piece a frame needs
        room = "needs {} in one piece and the {} free is in smaller pieces".format(
            __sized(wanted), __sized(spare))
    return MemoryError("{} {}. Every frame is stored while it plays.".format(path, room))


class ImagePlayer:
    """The clock and the traversal over a sequence a subclass supplies; reports the frame to draw."""

    def __init__(self, frames, timings, fps=None, loop=True, ping_pong=False, first_as_last=False,
                 hold=0, paused=False):
        if frames < 1:
            raise ValueError("a player needs at least one frame")
        if first_as_last and loop and not ping_pong:
            raise ValueError("first_as_last plays the first frame again at the end and a forward loop has no end, its last frame leading straight back into its first: set ping_pong=True to play out and back, or loop=False to come to rest on it")

        self.__source_frames = frames
        self.__frames = frames + 1 if first_as_last else frames
        self.__first_as_last = first_as_last
        self.__loop = loop
        self.__ping_pong = ping_pong
        self.__clocked = fps is not False

        if not self.__clocked:
            if hold:
                raise ValueError("hold waits in seconds and fps=False leaves the timing to the caller: name an fps, or leave hold out")
            if paused:
                raise ValueError("fps=False advances only when advance() is called, so there is nothing for paused=True to pause: name an fps, or leave paused out")
            self.__timings = None
        elif fps is None:
            if timings is None:
                raise ValueError("this source declares no frame delays, so fps=None has nothing to read: name an fps")
            self.__timings = tuple(timings)
            if min(self.__timings) < 0:
                raise ValueError("a frame delay is a wait in milliseconds, so it cannot be negative")
            # A GIF can declare zero for every frame, leaving a cycle of no length for the
            # walk to divide by.
            if sum(self.__timings) < 1:
                raise ValueError("every frame delay is zero, so there is no time for the animation to play in: name an fps instead")
            if first_as_last:
                self.__timings += (self.__timings[0],)
        else:
            interval = int(1000 / fps + 0.5) if fps > 0 else 0
            if interval < 1:
                raise ValueError(f"fps={fps} is under a millisecond a frame, which no screen can present: fps=None takes the source's delays and fps=False drives by hand")
            self.__timings = (interval,) * self.__frames

        # The steps a traversal turns around or repeats on, which are the only steps a
        # dwell can sit on. A single-frame source turns at step 0 twice, listed once.
        if ping_pong:
            if loop:
                self.__turns = (0, self.__frames - 1) if self.__frames > 1 else (0,)
            else:
                self.__turns = (self.__frames - 1,)
        else:
            self.__turns = (self.__frames - 1,) if loop else ()

        if hold and not self.__turns:
            raise ValueError("hold waits where an animation turns around and this one plays straight through: set loop=True to repeat, ping_pong=True to play back and forth, or call reverse() to turn around on command")
        if isinstance(hold, (tuple, list)) and not (loop and ping_pong):
            raise ValueError("two hold values need two turnarounds, which only a looping ping-pong has: pass one value, or set both loop=True and ping_pong=True")

        self.__after_in_ms, self.__after_out_ms = self.__hold_values(hold)

        self.__order = self.__build_order()
        self.__build_delays()

        self.__step = 0                # Caller-driven position, fps=False only
        self.__seen = None             # Last step signalled, so the first read fires
        self.__measured_ms = 0
        self.__signalled_at = None

        begin = self.__origin(0)
        self.__frozen_ms = begin if paused else None
        self.__start = time.ticks_add(time.ticks_ms(), -begin)

    @staticmethod
    def __hold_values(hold):
        """The dwells in ms, from one value for both turns or a 2-tuple as they are served."""
        if isinstance(hold, (tuple, list)):
            if len(hold) != 2:
                raise ValueError(f"hold takes one value or two, not {len(hold)}: two being the wait at the far end, then the wait back at the start")
            after_in, after_out = hold
        else:
            after_in = after_out = hold

        if after_in < 0 or after_out < 0:
            raise ValueError("hold waits in seconds, so it cannot be negative")

        return int(after_in * 1000), int(after_out * 1000)

    def __build_order(self):
        """The traversal as frame numbers, both ping-pong legs included.

        Listing the legs here keeps ping-pong out of the rest of the class, which then
        works through one list of frame numbers in the order they play.

        A looping ping-pong is 2n-2 steps, omitting the endpoints so neither shows for
        twice its delay as the lap wraps. A one-shot has no next lap to double against
        and is 2n-1, closing on frame 0 so an animation that plays in and out retracts
        fully.
        """
        order = tuple(range(self.__frames))
        if self.__ping_pong:
            if self.__loop:
                order += tuple(range(self.__frames - 2, 0, -1))
            else:
                order += tuple(range(self.__frames - 2, -1, -1))
        return order

    def __build_delays(self):
        """The per-step dwells for the current order, with the cycle and target they give."""
        if not self.__clocked:
            self.__delays = None
            self.__cycle_ms = None
            self.__target_ms = None
            return

        delays = [self.__timings[frame] for frame in self.__order]
        for step in self.__turns:
            delays[step] += self.__hold_on(step)

        self.__delays = tuple(delays)
        self.__cycle_ms = sum(delays)
        # Dwells come back out of the reported target, or a two second hold reads as a
        # slow frame rate instead of as a pause.
        held = sum(self.__hold_on(step) for step in self.__turns)
        self.__target_ms = (self.__cycle_ms - held) / len(self.__order)

    def __hold_on(self, step):
        """The dwell this step carries on top of its frame's own delay."""
        if step not in self.__turns:
            return 0
        return self.__after_out_ms if step == 0 else self.__after_in_ms

    def __image_for(self, frame):
        """The image for a frame number, which is all a subclass has to answer.

        Called on every image read, so a subclass loading on demand has to cache.
        """
        raise NotImplementedError("an ImagePlayer subclass supplies its own frames")

    def __frame_number(self, frame):
        """A frame number as a caller gives it, negatives counting from the end."""
        wanted = frame
        if frame < 0:
            frame += self.__frames
        if not 0 <= frame < self.__frames:
            repeat = ", the last being first_as_last playing frame 0 again" if self.__first_as_last else ""
            raise ValueError(f"there is no frame {wanted} in a player holding {self.__frames}{repeat}: frames are 0 to {self.__frames - 1}, or -1 to -{self.__frames} from the end")
        return frame

    def __needs_clock(self, what):
        if not self.__clocked:
            raise ValueError(f"{what} needs a frame rate and this player was built with fps=False: name an fps, or drive it with advance()")

    def __walk(self, position):
        """The step a position within the cycle falls on.

        The fall-through serves a one-shot resting at the very end of its cycle, which
        is the one position no step contains.
        """
        reached = 0
        step = 0
        # A counter, since enumerate() allocates a tuple per step and this runs
        # on every frame read
        for delay in self.__delays:
            reached += delay
            if position < reached:
                return step
            step += 1
        return len(self.__delays) - 1

    def __position(self):
        """Elapsed reduced to within one cycle, so a long pause stays in ticks range."""
        if self.__frozen_ms is not None:
            elapsed = self.__frozen_ms
        else:
            elapsed = time.ticks_diff(time.ticks_ms(), self.__start)

        if self.__loop:
            return elapsed % self.__cycle_ms
        return min(elapsed, self.__cycle_ms)

    def __current_step(self):
        """The step being played, whichever mode is driving."""
        if not self.__clocked:
            return self.__step
        return self.__walk(self.__position())

    def __origin(self, step):
        """Where to put the clock to place the player on a step.

        Past the step's dwell, a dwell being earned by arriving rather than granted to
        a player set down there. Construction uses this too, so the dwell back at the
        start is not spent before the first outward leg has run.
        """
        if not self.__clocked:
            return 0
        return sum(self.__delays[:step]) + self.__hold_on(step)

    def __goto(self, step):
        """Move to a step, keeping the pause state, so the next read reports it."""
        if self.__clocked:
            into = self.__origin(step)
            if self.__frozen_ms is not None:
                self.__frozen_ms = into
            else:
                self.__start = time.ticks_add(time.ticks_ms(), -into)
        else:
            self.__step = step

        self.__seen = None

    def __signal(self, step):
        """Record a frame reaching the caller, and the step it was on.

        An interval leaving a turn spent most of itself dwelling, so it is no frame rate
        and does not count. The step is recorded here because the measure reads the step
        it replaces, and the two must not come apart.
        """
        now = time.ticks_ms()
        if self.__signalled_at is not None and self.__seen not in self.__turns:
            self.__measured_ms = time.ticks_diff(now, self.__signalled_at)
        self.__signalled_at = now
        self.__seen = step

    @property
    def frames(self):
        """How many frames there are to play, first_as_last making it one more than the source."""
        return self.__frames

    @property
    def frame(self):
        """The frame number to play; a ping-pong reports the same number out and back."""
        return self.__order[self.__current_step()]

    @property
    def image(self):
        """The frame to draw, readable in every state."""
        # The modulo serves first_as_last, whose closing frame is the source's first, and
        # is the identity without it.
        return self.__image_for(self.frame % self.__source_frames)

    def image_at(self, frame):
        """The image for any frame number, in the numbering to_frame() takes."""
        return self.__image_for(self.__frame_number(frame) % self.__source_frames)

    def has_advanced(self):
        """Whether the frame has moved since this last reported, the first call firing."""
        self.__needs_clock("has_advanced()")

        step = self.__current_step()
        if step == self.__seen:
            return False

        self.__signal(step)
        return True

    def advance(self):
        """Move on one frame, for a player built with fps=False."""
        if self.__clocked:
            raise ValueError("advance() drives a player by hand and this one has a frame rate: read has_advanced() instead, or build it with fps=False")

        if self.__loop:
            self.__step = (self.__step + 1) % len(self.__order)
        else:
            self.__step = min(self.__step + 1, len(self.__order) - 1)

        self.__signal(self.__step)

    def reverse(self):
        """Turn around from where it stands."""
        step = self.__current_step()
        if self.__ping_pong:
            step = (2 * self.__frames - 2 - step) % len(self.__order)
        else:
            self.__order = tuple(reversed(self.__order))
            self.__build_delays()
            step = len(self.__order) - 1 - step

        self.__goto(step)

    def is_reversed(self):
        """Whether the frame number is decreasing: reverse() flipped it, or a ping-pong is on its way back."""
        if self.__ping_pong:
            return self.__current_step() >= self.__frames
        return self.__order[0] > self.__order[-1]

    def to_frame(self, frame):
        """Position on a frame by number, negatives counting from the end."""
        self.__goto(self.__order.index(self.__frame_number(frame)))

    def to_first(self):
        """Position on frame 0."""
        self.to_frame(0)

    def to_last(self):
        """Position on the last frame, which is the far end of a ping-pong."""
        self.to_frame(-1)

    def pause(self):
        """Hold the current frame. Positioning and reverse() still work while paused."""
        self.__needs_clock("pause()")
        if self.__frozen_ms is None:
            self.__frozen_ms = self.__position()

    def play(self):
        """Start, or carry on from a pause. Both are the same action here."""
        self.__needs_clock("play()")
        if self.__frozen_ms is not None:
            self.__start = time.ticks_add(time.ticks_ms(), -self.__frozen_ms)
            self.__frozen_ms = None

    def is_playing(self):
        """Whether the frame is advancing, so False when paused and when done."""
        self.__needs_clock("is_playing()")
        if self.__frozen_ms is not None:
            return False
        return self.__loop or self.__position() < self.__cycle_ms

    def is_done(self):
        """Whether a one-shot has finished its traversal in the current direction."""
        if self.__loop:
            raise ValueError("is_done() reports a one-shot finishing and this player loops: build it with loop=False, or leave the check out")

        if not self.__clocked:
            return self.__step == len(self.__order) - 1
        return self.__position() >= self.__cycle_ms

    @property
    def cycle_ms(self):
        """One full traversal, dwells and both ping-pong legs included."""
        return self.__cycle_ms

    @property
    def target_ms(self):
        """The mean interval a frame is meant to show for, dwells excluded."""
        return self.__target_ms

    @property
    def target_fps(self):
        """The rate target_ms amounts to."""
        if self.__target_ms is None:
            return None
        return 1000 / self.__target_ms

    @property
    def measured_ms(self):
        """The last interval between frames reaching the caller; it changes where has_advanced() is True."""
        return self.__measured_ms

    @property
    def measured_fps(self):
        """The rate the measured interval amounts to."""
        return 1000 / self.__measured_ms if self.__measured_ms > 0 else float("inf")


class GIFPlayer(ImagePlayer):
    """An animated GIF, decoded once at construction and played at its own delays or a named rate."""

    def __init__(self, path, fps=None, loop=True, ping_pong=False, first_as_last=False, hold=0,
                 paused=False):
        # Diagnostics only: one call of about a second, so there is no progress to report
        # and no wait worth announcing.
        logging.debug(f"> Loading {path} ...")
        started = time.ticks_ms()
        try:
            self.__sheet = picovector.spritesheet.load(path)
        except MemoryError as e:
            raise out_of_memory(path, e) from None
        logging.debug(f"> Loaded {self.__sheet.sprites} frames in {time.ticks_diff(time.ticks_ms(), started)}ms")

        super().__init__(self.__sheet.sprites, self.__sheet.timings, fps=fps, loop=loop,
                         ping_pong=ping_pong, first_as_last=first_as_last, hold=hold,
                         paused=paused)

    def __image_for(self, frame):
        return self.__sheet.sprite(frame)

    @property
    def width(self):
        """One frame's width in pixels, every frame of a GIF sharing a size."""
        return self.__sheet.source.width // self.__sheet.cols

    @property
    def height(self):
        """One frame's height in pixels, as width is."""
        return self.__sheet.source.height // self.__sheet.rows

    @property
    def palette(self):
        """The colour table every frame shares, writable, or None for a truecolour GIF."""
        return self.__sheet.source.palette

    @property
    def palette_size(self):
        """Entries in that table, 0 for a truecolour GIF."""
        return self.__sheet.source.palette_size


class SequencePlayer(ImagePlayer):
    """An animation held as one image file a frame, ordered by the numbers in their names."""

    def __init__(self, folder, fps=None, timings=None, loop=True, ping_pong=False,
                 first_as_last=False, hold=0, paused=False):
        names = [name for name in os.listdir(folder)
                 if name.lower().endswith(IMAGE_SUFFIXES)]
        if not names:
            raise ValueError(f"{folder} holds no images to play, looking for {', '.join(IMAGE_SUFFIXES)}")
        # Keys built once and sorted with the names, since sort(key=...) recomputes a key on
        # every comparison here: 160 names cost 8.5 seconds that way against under one.
        keyed = sorted((self.__numbers_in(name), name) for name in names)
        names = [name for _, name in keyed]

        if timings is not None and fps is not None:
            raise ValueError("an fps and timings are two ways to say the frame delays: name one of them, or neither to read the delays the file names declare")

        if timings is None and fps is None:
            declared = [self.__delay_in(name) for name in names]
            if None in declared:
                raise ValueError(f"the names in {folder} do not all declare a delay, so fps=None has nothing to read: name an fps, or pass timings with one delay a frame")
            timings = tuple(declared)
        elif timings is not None and len(timings) != len(names):
            raise ValueError(f"{folder} holds {len(names)} images and timings gives {len(timings)} delays: pass one a frame, in the order they play, which is by the numbers in their names")

        self.__paths = tuple(f"{folder}/{name}" for name in names)
        try:
            self.__images = self.__load(folder, names, self.__paths)
        except MemoryError as e:
            raise out_of_memory(folder, e) from None

        super().__init__(len(self.__images), timings, fps=fps, loop=loop,
                         ping_pong=ping_pong, first_as_last=first_as_last, hold=hold,
                         paused=paused)

    @staticmethod
    def __numbers_in(name):
        """The numbers in a name, so frame_10 sorts after frame_9 and not after frame_1.

        Lexicographic order is wrong for any export past nine frames, and wrong silently:
        the animation simply plays in the wrong order.
        """
        found = []
        digits = ""
        for character in name:
            if "0" <= character <= "9":
                digits += character
            elif digits:
                found.append(int(digits))
                digits = ""
        if digits:
            found.append(int(digits))
        return found

    @staticmethod
    def __delay_in(name):
        """The delay in ms a frame's name declares, or None.

        Reads the form an ezgif export writes, frame_3_delay-0.08s.png. Each name gives its
        own frame's delay, so a sequence that holds one frame longer keeps that timing.
        """
        _, found, rest = name.partition("delay-")
        if not found:
            return None

        seconds, found, _ = rest.partition("s")
        if not found:
            return None
        try:
            return int(float(seconds) * 1000)
        except ValueError:
            return None

    @staticmethod
    def __load(folder, names, paths):
        """Decode every frame, saying so as it goes since this blocks for seconds.

        A line of dots at LOG_INFO, a line a frame at LOG_DEBUG, the measured total either
        way, and no estimate: cost a frame spans fivefold with image size, and the first
        frames load about three times faster than the rest while the heap is still empty.
        """
        count = len(paths)
        # Dots and per-frame lines are alternatives, not levels of the same thing: info()
        # prints at LOG_DEBUG too, so a dot would land in the middle of a line.
        dotted = logging.level < logging.LOG_DEBUG

        logging.info(f"> Loading {count} frames from {folder}", end=" " if dotted else "\n")

        every = max(1, count // 20)     # at most twenty dots, however long the folder
        started = time.ticks_ms()
        images = []
        for index, path in enumerate(paths):
            images.append(picovector.image.load(path))
            logging.debug(f"  {index + 1}/{count} {names[index]}")
            if dotted and (index + 1) % every == 0:
                logging.info(".", end="")

        took = time.ticks_diff(time.ticks_ms(), started)
        logging.info(f"  {took}ms" if dotted else f"> Loaded {count} frames in {took}ms")

        return tuple(images)

    def __image_for(self, frame):
        return self.__images[frame]

    @property
    def path(self):
        """The file the frame on show came from, beside image and frame."""
        return self.__paths[self.frame % len(self.__paths)]

    def path_at(self, frame):
        """The file behind any frame number, as image_at() is to image."""
        return self.__paths[self.__frame_number(frame) % len(self.__paths)]
