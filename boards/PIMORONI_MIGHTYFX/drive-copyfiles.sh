#!/bin/bash

TARGET=$1

SCRIPT_PATH=${BASH_SOURCE-$0}
SCRIPT_PATH=$(dirname "$SCRIPT_PATH")

# The examples and their art go on the FX drive, where the computer can see them
cp -r -v "$SCRIPT_PATH/../../examples/mighty_fx/examples" "$TARGET/"

# Remove any markdown files
find "$TARGET" -type f -name '*.md' -exec rm -v {} \;
