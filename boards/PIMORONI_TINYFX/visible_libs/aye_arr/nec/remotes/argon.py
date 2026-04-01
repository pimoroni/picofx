# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from .descriptor import RemoteDescriptor


class ArgonRemote(RemoteDescriptor):
    NAME = "Argon"

    ADDRESS = 0x00

    BUTTON_CODES = {
        "UP": 0xca,
        "DOWN": 0xd2,
        "LEFT": 0x99,
        "RIGHT": 0xc1,
        "CENTRE": 0xce,
        "POWER": 0x9c,
        "PLUS": 0x80,
        "MINUS": 0x81,
        "MENU": 0x9d,
        "HOME": 0xcb,
        "BACK": 0x90
        }

    def __init__(self):
        super().__init__()
