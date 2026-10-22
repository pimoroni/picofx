include(${CMAKE_CURRENT_LIST_DIR}/wireless.cmake)

set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest_w.py)

set(UF2_STAGING_SCRIPT ${CMAKE_CURRENT_LIST_DIR}/uf2-copyfiles-w.sh)
set(PIMORONI_UF2_MANIFEST ${CMAKE_CURRENT_LIST_DIR}/uf2-manifest-w.txt)
include(${CMAKE_CURRENT_LIST_DIR}/../common.cmake)