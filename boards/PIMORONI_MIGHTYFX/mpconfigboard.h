// Board and hardware specific configuration
#ifndef MICROPY_HW_BOARD_NAME
// Might be defined by mpconfigvariant.cmake
#define MICROPY_HW_BOARD_NAME                   "Pimoroni MightyFX"
#endif

// The flash partition sizes come from mpconfigboard.cmake: the port passes them to the
// linker as defsyms and defines them here itself, so setting them again is an error.

// CYW43 driver configuration.
#define CYW43_USE_SPI                           (1)
#define CYW43_LWIP                              (1)
#define CYW43_GPIO                              (0)
#define CYW43_SPI_PIO                           (1)

// PSRAM Settings. Enabled in mpconfigboard.cmake, because the port defines
// MICROPY_HW_ENABLE_PSRAM here itself; the chip select and size are in pimoroni_mightyfx.h.
// GC heap lives entirely in PSRAM, freeing the linker's SRAM heap region for
// the display to use as a fast staging/backing buffer (see spidisplay module).
#define MICROPY_GC_SPLIT_HEAP                   (0)

// core1 is a shared worker: PicoVector's DUAL_CORE blit/rasterisation dispatches to it, and so does
// the spidisplay module's frame conversion. A Python thread would conflict badly with both.
#define MICROPY_PY_THREAD                       (0)
