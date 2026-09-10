# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# The common base a single screen and a broadcast group are both constructed on. It
# holds the placement settings a frame follows, hands out canvases in fast SRAM, sends
# or stages a frame, and picks which screen's tearing-effect signal that frame waits on.
# The tearing-margin arithmetic a pair and a group price a hold with is here too. Two
# methods are native, the thin wrappers a frame passes through, paying 1.6x to 5.6x.

import spidisplay

# A dither moves a member one porch line either way
DITHER_EXTENT_LINES = 1


class Tile:
    """The values tile= takes, repeating a source along an axis."""
    OFF = 0         # No repeat, which False also means
    REPEAT = 1      # The source repeated, which True also means
    MIRROR = 2      # Every other repeat reversed, so each seam is a reflection


def __check_rotation(rotation):
    r_index = rotation // 90
    if r_index < 0 or r_index > 3 or rotation % 90:
        raise ValueError(f"{rotation} is not a valid angle. Expected 0, 90, 180, or 270.")


def __fold(delta, period):
    # Fold a difference onto half a period either way, keeping the sign, so a phase
    # error reads as the short way round. The boundary is exactly half, a booking
    # carrying a fraction of a line, so a floored half would fold the wrong way
    delta %= period
    return delta - period if delta > period / 2 else delta


def __tightest_margin(screens, pads, line_us, wire_us):
    # Margin is the scan lines a write leaves uncovered, judged in each member's line
    # time. Returns (tightest index, margins in us, the dither's range in us).
    margins = [screen.__line_slots + pad + screen.height - wire / line
               for screen, pad, line, wire in zip(screens, pads, line_us, wire_us)]
    tightest = margins.index(min(margins))
    margins_us = tuple(margin * line for margin, line in zip(margins, line_us))

    # Doubled, the dither reaching either way, and in the tightest member's line time
    return tightest, margins_us, 2 * DITHER_EXTENT_LINES * line_us[tightest]


class ScreenBase:
    """What a Screen and a ScreenGroup share. Construct one of those."""

    def __init__(self, port, display, width, height, bitdepth, backlight,
                 te, v_sync, reserve, members=None, shared_te=False,
                 leader=None, rotation=0, mirror=False, reveal_together=False):
        __check_rotation(rotation)
        self.__port = port
        self.__display = display
        self.__width = width
        self.__height = height
        self.__bitdepth = bitdepth
        self.__backlight = backlight
        self.__te = te                  # Whether a tearing-effect signal is read, which v_sync needs
        self.__v_sync = v_sync          # Whether a frame waits unless it sets its own
        self.__reserve = reserve

        self.__members = members
        self.__canvases = {}
        self.__pair = None              # The ScreenPair holding this screen off its own rate, the follower alone
        self.__group = None             # The ScreenGroup this screen is a member of, if any
        self.__subset_of = None         # The group a subset narrows, so it writes its members only
        self.__subset_displays = None   # The members' displays, built once per subset

        self.__shared_te = shared_te    # Whether this panel's TE reaches a line others share
        self.__leader = leader          # The screen whose TE is switched onto the shared line, None to switch nothing
        self.__leader_source = None     # A group whose current leader an inheriting subset waits on
        self.__synced_frame = None      # The screen the last frame's wait ended on, if any
        self.__sync_delay_us = 0        # How long a write trails the wait, set by a holding group

        self.__rotation = rotation
        self.__mirror = bool(mirror)
        self.__reveal_together = bool(reveal_together)

    @property
    def port(self):
        """The SP/CE connector this screen is on, which a hub's screens all share."""
        return self.__port

    @property
    def backlight(self):
        """The port's backlight, or None where the screen declined it."""
        return self.__backlight

    @property
    def screens(self):
        """A broadcast group's member screens, or this screen on its own."""
        return self.__members if self.__members is not None else (self,)

    @property
    def width(self):
        return self.__width

    @property
    def height(self):
        return self.__height

    @property
    def rotation(self):
        """The angle a frame is placed at unless it sets its own."""
        return self.__rotation

    @property
    def mirror(self):
        """Whether a frame is flipped left to right unless it sets its own."""
        return self.__mirror

    @property
    def reveal_together(self):
        """Whether the port's backlight waits for every screen asking for it."""
        return self.__reveal_together

    def brightness(self, value):
        """Set the brightness of the backlight, from 0.0 to 1.0."""
        if self.__backlight is None:
            raise ValueError("this screen has no backlight to set, so its brightness is whatever "
                             "the assembly ties it to")

        self.__backlight.brightness(value)

    def canvas(self, width=None, height=None, offset=None):
        """Claim an image in fast SRAM, sized to this screen by default and reused per size.
        offset= instead places one by hand at a byte offset, outside the claims."""
        width = self.__width if width is None else width
        height = self.__height if height is None else height
        if width < 1 or height < 1:
            raise ValueError("a canvas needs a positive width and height")

        # Imported where it is needed, so the frame path stands on spidisplay alone
        import picovector

        nbytes = width * height * 4    # RGBA8888
        if offset is not None:
            return picovector.image(width, height, spidisplay.buffer(nbytes, offset))

        canvas = self.__canvases.get((width, height))
        if canvas is None:
            canvas = picovector.image(width, height, spidisplay.buffer(nbytes))
            self.__canvases[(width, height)] = canvas

        return canvas

    def __drawn(self, to=None, keep_dark=False):
        # An undrawn panel is black, cleared at bringup, so the backlight can light on
        # the first frame anywhere. keep_dark returns the wait in ms instead of lighting,
        # for a caller revealing several ports together.
        if self.__backlight is None:
            return None

        return self.__backlight.__frame_shown(self, to, keep_dark)

    def __command(self, command, data=None):
        self.__display.command(command, data)

    @micropython.native
    def __write_targets(self, to):
        # Nothing named writes the display's own targets, which for a subset is its
        # members alone and for anything else is every panel the display covers
        if to is None:
            return self.__subset_displays

        members = self.screens
        for screen in to:
            if screen not in members:
                raise ValueError(f"{screen} is not one of these screens, so a frame cannot be sent to it")

        return tuple(screen.__display for screen in to)

    def __sync_screen(self, v_sync, to):
        # A leader is set only where TE comes back on the shared DC line, since that is
        # the only case needing one panel's TE switched on for the frame and off after
        leader = self.__leader if self.__leader_source is None else self.__leader_source.__leader
        if not v_sync or leader is None:
            return None

        written = self.screens if to is None else to
        if leader is self or leader in written:
            return leader

        # Waiting on a panel this frame does not write protects nothing, and a group
        # anchors its hold on whichever member the frame waited on, so pick a written one
        for screen in written:
            if screen.__shared_te:
                return screen
        return None

    def update(self, image, *, rotation=None, mirror=None, pixel_double=False, offset=None, tile=False, bg_color=None, v_sync=None, to=None):
        """Stream a frame to this screen, or to every member of a group."""
        if self.__pair is not None:
            # Hand back the panel state alignment holds, this frame being outside the pair
            self.__pair.__release_panel()

        # Check if the frame left v_sync unset, so it follows the screen's own
        if v_sync is None:
            v_sync = self.__v_sync
        elif v_sync and not self.__te:
            if self.__members is not None:
                raise ValueError("this broadcast group has no member to wait on. Its panels' scans are "
                                 "unsynchronised, so build it with leader naming one of them, which "
                                 "needs every member built with te set to the DC line they share")

            raise ValueError("v_sync needs a screen created with te, since it waits on the "
                             "panel's tearing-effect signal")

        # None is opaque black in picovector's packed premultiplied form
        bg = 0xff000000 if bg_color is None else bg_color.p & 0xffffffff

        # rotation and mirror both need the identity test, since 0 and False are real
        # settings a bare check would read as follow the screen
        if rotation is None:
            rotation = self.__rotation
        if mirror is None:
            mirror = self.__mirror

        __check_rotation(rotation)

        synced = self.__sync_screen(v_sync, to)
        delay = (self.__subset_of or self).__sync_delay_us
        self.__display.update(image,
                              rotation=rotation,
                              mirror=1 if mirror else 0,
                              pixel_double=1 if pixel_double else 0,
                              offset=offset, tile=tile, bg=bg, v_sync=v_sync,
                              to=self.__write_targets(to),
                              sync=None if synced is None else synced.__display,
                              sync_delay_us=delay)
        self.__synced_frame = synced
        self.__drawn(to)

        if self.__group is not None:
            # Advance the group's hold, or a run of a member's own frames lets it drift apart
            self.__group.__frame_ticked(self.__display.stats(), synced, delay)

    @micropython.native
    def prepare(self, image, *, rotation=None, mirror=None, pixel_double=False, offset=None, tile=False, bg_color=None, to=None):
        """Stage a frame for update_pair(), converting as far ahead as it can."""
        bg = 0xff000000 if bg_color is None else bg_color.p & 0xffffffff

        if rotation is None:
            rotation = self.__rotation
        if mirror is None:
            mirror = self.__mirror

        __check_rotation(rotation)

        # The TE target is fixed when a frame is staged, though update_pair() does the waiting
        synced = self.__sync_screen(self.__v_sync, to)
        self.__display.prepare(image,
                               rotation=rotation,
                               mirror=1 if mirror else 0,
                               pixel_double=1 if pixel_double else 0,
                               offset=offset, tile=tile, bg=bg,
                               to=self.__write_targets(to),
                               sync=None if synced is None else synced.__display)
