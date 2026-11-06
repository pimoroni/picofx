# The W with the FX drive: the W's wireless module, and the drive as the drive variant carries it.
# The flash split for it is in mpconfigboard.cmake
include(${CMAKE_CURRENT_LIST_DIR}/wireless.cmake)

list(APPEND MICROPY_DEF_BOARD
    "PIMORONI_FX_DRIVE=1"
)

set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest_w_drive.py)

set(UF2_STAGING_SCRIPT ${CMAKE_CURRENT_LIST_DIR}/uf2-copyfiles-w-drive.sh)
set(PIMORONI_UF2_MANIFEST ${CMAKE_CURRENT_LIST_DIR}/uf2-manifest-w-drive.txt)
set(PIMORONI_DRIVE_STAGING_SCRIPT ${CMAKE_CURRENT_LIST_DIR}/drive-copyfiles-w.sh)
include(${CMAKE_CURRENT_LIST_DIR}/../common.cmake)
