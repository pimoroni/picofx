#!/bin/bash

TARGET=$1

SCRIPT_PATH=${BASH_SOURCE-$0}
SCRIPT_PATH=$(dirname "$SCRIPT_PATH")

cp -r -v "$SCRIPT_PATH/../../examples/tiny_fx/." "$TARGET/"
cp -r -v "$SCRIPT_PATH/../../examples/tiny_fx_w/." "$TARGET/"

mkdir -p "$TARGET/lib"
cp -r -v "$SCRIPT_PATH/../../picofx" "$TARGET/lib"
cp -r -v "$SCRIPT_PATH/visible_libs/." "$TARGET/lib"
cp -r -v "$SCRIPT_PATH/../visible_libs/." "$TARGET/lib"
cp -r -v "$SCRIPT_PATH/../../../aye_arr/aye_arr" "$TARGET/lib"

# Remove any markdown files
find "$TARGET" -type f -name '*.md' -exec rm -v {} \;
