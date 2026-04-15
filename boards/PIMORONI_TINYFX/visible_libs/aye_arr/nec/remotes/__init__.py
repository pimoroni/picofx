# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from .descriptor import RemoteDescriptor    # noqa: F401
from .argon import ArgonRemote
from .pimoroni import PimoroniRemote
from .lg import LGRemote

KNOWN_REMOTES = (
    ArgonRemote,
    PimoroniRemote,
    LGRemote)
