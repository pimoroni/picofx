#!/bin/bash

TARGET=$1

SCRIPT_PATH=${BASH_SOURCE-$0}
SCRIPT_PATH=$(dirname "$SCRIPT_PATH")

# The drive variant carries what the standard image does, with autofx and without main.py
bash "$SCRIPT_PATH/uf2-copyfiles.sh" "$TARGET" || exit 1

# autofx plays the FX drive, and the board writes its own main.py, which runs it
cp -v "$SCRIPT_PATH/../visible_libs/autofx.py" "$TARGET/lib"
rm -v "$TARGET/main.py"
