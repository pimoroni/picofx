# cmake file for Raspberry Pi Pico
set(PICO_BOARD "pimoroni_tinyfx")

set(PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR})

# Board specific version of the frozen manifest
set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)

set(MICROPY_C_HEAP_SIZE 4096)

# The software float routines run from SRAM, where from flash they can share XIP cache sets with the
# interpreter's hottest code, depending on where the rest of the firmware moves them
list(APPEND MICROPY_DEF_BOARD "PICO_FLOAT_IN_RAM=1")

# Firmware, then the filesystem, then the FX drive's volume to the end of flash where the variant
# has one, so a uf2 rewriting the filesystem never reaches the volume. That matters on RP2040, where
# dir2uf2 cannot build a sparse uf2 and fills every block up to the filesystem. The port reads this split
# from here, so mpconfigboard.h sets none of it. FLASH_SIZE_BYTES must match PICO_FLASH_SIZE_BYTES
# in pimoroni_tinyfx.h, which the SDK has not read into cmake by this point
math(EXPR FLASH_SIZE_BYTES "4 * 1024 * 1024")

# The W variants reserve another half megabyte for the networking firmware, and the drive variants
# two and a half megabytes for the FX drive, or two on the W. This file is read before the
# variant's own, so the variant is what to test rather than what it defines.
math(EXPR FIRMWARE_SIZE_BYTES "1 * 1024 * 1024")
math(EXPR CONFIG_FAT_SIZE_BYTES "0")
if(MICROPY_BOARD_VARIANT STREQUAL "w")
    math(EXPR FIRMWARE_SIZE_BYTES "1536 * 1024")
elseif(MICROPY_BOARD_VARIANT STREQUAL "drive")
    math(EXPR CONFIG_FAT_SIZE_BYTES "2560 * 1024")
elseif(MICROPY_BOARD_VARIANT STREQUAL "w_drive")
    math(EXPR FIRMWARE_SIZE_BYTES "1536 * 1024")
    math(EXPR CONFIG_FAT_SIZE_BYTES "2048 * 1024")
endif()

if(NOT DEFINED MICROPY_HW_FLASH_STORAGE_BYTES)
    math(EXPR MICROPY_HW_FLASH_STORAGE_BYTES
         "${FLASH_SIZE_BYTES} - ${FIRMWARE_SIZE_BYTES} - ${CONFIG_FAT_SIZE_BYTES}")
endif()

list(APPEND MICROPY_DEF_BOARD "MICROPY_HW_FLASH_STORAGE_BASE=${FIRMWARE_SIZE_BYTES}")

if(CONFIG_FAT_SIZE_BYTES GREATER 0)
    math(EXPR CONFIG_FAT_OFFSET "${FIRMWARE_SIZE_BYTES} + ${MICROPY_HW_FLASH_STORAGE_BYTES}")
    list(APPEND MICROPY_DEF_BOARD
        "MICROPY_HW_USB_MSC_FLASH_OFFSET=${CONFIG_FAT_OFFSET}"
        "MICROPY_HW_USB_MSC_FLASH_BYTES=${CONFIG_FAT_SIZE_BYTES}"
    )
endif()