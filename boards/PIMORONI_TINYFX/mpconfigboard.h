// Board and hardware specific configuration
#ifndef MICROPY_HW_BOARD_NAME
// Might be defined by mpconfigvariant.cmake
#define MICROPY_HW_BOARD_NAME                   "Pimoroni TinyFX"
#endif

#if defined(MICROPY_PY_NETWORK_CYW43)

// We need space for networking firmware on network builds
// 1536 * 1024 = 1.5MB
#define FIRMWARE_SIZE_BYTES                     (1536 * 1024)

// CYW43 driver configuration.
#define CYW43_USE_SPI                           (1)
#define CYW43_LWIP                              (1)
#define CYW43_GPIO                              (0)
#define CYW43_SPI_PIO                           (1)

#else

// 1MB for the firmware
#define FIRMWARE_SIZE_BYTES                     (1 * 1024 * 1024)

#endif

#define MICROPY_HW_FLASH_STORAGE_BYTES          (PICO_FLASH_SIZE_BYTES - FIRMWARE_SIZE_BYTES)