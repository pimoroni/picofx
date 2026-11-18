#!/bin/bash

TARGET=$1

SCRIPT_PATH=${BASH_SOURCE-$0}
SCRIPT_PATH=$(dirname "$SCRIPT_PATH")

# The examples and their art go on the FX drive, where the computer can see them
cp -r -v "$SCRIPT_PATH/../../examples/mighty_fx/examples" "$TARGET/"

# Remove any markdown files
find "$TARGET" -type f -name '*.md' -exec rm -v {} \;

# Remove the drawings that repeat a showcase program, keeping the three that use two screens.
# The examples index still offers the rest to download
find "$TARGET/examples/drawings" -type f \( -name '*.py' -o -name '*.png' \) \
    ! -name 'bus_departures*' ! -name 'departures_list*' ! -name 'creature_eyes*' -exec rm -v {} \;
