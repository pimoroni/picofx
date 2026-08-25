# cmake file for Raspberry Pi Pico
set(PICO_BOARD "pimoroni_mightyfx")
set(PICO_PLATFORM "rp2350")

set(PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR})

# Board specific version of the frozen manifest
set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)

set(MICROPY_C_HEAP_SIZE 4096)

set(PICO_NUM_GPIOS 48)

# The flash split: firmware, the config FAT volume, a read-only ROMFS for the fonts,
# and the filesystem taking what is left. The port reads the last two from here, so
# mpconfigboard.h does not set them; the config volume's offset and size are repeated there
# as MICROPY_HW_USB_MSC_FLASH_OFFSET/_BYTES, so the two must agree. The config volume must
# come out of this expression, not only out of the ROMFS: the filesystem sits at the end of
# flash, so a larger storage value moves its base and orphans every existing filesystem.
# FLASH_SIZE_BYTES repeats PICO_FLASH_SIZE_BYTES from pimoroni_mightyfx.h, which the SDK does
# not scan into a cmake variable until after this file is read, so the two must agree.
math(EXPR FLASH_SIZE_BYTES "16 * 1024 * 1024")
math(EXPR FIRMWARE_SIZE_BYTES "2 * 1024 * 1024")
math(EXPR CONFIG_FAT_SIZE_BYTES "6784 * 1024")

if(NOT DEFINED MICROPY_HW_ROMFS_BYTES)
    math(EXPR MICROPY_HW_ROMFS_BYTES "768 * 1024")
endif()

if(NOT DEFINED MICROPY_HW_FLASH_STORAGE_BYTES)
    math(EXPR MICROPY_HW_FLASH_STORAGE_BYTES
         "${FLASH_SIZE_BYTES} - ${FIRMWARE_SIZE_BYTES} - ${CONFIG_FAT_SIZE_BYTES} - ${MICROPY_HW_ROMFS_BYTES}")
endif()

# The port links the SDK's hardware_psram from here and takes the chip select and size from
# pimoroni_mightyfx.h, so neither is repeated here. MICROPY_HW_PSRAM_CS_PIN is only wanted by
# boards that leave the size to be detected.
set(MICROPY_HW_ENABLE_PSRAM 1)