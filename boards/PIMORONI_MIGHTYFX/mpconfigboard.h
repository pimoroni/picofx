// Board and hardware specific configuration
#ifndef MICROPY_HW_BOARD_NAME
// Defined by mpconfigboard.cmake, so this is only a fallback
#define MICROPY_HW_BOARD_NAME                   "Pimoroni Mighty FX"
#endif

// The flash partition sizes come from mpconfigboard.cmake. The port passes them to the linker
// and defines them as C macros itself, so defining them again here is an error.

// CYW43 driver configuration.
#define CYW43_USE_SPI                           (1)
#define CYW43_LWIP                              (1)
#define CYW43_GPIO                              (0)
#define CYW43_SPI_PIO                           (1)

// PSRAM settings. mpconfigboard.cmake enables PSRAM, as the port links the SDK's library and
// defines MICROPY_HW_ENABLE_PSRAM from there. The chip select and size are in pimoroni_mightyfx.h.
// GC heap lives entirely in PSRAM, freeing the linker's SRAM heap region for
// the display to use as a fast staging/backing buffer (see spidisplay module).
#define MICROPY_GC_SPLIT_HEAP                   (0)

// core1 is a shared worker, as PicoVector's DUAL_CORE blit/rasterisation dispatches to it and so does
// the spidisplay module's frame conversion. A Python thread would conflict badly with both.
#define MICROPY_PY_THREAD                       (0)

// A function whose locals and value stack exceed this size takes its call frame from the GC heap,
// here PSRAM. The default of 11 slots leaves several per-LED functions just over it, and 18
// clears them all with room. Those functions take C stack instead, so they nest less deeply.
#define VM_MAX_STATE_ON_STACK                   (sizeof(mp_uint_t) * 18)

// Floats are held in the object word, so float maths allocates nothing. They keep about six
// significant digits, so a float summed over hours drifts.
#define MICROPY_OBJ_REPR                        (MICROPY_OBJ_REPR_C)

// The interpreter's hottest helpers run from SRAM, where from flash each cache miss stalls them
#define MICROPY_HW_VM_IN_RAM                    (1)

// machine.SPI and machine.UART need their pins named. The usual defaults are this board's LED
// outputs, its user switch and its PSRAM chip select. machine.I2C keeps its default, Qw/ST.
#define MICROPY_HW_SPI_NO_DEFAULT_PINS          (1)
#define MICROPY_HW_UART_NO_DEFAULT_PINS         (1)

