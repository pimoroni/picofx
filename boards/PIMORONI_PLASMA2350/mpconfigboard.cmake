# cmake file for the Pimoroni Plasma 2350 and 2350 W, one build serving both. The board header
# is the W's, as the plasma repository builds it, wireless included.
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

set(MICROPY_C_HEAP_SIZE 4096)

# The flash split: firmware, the FX drive's FAT volume, and the filesystem taking what is
# left. There is no ROMFS, nothing on this board reading one. The volume's offset and size
# are repeated in mpconfigboard.h as MICROPY_HW_USB_MSC_FLASH_OFFSET/_BYTES, so the two must
# agree. The filesystem sits at the end of flash, so a larger storage value moves its base
# and orphans every existing filesystem. FLASH_SIZE_BYTES repeats PICO_FLASH_SIZE_BYTES from
# pimoroni_plasma2350w.h, which is not scanned into a cmake variable until after
# this file is read, so the two must agree.
math(EXPR FLASH_SIZE_BYTES "4 * 1024 * 1024")
math(EXPR FIRMWARE_SIZE_BYTES "1664 * 1024")
math(EXPR CONFIG_FAT_SIZE_BYTES "2048 * 1024")

if(NOT DEFINED MICROPY_HW_FLASH_STORAGE_BYTES)
    math(EXPR MICROPY_HW_FLASH_STORAGE_BYTES
         "${FLASH_SIZE_BYTES} - ${FIRMWARE_SIZE_BYTES} - ${CONFIG_FAT_SIZE_BYTES}")
endif()
