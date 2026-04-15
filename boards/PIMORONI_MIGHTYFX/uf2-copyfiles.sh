#!/bin/bash

TARGET=$1

SCRIPT_PATH=${BASH_SOURCE-$0}
SCRIPT_PATH=$(dirname "$SCRIPT_PATH")

cp -r -v "$SCRIPT_PATH/../../examples/mighty_fx/" "$TARGET/"

mkdir -p "$TARGET/lib"
cp -r -v "$SCRIPT_PATH/../../picofx" "$TARGET/lib"
cp -r -v "$SCRIPT_PATH/visible_libs/" "$TARGET/lib"