#!/bin/bash

TARGET=$1

SCRIPT_PATH=${BASH_SOURCE-$0}
SCRIPT_PATH=$(dirname "$SCRIPT_PATH")

# The drive variant carries what the standard image does, less three things
bash "$SCRIPT_PATH/uf2-copyfiles.sh" "$TARGET" || exit 1

# The board writes its own main.py, which plays the FX drive, and the examples' sounds
# would take the room the drive needs
rm -v "$TARGET/main.py"
find "$TARGET" -type f -name '*.wav' -exec rm -v {} \;

# autofx is frozen into the firmware, so the copy in the shared libraries is not staged
rm -v "$TARGET/lib/autofx.py"
