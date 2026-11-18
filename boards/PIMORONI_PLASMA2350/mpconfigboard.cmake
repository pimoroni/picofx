# cmake file for the Pimoroni Plasma 2350 and Plasma 2350 W, which share one build. The board
# header is the W's, as in the plasma repository, so the build includes wireless.
set(PICO_BOARD "pimoroni_plasma2350w")
set(PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR})
set(PICO_PLATFORM "rp2350")

set(MICROPY_PY_LWIP ON)
set(MICROPY_PY_NETWORK_CYW43 ON)
set(MICROPY_PY_BLUETOOTH ON)
set(MICROPY_BLUETOOTH_BTSTACK ON)
set(MICROPY_PY_BLUETOOTH_CYW43 ON)

# Board specific version of the frozen manifest
set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)

# Where ci/micropython.sh fetched this board's hosted packages. The port passes each
# MICROPY_MANIFEST_* variable to the manifest without its prefix, so this one is $(LIB_DIR)
set(MICROPY_MANIFEST_LIB_DIR ${CI_BUILD_ROOT}/lib)

set(MICROPY_C_HEAP_SIZE 4096)

# Firmware, then the filesystem, then the FX drive's FAT volume to the end of flash. There is
# no ROMFS, since nothing on this board reads one. The port reads this split from here, so
# mpconfigboard.h sets none of it. FLASH_SIZE_BYTES must match PICO_FLASH_SIZE_BYTES in
# pimoroni_plasma2350w.h, which the SDK has not read into cmake by this point
math(EXPR FLASH_SIZE_BYTES "4 * 1024 * 1024")
math(EXPR FIRMWARE_SIZE_BYTES "1664 * 1024")
math(EXPR CONFIG_FAT_SIZE_BYTES "2048 * 1024")

if(NOT DEFINED MICROPY_HW_FLASH_STORAGE_BYTES)
    math(EXPR MICROPY_HW_FLASH_STORAGE_BYTES
         "${FLASH_SIZE_BYTES} - ${FIRMWARE_SIZE_BYTES} - ${CONFIG_FAT_SIZE_BYTES}")
endif()

list(APPEND MICROPY_DEF_BOARD "MICROPY_HW_FLASH_STORAGE_BASE=${FIRMWARE_SIZE_BYTES}")

math(EXPR CONFIG_FAT_OFFSET "${FIRMWARE_SIZE_BYTES} + ${MICROPY_HW_FLASH_STORAGE_BYTES}")
list(APPEND MICROPY_DEF_BOARD
    "MICROPY_HW_USB_MSC_FLASH_OFFSET=${CONFIG_FAT_OFFSET}"
    "MICROPY_HW_USB_MSC_FLASH_BYTES=${CONFIG_FAT_SIZE_BYTES}"
)
