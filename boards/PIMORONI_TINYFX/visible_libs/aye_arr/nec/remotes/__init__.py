# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from .argon import ArgonRemote
from .descriptor import RemoteDescriptor  # noqa: F401
from .lg import LGRemote
from .pimoroni import PimoroniRemote

KNOWN_REMOTES = (
    ArgonRemote,
    PimoroniRemote,
    LGRemote)
