# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# The frame path a single screen and a broadcast group share: staging a frame, the
# wait on the tearing-effect signal, and the backlight that stays dark until one has drawn.

import spidisplay


class Tile:
    """How update() and prepare() repeat a source along an axis."""
    OFF = 0         # What False means
    REPEAT = 1      # What True means
    MIRROR = 2      # Every other repeat reversed, so each seam is a reflection


def __check_rotation(rotation):
    r_index = rotation // 90
    if r_index < 0 or r_index > 3 or rotation % 90:
        raise ValueError(f"{rotation} is not a valid angle. Expected 0, 90, 180, or 270.")


def __tightest_margin(screens, trims, line_us, wire_us):
    # Margin is the scan lines a write leaves uncovered, judged in each member's line
    # time. Returns (tightest index, margins in us, the hold's quantum of two lines).
    margins = [screen.__line_slots + trim + screen.height - wire / line
               for screen, trim, line, wire in zip(screens, trims, line_us, wire_us)]
    tightest = margins.index(min(margins))
    margins_us = tuple(margin * line for margin, line in zip(margins, line_us))
    return tightest, margins_us, 2 * line_us[tightest]


class ScreenBase:
    """The frame path a Screen and a ScreenGroup share. Construct one of those."""

    def __init__(self, port, display, width, height, bitdepth, backlight, te, v_sync, reserve, members=None, shared_te=False, leader=None, rotation=0, mirror=False, reveal_together=False):
        __check_rotation(rotation)
        self.__port = port
        self.__display = display
        self.__width = width
        self.__height = height
        self.__bitdepth = bitdepth
        self.__backlight = backlight
        self.__te = te
        self.__v_sync = v_sync
        self.__reserve = reserve
        self.__members = members
        self.__canvases = {}
        self.__pair = None      # The ScreenPair holding panel state on this screen
        self.__group = None     # The ScreenGroup this screen is a member of, if any
        self.__subset_of = None  # The group a subset narrows, so it writes its members only
        self.__subset_displays = None  # The members' displays, built once per subset
        self.__shared_te = shared_te  # Whether this panel's TE reaches a line others share
        self.__leader = leader  # The screen whose TE a frame waits on, None to leave TE alone
        self.__synced_frame = None  # The screen the last frame's wait ended on, if any
        self.__sync_delay_us = 0    # How long a write trails the wait, set by a holding group
        self.__rotation = rotation  # The angle every frame takes unless it names its own
        self.__mirror = bool(mirror)
        self.__reveal_together = bool(reveal_together)

    @property
    def port(self):
        return self.__port

    @property
    def backlight(self):
        return self.__backlight

    @property
    def screens(self):
        """The screens a broadcast group stands for, or just this one."""
        return self.__members if self.__members is not None else (self,)

    @property
    def width(self):
        return self.__width

    @property
    def height(self):
        return self.__height

    @property
    def rotation(self):
        """The angle a frame is placed at unless it names its own."""
        return self.__rotation

    @property
    def mirror(self):
        """Whether a frame is flipped left to right unless it says otherwise."""
        return self.__mirror

    @property
    def reveal_together(self):
        """Whether the port's backlight waits for every screen asking for it."""
        return self.__reveal_together

    def brightness(self, value):
        """Set how bright the backlight looks, from 0.0 to 1.0."""
        if self.__backlight is None:
            raise ValueError("this screen has no backlight to set, so its brightness is whatever the assembly ties it to")

        self.__backlight.brightness(value)

    def canvas(self, width=None, height=None, offset=None):
        """An image in fast SRAM, by default sized to this screen and claimed once per size."""
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
        # Every panel on a port is cleared at bringup, so one frame anywhere on the line
        # lights it. keep_dark hands back the scan, for a caller lighting several ports at once.
        if self.__backlight is None:
            return None

        return self.__backlight.__frame_shown(self, to, keep_dark)

    def __command(self, command, data=None):
        self.__display.command(command, data)

    @micropython.native
    def __write_targets(self, to):
        # A subset with nothing named writes its own members, so front.update(image)
        # reaches only the panels front stands for
        if to is None:
            return self.__subset_displays

        members = self.screens
        for screen in to:
            if screen not in members:
                raise ValueError(f"{screen} is not one of these screens, so a frame cannot be sent to it")

        return tuple(screen.__display for screen in to)

    def __sync_screen(self, v_sync, to):
        # Only a screen sharing its DC line needs the transient wait. A member outside the
        # written set would stay clean while every written panel tears, so a narrowed write waits on one of its own.
        if not v_sync or self.__leader is None:
            return None

        written = self.screens if to is None else to
        if self.__leader is self or self.__leader in written:
            return self.__leader

        for screen in written:
            if screen.__shared_te:
                return screen
        return None

    def update(self, image, *, rotation=None, mirror=None, pixel_double=False, offset=None, tile=False, bg_color=None, v_sync=None, to=None):
        """Stream a frame to the panel, or to every screen a group stands for."""
        # A frame outside the pair hands back the panel state its alignment holds
        if self.__pair is not None:
            self.__pair.__release_panel()

        # v_sync=None follows the screen, so only a frame that differs names it
        if v_sync is None:
            v_sync = self.__v_sync
        elif v_sync and not self.__te:
            if self.__members is not None:
                raise ValueError("this broadcast group has no member to wait on: its panels' scans are unsynchronised, so build it with leader naming one of them, which needs every member built with te set to the DC line they share")

            raise ValueError("v_sync needs a screen created with te, since it waits on the panel's tearing-effect signal")

        # None is opaque black in the module's packed premultiplied form
        bg = 0xff000000 if bg_color is None else bg_color.p & 0xffffffff

        # mirror needs the identity test: None is falsy, so a truthiness check would
        # read "follow the screen" as "do not mirror"
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

        # A member's own frames advance its group's hold too, or a run of them walks the group apart
        if self.__group is not None:
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

        synced = self.__sync_screen(self.__v_sync, to)
        self.__display.prepare(image,
                               rotation=rotation,
                               mirror=1 if mirror else 0,
                               pixel_double=1 if pixel_double else 0,
                               offset=offset, tile=tile, bg=bg,
                               to=self.__write_targets(to),
                               sync=None if synced is None else synced.__display)
