# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from .descriptor import RemoteDescriptor


class PimoroniRemote(RemoteDescriptor):
    NAME = "Pimoroni"

    ADDRESS = 0x00

    BUTTON_CODES = {
        "ANTICLOCK": 0x45,
        "UP": 0x46,
        "CLOCKWISE": 0x47,
        "LEFT": 0x44,
        "OK/STOP": 0x40,
        "RIGHT": 0x43,
        "RETURN/UNDO": 0x07,
        "DOWN": 0x15,
        "MENU/ACTION": 0x09,
        "1/RED": 0x16,
        "2/GREEN": 0x19,
        "3/BLUE": 0x0d,
        "4/CYAN": 0x0c,
        "5/MAGENTA": 0x18,
        "6/YELLOW": 0x5e,
        "7/WARM": 0x08,
        "8/WHITE": 0x1c,
        "9/COOL": 0x5a,
        "RECORD": 0x42,
        "0/RAINBOW": 0x52,
        "PLAY/PAUSE": 0x4a
        }

    def __init__(self):
        super().__init__()
