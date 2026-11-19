#!/bin/bash

TARGET=$1

SCRIPT_PATH=${BASH_SOURCE-$0}
SCRIPT_PATH=$(dirname "$SCRIPT_PATH")

# The examples go on the FX drive, where the computer can see them
cp -r -v "$SCRIPT_PATH/../../examples/tiny_fx/examples" "$TARGET/"

# Remove any markdown files, and the sounds, which are not shipped on the board
find "$TARGET" -type f \( -name '*.md' -o -name '*.wav' \) -exec rm -v {} \;

# Keep only the programs drive-programs.txt names, the demos worth running. The examples index
# offers the others that name a section to download. photon_sword is not offered either, since it
# needs the sounds removed above, and fx_board.json's examples_left_out keeps it out of the index
python3 "$SCRIPT_PATH/../../tools/drive_programs.py" "$TARGET/examples" \
    "$SCRIPT_PATH/drive-programs.txt" || exit 1

# The example sounds are downloaded through Discover, so only their sections go on the drive, for
# the picker to group them by
mkdir -p "$TARGET/examples/sounds"
cp -v "$SCRIPT_PATH/../../examples/shared/examples/sounds/sections.txt" "$TARGET/examples/sounds/"
