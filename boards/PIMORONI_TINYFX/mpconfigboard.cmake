# cmake file for Raspberry Pi Pico
set(PICO_BOARD "pimoroni_tinyfx")

set(PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR})

# Board specific version of the frozen manifest
set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)

set(MICROPY_C_HEAP_SIZE 4096)

# The flash split: firmware, and the filesystem taking what is left. There is no ROMFS, so
# the port defaults that partition to nothing. FLASH_SIZE_BYTES repeats PICO_FLASH_SIZE_BYTES
# from pimoroni_tinyfx.h, which the SDK does not scan into a cmake variable until after this
# file is read, so the two must agree.
math(EXPR FLASH_SIZE_BYTES "4 * 1024 * 1024")

# The W variant reserves another half megabyte for the networking firmware. This file is read
# before the variant's own, so the variant is what to test rather than MICROPY_PY_NETWORK_CYW43.
if(MICROPY_BOARD_VARIANT STREQUAL "w")
    math(EXPR FIRMWARE_SIZE_BYTES "1536 * 1024")
else()
    math(EXPR FIRMWARE_SIZE_BYTES "1 * 1024 * 1024")
endif()

if(NOT DEFINED MICROPY_HW_FLASH_STORAGE_BYTES)
    math(EXPR MICROPY_HW_FLASH_STORAGE_BYTES "${FLASH_SIZE_BYTES} - ${FIRMWARE_SIZE_BYTES}")
endif()