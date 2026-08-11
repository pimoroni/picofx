// Board and hardware specific configuration
#ifndef MICROPY_HW_BOARD_NAME
// Might be defined by mpconfigvariant.cmake
#define MICROPY_HW_BOARD_NAME                   "Pimoroni TinyFX"
#endif

// The flash partition sizes come from mpconfigboard.cmake, which reserves the extra half
// megabyte the networking firmware needs on the W variant. The port passes them to the
// linker as defsyms and defines them here itself, so setting them again is an error.

#if defined(MICROPY_PY_NETWORK_CYW43)

// CYW43 driver configuration.
#define CYW43_USE_SPI                           (1)
#define CYW43_LWIP                              (1)
#define CYW43_GPIO                              (0)
#define CYW43_SPI_PIO                           (1)

#endif