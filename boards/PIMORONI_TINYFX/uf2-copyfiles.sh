#!/bin/bash

TARGET=$1

SCRIPT_PATH=${BASH_SOURCE-$0}
SCRIPT_PATH=$(dirname "$SCRIPT_PATH")

if [ -z ${CI_BUILD_ROOT+x} ]; then
    CI_BUILD_ROOT="$SCRIPT_PATH/../../.."
    echo "Using default libs path: $CI_BUILD_ROOT"
else
    echo "Using custom libs path: $CI_BUILD_ROOT"
fi

cp -r -v "$SCRIPT_PATH/../../examples/tiny_fx/." "$TARGET/"

mkdir -p "$TARGET/lib"
cp -r -v "$SCRIPT_PATH/../../picofx" "$TARGET/lib"
cp -r -v "$SCRIPT_PATH/visible_libs/." "$TARGET/lib"
cp -r -v "$SCRIPT_PATH/../visible_libs/." "$TARGET/lib"
cp -r -v "$CI_BUILD_ROOT/aye_arr/aye_arr" "$TARGET/lib"

# Remove any markdown files
find "$TARGET" -type f -name '*.md' -exec rm -v {} \;
