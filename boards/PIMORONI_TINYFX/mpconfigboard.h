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

#if defined(PIMORONI_FX_DRIVE)

// USB mass storage exposes only the FX drive's volume, the FAT region sitting between the
// firmware and the filesystem. Offset and size must agree with the flash split in
// mpconfigboard.cmake. Defining the offset keeps the standard LittleFS boot; mounting the
// volume is board code's job. The volume stays invisible to the host until
// rp2.enable_msc() is called.
#define MICROPY_HW_USB_MSC                      (1)
#define MICROPY_HW_USB_MSC_FLASH_OFFSET         (1024 * 1024)
#define MICROPY_HW_USB_MSC_FLASH_BYTES          (2048 * 1024)
#define MICROPY_HW_USB_MSC_INQUIRY_VENDOR_STRING   "Pimoroni"
#define MICROPY_HW_USB_MSC_INQUIRY_PRODUCT_STRING  "TinyFX Drive"

// FAT file names pass to and from Python as UTF-8. A computer writes its long names in Unicode,
// and read through a code page one accented name breaks listing the whole folder.
#define MICROPY_FATFS_LFN_UNICODE               (2)

#endif