# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# autofx plays the effects file a user edits, so a board needs no code written for it.
# Its files import only those before them in the order vocabulary, hardware, parser, checks,
# shows, sounds, loader, triggers and runner.
# Only run() and the vocabulary's tables are public.

from .vocabulary import (AUDIO, AUDIO_EFFECTS, BOARD_SETTINGS, CHANNEL_KINDS, COLOURS, EFFECTS, HUB,
                         OUTPUT_SETTINGS, SCREEN_EFFECTS, SCREEN_SETTINGS, SCREEN_SIZES, SETTINGS,
                         TILING)
from .runner import run
