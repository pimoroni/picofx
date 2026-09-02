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
    """A MemoryError from decoding, with the sizes a caller can act on.

    MicroPython's bare text gives the bytes and nothing else, not even which file. Says
    what was wanted and what was free, and why an animation wants so much, but not why
    the memory had gone: only the caller knows what else it is holding. An error that
    already explains itself, a GIF over picovector's own limit being the one, is handed
    back untouched.
    """
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
    """The clock and the traversal, over a sequence a subclass supplies.

    Reports which frame to draw and never draws it. The frame is a pure function of
    elapsed time over a fixed order, which is what makes pause, positioning and
    reverse() all origin shifts.

    A frame is one image of the source and a step is one place in the traversal. Under
    ping-pong the traversal plays out and back, so it visits most frames twice and turns
    at each end, where hold adds a dwell on top of the frame's own delay.

    first_as_last plays the first frame again as the traversal's last, for an animation
    drawn to loop, so the whole loop is travelled in each direction. That frame counts as
    one the source supplied, which is what makes frames, the order and positioning all
    take it. A forward loop has no last frame, so it refuses there.

    fps=None takes the source's own delays, a number names a rate and ignores them,
    and fps=False removes the clock so advance() drives instead. Without a clock the
    figures over the cycle all read None, and anything that would consult one raises,
    naming the setting it needs.
    """

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
            interval = int(1000 / fps) if fps > 0 else 0
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
        """The frame to play, readable in every state.

        A frame number, not a place in the traversal, so a ping-pong reports the same
        number on the way out and on the way back, and is_reversed() says which leg.
        """
        return self.__order[self.__current_step()]

    @property
    def image(self):
        """The frame to draw, readable in every state."""
        # The modulo serves first_as_last, whose closing frame is the source's first, and
        # is the identity without it.
        return self.__image_for(self.frame % self.__source_frames)

    def image_at(self, frame):
        """The image for any frame number, in the same numbering to_frame() takes.

        For a caller drawing a frame the player is not on, such as one player feeding two
        screens a fixed distance apart.
        """
        return self.__image_for(self.__frame_number(frame) % self.__source_frames)

    def has_advanced(self):
        """Whether the frame has moved since this last reported, the first call firing.

        Two players can share one condition: the position comes from the clock and not
        from a count of calls, so a call skipped by short-circuiting costs at most one
        redundant redraw.
        """
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
        """Turn around from where it stands.

        Under ping-pong this mirrors the step, both directions already sitting in the
        order, so at a turn it drops the balance of that dwell and carries on. On a
        plain order the order itself flips. The frame on screen keeps its own delay
        either way, so motion resumes at the usual rate.
        """
        step = self.__current_step()
        if self.__ping_pong:
            step = (2 * self.__frames - 2 - step) % len(self.__order)
        else:
            self.__order = tuple(reversed(self.__order))
            self.__build_delays()
            step = len(self.__order) - 1 - step

        self.__goto(step)

    def is_reversed(self):
        """Whether the frame number is decreasing.

        On a plain order, whether reverse() has flipped it. Under ping-pong, whether
        the walk is on the return leg, the far turn counting as outward until the walk
        crosses it.
        """
        if self.__ping_pong:
            return self.__current_step() >= self.__frames
        return self.__order[0] > self.__order[-1]

    def to_frame(self, frame):
        """Position on a frame by number, negatives counting from the end.

        A ping-pong order shows a frame twice, and this lands on the first of them, so
        to_frame(player.frame) is not always where it stood.
        """
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
        """Whether the frame is advancing, so False when paused and when done.

        Narrower than WavPlayer.is_playing(), which reports being engaged and stays
        True through a pause.
        """
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
        """The mean interval a frame is meant to show for, dwells excluded.

        A mean because a GIF's frames may each declare their own delay.
        """
        return self.__target_ms

    @property
    def target_fps(self):
        """The rate target_ms amounts to."""
        if self.__target_ms is None:
            return None
        return 1000 / self.__target_ms

    @property
    def measured_ms(self):
        """The last interval between frames actually reaching the caller.

        Read it where has_advanced() returns True, which is when it changes, or a
        polling caller sees only whichever interval was most recent.
        """
        return self.__measured_ms

    @property
    def measured_fps(self):
        """The rate the measured interval amounts to."""
        return 1000 / self.__measured_ms if self.__measured_ms > 0 else float("inf")


class GIFPlayer(ImagePlayer):
    """An animated GIF, played at the delays the file declares or at a named rate.

    The whole GIF decodes once at construction, so a frame costs nothing to reach.
    Frame delays are often whatever the exporting tool wrote, and a 2.8 inch pair
    presents a frame in about 78ms, so a file asking for more than that gets its
    speed and not its smoothness: measured_fps against target_fps says by how
    much.
    """

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
        """One frame's width in pixels, every frame being a cell of one grid.

        A GIF's frames share a size by design, which is what lets the player answer:
        SequencePlayer's images are free to differ, so it does not.
        """
        return self.__sheet.source.width // self.__sheet.cols

    @property
    def height(self):
        """One frame's height in pixels, as width is."""
        return self.__sheet.source.height // self.__sheet.rows

    @property
    def palette(self):
        """The colour table every frame shares, writable, or None for a truecolour GIF.

        The frames are cells carved from one image, so rewriting an entry recolours
        the whole animation at once.
        """
        return self.__sheet.source.palette

    @property
    def palette_size(self):
        """Entries in that table, 0 for a truecolour GIF."""
        return self.__sheet.source.palette_size


class SequencePlayer(ImagePlayer):
    """An animation held as one image file a frame, the sibling of GIFPlayer.

    Frames are PNG, JPEG or single-frame GIF, ordered by the numbers in their names so an
    export numbering past nine without padding still plays in order. An animated GIF is
    GIFPlayer's job, picovector compositing all of its frames into one stacked image.
    fps=None reads the delay each name declares in the form an ezgif export writes, a
    caller with delays from anywhere else passes timings, and fps=n names one rate for
    every frame.

    Every frame decodes into the heap at construction, which blocks for seconds and says
    so as it goes. Measured on a MightyFX: 8 truecolour frames of 320x320 cost 410KB each
    and 2.2 seconds to load, where 160 half-size palettised frames cost 20KB each and 6.1
    seconds. Palettised sources are worth roughly twenty times the animation for the same
    heap, so a long sequence wants exporting half size and indexed, drawn back with
    pixel_double.
    """

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
        """The file behind any frame number, as image_at() is to image.

        For a gallery listing what it holds, or a menu naming a frame to jump to.
        """
        return self.__paths[self.__frame_number(frame) % len(self.__paths)]
