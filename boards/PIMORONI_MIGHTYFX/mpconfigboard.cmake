# cmake file for Raspberry Pi Pico
set(PICO_BOARD "pimoroni_mightyfx")
set(PICO_PLATFORM "rp2350")

set(PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR})

# Board specific version of the frozen manifest
set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)

# Where ci/micropython.sh fetched this board's hosted packages. It reaches the manifest as
# $(LIB_DIR), every MICROPY_MANIFEST_* variable arriving there with the prefix stripped
set(MICROPY_MANIFEST_LIB_DIR ${CI_BUILD_ROOT}/lib)

set(MICROPY_C_HEAP_SIZE 4096)

set(PICO_NUM_GPIOS 48)

# Override the MicroPython board name
# And set basic options which are expanded upon in mpconfigboard.h
list(APPEND MICROPY_DEF_BOARD
    "MICROPY_HW_BOARD_NAME=\"Pimoroni MightyFX\""
    "MICROPY_PY_NETWORK=1"
    "MICROPY_PY_NETWORK_PPP_LWIP=1"
)

# Links micropy_lib_lwip and sets MICROPY_PY_LWIP = 1
# Picked up and expanded upon in mpconfigboard.h
set(MICROPY_PY_LWIP ON)

# Links cyw43-driver and sets:
# MICROPY_PY_NETWORK_CYW43 = 1,
# MICROPY_PY_SOCKET_DEFAULT_TIMEOUT_MS = 30000
set(MICROPY_PY_NETWORK_CYW43 ON)

# Adds mpbthciport.c
# And sets:
# MICROPY_PY_BLUETOOTH = 1,
# MICROPY_PY_BLUETOOTH_USE_SYNC_EVENTS = 1,
# MICROPY_PY_BLUETOOTH_ENABLE_CENTRAL_MODE = 1
set(MICROPY_PY_BLUETOOTH ON)

# Links pico_btstack_hci_transport_cyw43
# And sets:
# MICROPY_BLUETOOTH_BTSTACK = 1,
# MICROPY_BLUETOOTH_BTSTACK_CONFIG_FILE =
set(MICROPY_BLUETOOTH_BTSTACK ON)

# Sets:
# CYW43_ENABLE_BLUETOOTH = 1,
# MICROPY_PY_BLUETOOTH_CYW43 = 1
set(MICROPY_PY_BLUETOOTH_CYW43 ON)

# The flash split, in order: firmware, a read-only ROMFS for the fonts, the filesystem, and the
# FX drive's FAT volume to the end of flash where the variant carries one. The filesystem starts
# at the same place with or without the volume, so the variants differ only in its size. The
# port reads the filesystem's base and size and the volume's place from here, so
# mpconfigboard.h sets none of them. FLASH_SIZE_BYTES repeats PICO_FLASH_SIZE_BYTES from
# pimoroni_mightyfx.h, which the SDK does not scan into a cmake variable until after this file
# is read, so the two must agree.
math(EXPR FLASH_SIZE_BYTES "16 * 1024 * 1024")
math(EXPR FIRMWARE_SIZE_BYTES "2 * 1024 * 1024")

# This file is read before the variant's own, so the variant is what to test rather than what
# it defines
math(EXPR CONFIG_FAT_SIZE_BYTES "0")
if(MICROPY_BOARD_VARIANT STREQUAL "drive")
    math(EXPR CONFIG_FAT_SIZE_BYTES "13056 * 1024")
endif()

if(NOT DEFINED MICROPY_HW_ROMFS_BYTES)
    math(EXPR MICROPY_HW_ROMFS_BYTES "768 * 1024")
endif()

if(NOT DEFINED MICROPY_HW_FLASH_STORAGE_BYTES)
    math(EXPR MICROPY_HW_FLASH_STORAGE_BYTES
         "${FLASH_SIZE_BYTES} - ${FIRMWARE_SIZE_BYTES} - ${MICROPY_HW_ROMFS_BYTES} - ${CONFIG_FAT_SIZE_BYTES}")
endif()

# The port puts the ROMFS just below the filesystem's base, so setting the base places both
math(EXPR FLASH_STORAGE_BASE "${FIRMWARE_SIZE_BYTES} + ${MICROPY_HW_ROMFS_BYTES}")
list(APPEND MICROPY_DEF_BOARD "MICROPY_HW_FLASH_STORAGE_BASE=${FLASH_STORAGE_BASE}")

if(CONFIG_FAT_SIZE_BYTES GREATER 0)
    math(EXPR CONFIG_FAT_OFFSET "${FLASH_STORAGE_BASE} + ${MICROPY_HW_FLASH_STORAGE_BYTES}")
    list(APPEND MICROPY_DEF_BOARD
        "MICROPY_HW_USB_MSC_FLASH_OFFSET=${CONFIG_FAT_OFFSET}"
        "MICROPY_HW_USB_MSC_FLASH_BYTES=${CONFIG_FAT_SIZE_BYTES}"
    )
endif()

# The port links the SDK's hardware_psram from here and takes the chip select and size from
# pimoroni_mightyfx.h, so neither is repeated here. MICROPY_HW_PSRAM_CS_PIN is only wanted by
# boards that leave the size to be detected.
set(MICROPY_HW_ENABLE_PSRAM 1)