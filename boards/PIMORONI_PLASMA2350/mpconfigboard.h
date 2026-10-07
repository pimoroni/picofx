// Board and hardware specific configuration
#ifndef MICROPY_HW_BOARD_NAME
// Might be defined by mpconfigvariant.cmake
#define MICROPY_HW_BOARD_NAME                   "Pimoroni Plasma 2350"
#endif

// The flash partition sizes come from mpconfigboard.cmake: the port passes them to the
// linker as defsyms and defines them here itself, so setting them again is an error.

// core1 is a shared worker: PicoVector's DUAL_CORE blit/rasterisation dispatches to it, and so does
// the spidisplay module's frame conversion. A Python thread would conflict badly with both.
#define MICROPY_PY_THREAD                       (0)

// USB mass storage exposes only the FX drive's volume, the FAT region sitting between the
// firmware and the filesystem. Offset and size must agree with the flash split in
// mpconfigboard.cmake. Defining the offset keeps the standard LittleFS boot; mounting the
// volume is board code's job. The volume stays invisible to the host until
// rp2.enable_msc() is called.
#define MICROPY_HW_USB_MSC                      (1)
#define MICROPY_HW_USB_MSC_FLASH_OFFSET         (1280 * 1024)
#define MICROPY_HW_USB_MSC_FLASH_BYTES          (2304 * 1024)
#define MICROPY_HW_USB_MSC_INQUIRY_VENDOR_STRING   "Pimoroni"
#define MICROPY_HW_USB_MSC_INQUIRY_PRODUCT_STRING  "Plasma FX Drive"
