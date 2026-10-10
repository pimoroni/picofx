#!/bin/bash

TARGET=$1

SCRIPT_PATH=${BASH_SOURCE-$0}
SCRIPT_PATH=$(dirname "$SCRIPT_PATH")

# The drive variant carries the standard image's libraries, less those its firmware freezes
bash "$SCRIPT_PATH/uf2-copyfiles.sh" "$TARGET" || exit 1

# The board writes its own main.py, which plays the FX drive
rm -v "$TARGET/main.py"
rm -v "$TARGET/lib/logging.py" "$TARGET/lib/spce.py" "$TARGET/lib/st7789.py"
rm -r -v "$TARGET/lib/screens"

# The examples and their art go on the FX drive instead, by drive-copyfiles.sh
rm -r -v "$TARGET/examples"

# The board writes the WiFi credentials to the FX drive, for a text editor to fill in
rm -v "$TARGET/secrets.py"
