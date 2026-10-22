// Board and hardware specific configuration
#ifndef MICROPY_HW_BOARD_NAME
// Might be defined by mpconfigvariant.cmake
#define MICROPY_HW_BOARD_NAME                   "Pimoroni Mighty FX"
#endif

// The flash partition sizes come from mpconfigboard.cmake, as the port passes them to the
// linker as defsyms and defines them here itself, so setting them again is an error.

// CYW43 driver configuration.
#define CYW43_USE_SPI                           (1)
#define CYW43_LWIP                              (1)
#define CYW43_GPIO                              (0)
#define CYW43_SPI_PIO                           (1)

// PSRAM Settings. Enabled in mpconfigboard.cmake, because the port defines
// MICROPY_HW_ENABLE_PSRAM here itself. The chip select and size are in pimoroni_mightyfx.h.
// GC heap lives entirely in PSRAM, freeing the linker's SRAM heap region for
// the display to use as a fast staging/backing buffer (see spidisplay module).
#define MICROPY_GC_SPLIT_HEAP                   (0)

// core1 is a shared worker, as PicoVector's DUAL_CORE blit/rasterisation dispatches to it and so does
// the spidisplay module's frame conversion. A Python thread would conflict badly with both.
#define MICROPY_PY_THREAD                       (0)

// A function whose locals exceed this size has its call frame allocated on the GC heap, which
// here is PSRAM. The default of 11 slots leaves several per-LED functions just over it, and 18
// clears them all with room. Those functions take C stack instead, so they nest less deeply.
#define VM_MAX_STATE_ON_STACK                   (sizeof(mp_uint_t) * 18)

// Floats are held in the object word, so float maths allocates nothing. They keep about six
// significant digits, so a float summed over hours drifts.
#define MICROPY_OBJ_REPR                        (MICROPY_OBJ_REPR_C)

// The interpreter's hottest helpers run from SRAM, where from flash each cache miss stalls them
#define MICROPY_HW_VM_IN_RAM                    (1)

