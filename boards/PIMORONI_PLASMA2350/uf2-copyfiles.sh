#!/bin/bash

TARGET=$1

SCRIPT_PATH=${BASH_SOURCE-$0}
SCRIPT_PATH=$(dirname "$SCRIPT_PATH")

# Libraries only: this board plays the effects file and carries no examples. autofx is
# frozen into the firmware, so the copy in the shared libraries is not staged
mkdir -p "$TARGET/lib"
cp -r -v "$SCRIPT_PATH/../../picofx" "$TARGET/lib"
cp -r -v "$SCRIPT_PATH/visible_libs/." "$TARGET/lib"
cp -r -v "$SCRIPT_PATH/../visible_libs/." "$TARGET/lib"
rm -v "$TARGET/lib/autofx.py"

# Remove any markdown files
find "$TARGET" -type f -name '*.md' -exec rm -v {} \;
