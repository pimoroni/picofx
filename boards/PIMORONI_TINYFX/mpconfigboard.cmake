# cmake file for Raspberry Pi Pico
set(PICO_BOARD "pimoroni_tinyfx")

set(PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR})

# Board specific version of the frozen manifest
set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)

set(MICROPY_C_HEAP_SIZE 4096)

# The software float routines run from SRAM, where from flash they can share XIP cache sets with the
# interpreter's hottest code, depending on where the rest of the firmware moves them
list(APPEND MICROPY_DEF_BOARD "PICO_FLOAT_IN_RAM=1")

# The flash split, firmware then the filesystem. The port reads it from here, so mpconfigboard.h
# sets none of it. FLASH_SIZE_BYTES must match PICO_FLASH_SIZE_BYTES in pimoroni_tinyfx.h, which
# the SDK has not read into cmake by this point
math(EXPR FLASH_SIZE_BYTES "4 * 1024 * 1024")

# The W variant reserves another half megabyte for the networking firmware. This file is read
# before the variant's own, so the variant is what to test rather than what it defines.
math(EXPR FIRMWARE_SIZE_BYTES "1 * 1024 * 1024")
if(MICROPY_BOARD_VARIANT STREQUAL "w")
    math(EXPR FIRMWARE_SIZE_BYTES "1536 * 1024")
endif()

if(NOT DEFINED MICROPY_HW_FLASH_STORAGE_BYTES)
    math(EXPR MICROPY_HW_FLASH_STORAGE_BYTES "${FLASH_SIZE_BYTES} - ${FIRMWARE_SIZE_BYTES}")
endif()

list(APPEND MICROPY_DEF_BOARD "MICROPY_HW_FLASH_STORAGE_BASE=${FIRMWARE_SIZE_BYTES}")