#!/bin/bash

TARGET=$1

SCRIPT_PATH=${BASH_SOURCE-$0}
SCRIPT_PATH=$(dirname "$SCRIPT_PATH")

# The W drive variant carries the W image's libraries and i2c_target.py
bash "$SCRIPT_PATH/uf2-copyfiles-w.sh" "$TARGET" || exit 1

# The board writes its own main.py, which plays the FX drive
rm -v "$TARGET/main.py"

# The examples go on the FX drive instead, by drive-copyfiles-w.sh
rm -r -v "$TARGET/examples"

# The board writes the WiFi credentials to the FX drive, for a text editor to fill in
rm -v "$TARGET/secrets.py"
