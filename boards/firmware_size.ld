/* The firmware has to end inside its share of the flash, the FX drive or the filesystem starting
   straight after it, and the port's own link does not check that. __board_firmware_bytes__ is
   FIRMWARE_SIZE_BYTES from the board's mpconfigboard.cmake, and 0x10000000 is where flash starts */
ASSERT(__flash_binary_end <= 0x10000000 + __board_firmware_bytes__,
       "the firmware is larger than FIRMWARE_SIZE_BYTES in mpconfigboard.cmake gives it")
