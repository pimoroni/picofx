# cmake file for Raspberry Pi Pico
set(PICO_BOARD "pimoroni_mightyfx")
set(PICO_PLATFORM "rp2350")

set(PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR})

# Board specific version of the frozen manifest
set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)

set(MICROPY_C_HEAP_SIZE 4096)

set(PICO_NUM_GPIOS 48)

set(PIMORONI_UF2_MANIFEST ${CMAKE_CURRENT_LIST_DIR}/uf2-manifest.txt)
set(PIMORONI_UF2_DIR ${CMAKE_CURRENT_BINARY_DIR}/filesystem)
include(${CMAKE_CURRENT_LIST_DIR}/../common.cmake)