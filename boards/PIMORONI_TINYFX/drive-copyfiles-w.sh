#!/bin/bash

TARGET=$1

SCRIPT_PATH=${BASH_SOURCE-$0}
SCRIPT_PATH=$(dirname "$SCRIPT_PATH")

# The drive variant's examples, and the W's wireless ones beside them
bash "$SCRIPT_PATH/drive-copyfiles.sh" "$TARGET" || exit 1
cp -r -v "$SCRIPT_PATH/../../examples/tiny_fx_w/examples" "$TARGET/"

# Remove any markdown files
find "$TARGET" -type f -name '*.md' -exec rm -v {} \;
