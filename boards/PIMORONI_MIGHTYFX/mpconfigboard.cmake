# cmake file for Raspberry Pi Pico
set(PICO_BOARD "pimoroni_mightyfx")
set(PICO_PLATFORM "rp2350")

set(PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR})

# Board specific version of the frozen manifest
set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)

set(MICROPY_C_HEAP_SIZE 4096)

set(PICO_NUM_GPIOS 48)

# List of directories to copy into the UF2 staging dir
# The contents of these will be available for packing into the filesystem build
list(APPEND UF2_COPY_DIRS
    "${CMAKE_CURRENT_LIST_DIR}/../../examples/mighty_fx"
    "${CMAKE_CURRENT_LIST_DIR}/../../picofx"
    "${CMAKE_CURRENT_LIST_DIR}/visible_libs"
)

set(PIMORONI_UF2_MANIFEST ${CMAKE_CURRENT_LIST_DIR}/uf2-manifest.txt)
include(${CMAKE_CURRENT_LIST_DIR}/../common.cmake)