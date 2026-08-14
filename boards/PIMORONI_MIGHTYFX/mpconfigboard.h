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

// USB mass storage exposes only the config volume, the FAT region sitting between the
// firmware and the ROMFS. Offset and size must agree with the flash split in
// mpconfigboard.cmake. Defining the offset keeps the standard LittleFS boot; mounting the
// config volume is board code's job. The volume stays invisible to the host until
// rp2.enable_msc() is called.
#define MICROPY_HW_USB_MSC                      (1)
#define MICROPY_HW_USB_MSC_FLASH_OFFSET         (2 * 1024 * 1024)
#define MICROPY_HW_USB_MSC_FLASH_BYTES          (256 * 1024)
#define MICROPY_HW_USB_MSC_INQUIRY_VENDOR_STRING   "Pimoroni"
#define MICROPY_HW_USB_MSC_INQUIRY_PRODUCT_STRING  "MightyFX Drive"
