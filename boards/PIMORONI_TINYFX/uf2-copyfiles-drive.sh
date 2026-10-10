#!/bin/bash

TARGET=$1

SCRIPT_PATH=${BASH_SOURCE-$0}
SCRIPT_PATH=$(dirname "$SCRIPT_PATH")

# The drive variant carries the standard image's libraries and i2c_target.py
bash "$SCRIPT_PATH/uf2-copyfiles.sh" "$TARGET" || exit 1

# The board writes its own main.py, which plays the FX drive
rm -v "$TARGET/main.py"

# The examples are too large for the filesystem the drive leaves
rm -r -v "$TARGET/examples"
