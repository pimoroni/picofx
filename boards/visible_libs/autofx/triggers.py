# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# The triggers. A Triggers watches the sensor connector, the Aye Arr Remote's receiver or a PIR
# Stick's input, and says what each press, or motion starting or stopping, asks the runner to
# do. The runner does it, and says where the scenes have gone.

import time

from .vocabulary import REMOTE, TRIGGERS
from .loader import trigger_delay, trigger_does, trigger_given

# How many scenes back Previous can go
HISTORY = 10


class Triggers:
    """
    What the sensor fitted asks for, read from the board on each pass of the runner's loop.
    service() hands back the actions due, each as (what, place): "scene" with the place of the
    scene to go to, "restart" with the scene's place or None for a file without scenes,
    "standby" or "pause".

    Previous goes back through the scenes shown, the last HISTORY of them, and through the
    order once those run out. Going back takes a scene off the history, so two presses go
    back two scenes rather than to and fro.

    A motion trigger can wait before it acts. The opposite edge coming first cancels the wait,
    or, where the file says cancel=no, waits for it: when the wait is over, the trigger acts,
    and if the Stick has changed since, the opposite trigger's row starts from then, with its
    own wait. A wait is dropped when the scenes move on for another reason to one that does
    not use the row that started it.
    """
    def __init__(self, fx, settings, scenes, clock=None):
        # Looked up here, not as the default, so the module loads where time has no ticks_ms
        self.__clock = clock or time.ticks_ms
        self.__receiver = None
        self.__pin = None
        self.__pressed = []         # Buttons pressed since the last pass, oldest first
        sensor = settings.get("sensor")
        # A board that could not take the sensor has none to hand back
        try:
            if sensor == "ir":
                self.__receiver = fx.sensor
                self.__listen()
            elif sensor == "pir":
                self.__pin = fx.sensor
        except RuntimeError:
            pass
        self.reload(settings, scenes)

    def __listen(self):
        # Every button of the remote, reported once for each press and never for a held one
        from aye_arr.nec.remotes import PimoroniRemote
        remote = PimoroniRemote()
        for trigger in TRIGGERS[REMOTE]:
            remote.bind(trigger.upper(), on_press=(self.__press, trigger), on_repeat=None)
        self.__receiver.bind(remote)
        self.__receiver.start()

    def __press(self, trigger):
        self.__pressed.append(trigger)

    def reload(self, settings, scenes):
        """Take a file read again, which begins at its first scene with nothing to go back to."""
        self.__settings = settings
        self.__scenes = scenes
        self.__at = 0
        self.__history = []
        self.__back = None          # The scene Previous has taken off the history
        # A motion trigger waiting, as [trigger, when it acts, whether the opposite edge
        # cancels it, the row it came from], or None
        self.__waiting = None
        # The opposite trigger a finished wait held back, which acts once its action has
        # been taken, in the scene that action leaves showing
        self.__owed = None
        self.__level = self.__pin.value() if self.__pin is not None else None
        del self.__pressed[:]

    def service(self):
        """The actions due since the last pass, oldest first."""
        actions = []
        now = self.__clock()
        if self.__receiver is not None:
            self.__receiver.decode()
            while self.__pressed:
                actions.append(self.__does(self.__pressed.pop(0)))
        elif self.__pin is not None:
            if self.__owed is not None:
                owed, self.__owed = self.__owed, None
                actions.extend(self.__edge(owed, now))
            level = self.__pin.value()
            if level != self.__level:
                self.__level = level
                actions.extend(self.__edge("starts" if level else "stops", now))
            actions.extend(self.__due(now))
        return [action for action in actions if action[0] is not None]

    def shown(self, at):
        """
        Note the scene now showing, however it came to show. Leaving a scene puts it on
        Previous's history, unless Previous is what left it.
        """
        if at != self.__at and at != self.__back:
            self.__history.append(self.__at)
            del self.__history[:-HISTORY]
        self.__back = None
        self.__at = at

        # A wait from a row this scene does not use is dropped, the scene having moved on
        if self.__waiting is not None and self.__row(self.__waiting[0]) != self.__waiting[3]:
            self.__waiting = None

    def __row(self, trigger):
        # Where a trigger's choice comes from in the scene showing: its place for the scene's
        # own, or None for Always on's or the default
        scenes = self.__scenes
        if scenes and trigger in scenes[self.__at].triggers:
            return self.__at
        return None

    def __does(self, trigger):
        # What a trigger does in the scene showing, Previous going back through the history
        scenes = self.__scenes
        if scenes and trigger_given(scenes, self.__settings, self.__at, trigger)[0] == "previous":
            if self.__history:
                self.__back = self.__history.pop()
                return ("scene", self.__back)
            return ("scene", (self.__at - 1) % len(scenes))
        return trigger_does(scenes, self.__settings, self.__at, trigger)

    def __edge(self, trigger, now):
        # Motion starting or stopping, which acts now, waits, or is held by a wait
        waiting = self.__waiting
        if waiting is not None:
            # Check if this edge is the opposite of the one waiting, which a wait that
            # cancels gives way to. A wait that finishes first holds every edge until
            # it is over, and the same edge again is already being answered
            if waiting[0] != trigger and waiting[2]:
                self.__waiting = None
            else:
                return []

        seconds, cancels = trigger_delay(self.__scenes, self.__settings, self.__at, trigger)
        if seconds <= 0:
            return [self.__does(trigger)]
        # A trigger that does nothing has nothing to wait for
        if trigger_does(self.__scenes, self.__settings, self.__at, trigger)[0] is None:
            return []
        self.__waiting = [trigger, time.ticks_add(now, int(seconds * 1000)), cancels,
                          self.__row(trigger)]
        return []

    def __due(self, now):
        # A wait that is over, acting now. One that held the opposite edge back hands it on
        # where the Stick has changed since
        waiting = self.__waiting
        if waiting is None or time.ticks_diff(now, waiting[1]) < 0:
            return []
        self.__waiting = None
        trigger = waiting[0]
        if not waiting[2] and self.__level != (1 if trigger == "starts" else 0):
            self.__owed = "stops" if trigger == "starts" else "starts"
        return [self.__does(trigger)]
