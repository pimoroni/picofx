#!/bin/bash

TARGET=$1

SCRIPT_PATH=${BASH_SOURCE-$0}
SCRIPT_PATH=$(dirname "$SCRIPT_PATH")

# The examples go on the FX drive, where the computer can see them
cp -r -v "$SCRIPT_PATH/../../examples/tiny_fx/examples" "$TARGET/"

# Remove any markdown files, and the sounds, which are not shipped on the board
find "$TARGET" -type f \( -name '*.md' -o -name '*.wav' \) -exec rm -v {} \;
