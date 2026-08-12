# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# The frame path a single screen and a broadcast group share: staging a frame,
# waiting on the tearing-effect signal, naming which panels a write reaches, and
# the backlight that stays dark until one has been drawn.

import picovector
import spidisplay


class ScreenBase:
    """The frame path shared by a single screen and a broadcast group.

    te says whether a tearing-effect signal is reachable at all, and v_sync whether a
    frame waits on it by default. members is the screens a broadcast group stands
    for, and None for a screen standing for itself. shared_te says the signal arrives
    on a line other screens share, which is what makes the wait transient; sync names
    the screen whose signal a frame waits on.

    Not built directly: construct a Screen subclass or a ScreenGroup.
    """

    def __init__(self, port, display, width, height, bitdepth, backlight, te, v_sync, reserve, members=None, shared_te=False, sync=None):
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
        self.__shared_te = shared_te  # Whether this panel's TE reaches a line others share
        self.__sync = sync      # The screen whose TE a frame waits on, None to leave TE alone
        self.__synced_frame = None  # The screen the last frame's wait ended on, if any
        self.__sync_delay_us = 0    # How long a write trails the wait, set by a holding group

    @property
    def port(self):
        return self.__port

    @property
    def display(self):
        """The spidisplay.SPIDisplay a frame streams over, for its diagnostics."""
        return self.__display

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
    def bitdepth(self):
        return self.__bitdepth

    @property
    def v_sync(self):
        """Whether a frame waits on the tearing-effect signal unless told otherwise."""
        return self.__v_sync

    @property
    def sync(self):
        """The screen whose tearing-effect signal a frame waits on, or None.

        A single screen syncs on itself. A group syncs on the one member it
        nominated, the rest tearing, since panels on a hub scan independently and no
        edge is safe for all of them.
        """
        return self.__sync

    @property
    def reserve(self):
        """What this screen's share of the fast SRAM was set aside for."""
        return self.__reserve

    def brightness(self, value):
        """Set how bright the backlight looks, from 0.0 to 1.0.

        Against perceived brightness, so equal steps look equal. 0.0 is off and every
        setting above it is one the panel answers, the driver's own floor being folded
        in. backlight carries the rest of the control, on() and off() among it.
        """
        if self.__backlight is None:
            raise ValueError("this screen has no backlight to set, so its brightness is whatever the assembly ties it to")

        self.__backlight.brightness(value)

    def canvas(self, width=None, height=None, offset=None):
        """An SRAM-backed image, by default sized to this screen.

        The GC heap is PSRAM, so a plain image() is read over XIP and costs about
        twice as much per pixel to convert. Each size is claimed once from this
        screen's own part of the region and handed back on every later call, so two
        screens never share pixels.

        Half the panel's width and height, drawn with pixel_double=True, is a
        quarter of the bytes: two screens can hold one each where one full-size
        canvas already fills the region. offset places a canvas by hand instead,
        outside the claims.
        """
        width = self.__width if width is None else width
        height = self.__height if height is None else height
        if width < 1 or height < 1:
            raise ValueError("a canvas needs a positive width and height")

        nbytes = width * height * 4    # RGBA8888
        if offset is not None:
            return picovector.image(width, height, spidisplay.buffer(nbytes, offset))

        canvas = self.__canvases.get((width, height))
        if canvas is None:
            canvas = picovector.image(width, height, spidisplay.buffer(nbytes))
            self.__canvases[(width, height)] = canvas

        return canvas

    def drawn(self):
        """Note that a frame has landed, which the backlight waits for.

        Every panel on a port is cleared as it is brought up, so one frame anywhere
        on the line is enough: no panel is left holding what power-on put there,
        whatever the program goes on to draw and to whichever screens.
        """
        if self.__backlight is not None:
            self.__backlight.frame_shown()

    def command(self, command, data=None):
        self.__display.command(command, data)

    def __check_rotation(self, rotation):
        r_index = rotation // 90
        if r_index < 0 or r_index > 3 or rotation % 90:     # Modulo check ensures rotation is exactly a multipe of 90
            raise ValueError(f"{rotation} is not a valid angle. Expected 0, 90, 180, or 270.")

    @micropython.native
    def __write_targets(self, to):
        """The displays a write drives, or None for every one this object holds.

        A subset narrows to its own members when the caller names none, which is
        what makes front.update(image) write only the panels front stands for.
        """
        if to is None:
            if self.__subset_of is None:
                return None
            to = self.__members

        members = self.screens
        for screen in to:
            if screen not in members:
                raise ValueError(f"{screen} is not one of these screens, so a frame cannot be sent to it")

        return tuple(screen.display for screen in to)

    def __sync_screen(self, v_sync, to):
        """The screen whose TE this write waits on, or None to leave TE alone.

        Only a screen sharing its DC line needs the transient discipline, a panel
        owning its own line keeping TEON from bringup. Waiting on a member outside
        the written set buys nothing, that panel being clean and not updated while
        every panel that is written tears, so a narrowed write falls to a member of
        its own set.
        """
        if not v_sync or self.__sync is None:
            return None

        written = self.screens if to is None else to
        if self.__sync is self or self.__sync in written:
            return self.__sync

        for screen in written:
            if screen.__shared_te:
                return screen
        return None

    def update(self, image, rotation=0, mirror=False, v_sync=None, bg_color=picovector.color.black, pixel_double=False, offset=None, to=None):
        # A frame outside the pair first hands back the panel state alignment
        # holds, the trimmed porch included: the narrowed TE pulse is only safe
        # under the pair's poll, and the period was the pair's choice
        if self.__pair is not None:
            self.__pair.__release_panel()

        # v_sync=None follows the screen, so only a frame that differs says so
        if v_sync is None:
            v_sync = self.__v_sync
        elif v_sync and not self.__te:
            if self.__members is not None:
                raise ValueError("this broadcast group has no member to wait on: its panels' scans are unsynchronised, so build it with sync naming one of them, which needs every member built with te set to the DC line they share")

            raise ValueError("v_sync needs a screen created with te, since it waits on the panel's tearing-effect signal")

        bg = bg_color.p & 0xffffffff

        self.__check_rotation(rotation)

        synced = self.__sync_screen(v_sync, to)
        delay = (self.__subset_of or self).__sync_delay_us
        # The C module handles the transform, transfer, and TE wait
        self.__display.update(image,
                              rotation=rotation,
                              mirror=1 if mirror else 0,
                              pixel_double=1 if pixel_double else 0,
                              bg=bg, offset=offset, v_sync=v_sync,
                              to=self.__write_targets(to),
                              sync=None if synced is None else synced.display,
                              sync_delay_us=delay)
        self.__synced_frame = synced
        self.drawn()

        # A member updated on its own still scans, so its frames advance its
        # group's hold too; a run of them would otherwise walk the group apart.
        if self.__group is not None:
            self.__group.__frame_ticked(self.__display.stats(), synced, delay)

    @micropython.native
    def prepare(self, image, rotation=0, mirror=False, bg_color=picovector.color.black, pixel_double=False, offset=None, to=None):
        """Stage a frame for update_pair(), converting as far ahead as it can.

        Placement is per screen, so a pair can differ in rotation, mirroring and
        offset to suit how each panel is mounted. Nothing reaches the panel until
        update_pair() runs, and a staged frame refuses command() until it does.
        """
        bg = bg_color.p & 0xffffffff

        self.__check_rotation(rotation)

        synced = self.__sync_screen(self.__v_sync, to)
        self.__display.prepare(image,
                               rotation=rotation,
                               mirror=1 if mirror else 0,
                               pixel_double=1 if pixel_double else 0,
                               bg=bg, offset=offset,
                               to=self.__write_targets(to),
                               sync=None if synced is None else synced.display)
