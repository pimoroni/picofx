# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from .descriptor import RemoteDescriptor


class LGRemote(RemoteDescriptor):
    NAME = "LG"

    ADDRESS = 0x04

    BUTTON_CODES = {
        "PLAY": 0xb0,
        "PAUSE": 0xba,
        "PLUS_CHANNEL": 0x00,
        "MINUS_CHANNEL": 0x01,
        "PLUS_VOLUME": 0x02,
        "MINUS_VOLUME": 0x03,
        "MUTE": 0x09,
        "HOME": 0x7c,
        "BACK": 0x28,
        "CENTRE": 0x44,
        "DOWN": 0x41,
        "UP": 0x40,
        "LEFT": 0x07,
        "RIGHT": 0x06,
        "POWER": 0x08,
        "SOURCE": 0x0b,
        "ZERO": 0x10,
        "ONE": 0x11,
        "TWO": 0x12,
        "THREE": 0x13,
        "FOUR": 0x14,
        "FIVE": 0x15,
        "SIX": 0x16,
        "SEVEN": 0x17,
        "EIGHT": 0x18,
        "NINE": 0x19,
        "SETTINGS": 0x43,
        }

    def __init__(self):
        super().__init__()
