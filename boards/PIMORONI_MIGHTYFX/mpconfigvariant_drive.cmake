# The FX drive: a FAT volume the board shows over USB, which effects.txt, the picker and the
# manual live on. The flash split for it is in mpconfigboard.cmake, and the volume's place in
# mpconfigboard.h
list(APPEND MICROPY_DEF_BOARD
    "PIMORONI_FX_DRIVE=1"
)

set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest_drive.py)

set(UF2_STAGING_SCRIPT ${CMAKE_CURRENT_LIST_DIR}/uf2-copyfiles-drive.sh)
set(PIMORONI_UF2_MANIFEST ${CMAKE_CURRENT_LIST_DIR}/uf2-manifest-drive.txt)
set(PIMORONI_ROMFS_DIR ${CMAKE_CURRENT_LIST_DIR}/romfs)
set(PIMORONI_DRIVE_STAGING_SCRIPT ${CMAKE_CURRENT_LIST_DIR}/drive-copyfiles.sh)
include(${CMAKE_CURRENT_LIST_DIR}/../common.cmake)
