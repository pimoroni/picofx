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
        "OK_STOP": 0x40,
        "RIGHT": 0x43,
        "RETURN_UNDO": 0x07,
        "DOWN": 0x15,
        "MENU_ACTION": 0x09,
        "1_RED": 0x16,
        "2_GREEN": 0x19,
        "3_BLUE": 0x0d,
        "4_CYAN": 0x0c,
        "5_MAGENTA": 0x18,
        "6_YELLOW": 0x5e,
        "7_WARM": 0x08,
        "8_WHITE": 0x1c,
        "9_COOL": 0x5a,
        "RECORD": 0x42,
        "0_RAINBOW": 0x52,
        "PLAY/PAUSE": 0x4a
    }

    NUMBERS = {
        "0_RAINBOW": 0,
        "1_RED": 1,
        "2_GREEN": 2,
        "3_BLUE": 3,
        "4_CYAN": 4,
        "5_MAGENTA": 5,
        "6_YELLOW": 6,
        "7_WARM": 7,
        "8_WHITE": 8,
        "9_COOL": 9,
    }

    def __init__(self):
        super().__init__()
