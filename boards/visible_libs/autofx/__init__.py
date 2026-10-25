# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# autofx plays the effects file a user edits, so a board needs no code written for it.
# Each of its files imports only those before it, from vocabulary.py up to runner.py.
# Only run() and the vocabulary's tables are public.

from .vocabulary import (AUDIO, AUDIO_EFFECTS, BOARD_SETTINGS, CHANNEL_KINDS, COLOURS, EFFECTS, HUB,
                         OUTPUT_SETTINGS, SCREEN_EFFECTS, SCREEN_SETTINGS, SCREEN_SIZES, SETTINGS,
                         TILING)
from .runner import run
