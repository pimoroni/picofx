# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from collections import namedtuple

ButtonCallbacks = namedtuple("ButtonCallbacks", ("on_press", "on_repeat", "on_release", "on_short"))


class RemoteDescriptor:
    NAME = "Unknown"
    ADDRESS = 0x00
    BUTTON_CODES = {}

    def __init__(self):
        self.__buttons = {}
        self.on_known = None
        self.on_any = None

    def bind(self, name, on_press, on_repeat=True, on_release=None, on_short=None):
        if name not in self.BUTTON_CODES:
            raise KeyError(f"Name '{name}' is not a bindable button of the '{self.NAME}' remote")

        self.bind_code(self.BUTTON_CODES[name], on_press, on_repeat, on_release, on_short)

    def bind_code(self, code, on_press, on_repeat=True, on_release=None, on_short=None):
        if code in self.__buttons:
            raise ValueError(f"A button with the code '0x{code:0x}' is already bound to the '{self.NAME}' remote. Use a different code")
        self.__buttons[code] = ButtonCallbacks(on_press,
                                               on_press if on_repeat is True else on_repeat,
                                               on_release, on_short)

    def unbind(self, name):
        if name not in self.BUTTON_CODES:
            raise KeyError(f"Name '{name}' is not a bindable button of the '{self.NAME}' remote")

        self.unbind_code(self.BUTTON_CODES[name])

    def unbind_code(self, code):
        del self.__buttons[code]

    def button(self, code):
        return self.__buttons[code]
