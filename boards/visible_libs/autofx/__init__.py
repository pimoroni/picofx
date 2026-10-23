# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# Reads the effects file a user edits, and turns it into entries a board can play.
# The format is one entry per set of outputs:
#
#   out1-6 level=0.5: pulse_wave speed=0.6
#   out3.g: blink speed=1.0 duty=0.3
#   screenA: gif file="anim.gif"
#
# A [Heading: 30s] begins a scene that shows for its time; scenes take turns, and
# entries before the first heading are always on.
#
# Output settings sit left of the colon, effect settings right of it. An entry runs
# until the next selector, so settings may be laid out over several lines. Everything
# a user reads says output, where the code says channel: a channel is a slot in a
# player, and an output is the connector a channel drives.
#
# Nothing in the parser knows which channels a board has. It reports names; the loader
# resolves them. Nothing raises either: a line that cannot be read is reported and
# skipped, so one bad edit costs its own entry and not the whole file.

from .vocabulary import (AUDIO, AUDIO_EFFECTS, BOARD_SETTINGS, CHANNEL_KINDS, COLOURS, EFFECTS, HUB,
                         OUTPUT_SETTINGS, SCREEN_EFFECTS, SCREEN_SETTINGS, SCREEN_SIZES, SETTINGS,
                         TILING)
from .runner import run
