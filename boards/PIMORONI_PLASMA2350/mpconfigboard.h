// Board and hardware specific configuration
#ifndef MICROPY_HW_BOARD_NAME
// Might be defined by mpconfigvariant.cmake
#define MICROPY_HW_BOARD_NAME                   "Pimoroni Plasma 2350"
#endif

// I2C0 on the Qw/ST connector
#define MICROPY_HW_I2C0_SDA                     (PLASMA2350_SDA_PIN)
#define MICROPY_HW_I2C0_SCL                     (PLASMA2350_SCL_PIN)

// Wireless on the 2350 W, and PPP for a modem on SP/CE
#define MICROPY_PY_NETWORK_HOSTNAME_DEFAULT     "Plasma2350W"
#define MICROPY_PY_NETWORK                      (1)
#define MICROPY_PY_NETWORK_PPP_LWIP             (1)

#define CYW43_USE_SPI                           (1)
#define CYW43_LWIP                              (1)
#define CYW43_GPIO                              (1)
#define CYW43_SPI_PIO                           (1)

#ifndef CYW43_WL_GPIO_COUNT
#define CYW43_WL_GPIO_COUNT                     (3)
#endif

#define MICROPY_HW_PIN_EXT_COUNT                CYW43_WL_GPIO_COUNT

int mp_hal_is_pin_reserved(int n);
#define MICROPY_HW_PIN_RESERVED(i)              mp_hal_is_pin_reserved(i)

// The flash partition sizes come from mpconfigboard.cmake: the port passes them to the
// linker as defsyms and defines them here itself, so setting them again is an error.

// core1 is a shared worker: PicoVector's DUAL_CORE blit/rasterisation dispatches to it, and so does
// the spidisplay module's frame conversion. A Python thread would conflict badly with both.
#define MICROPY_PY_THREAD                       (0)

// A function whose locals exceed this size has its call frame allocated on the GC heap, and each
// one freed sends the allocator's search back to the start of the heap. 18 keeps the per-LED
// functions on the C stack instead, so they nest less deeply.
#define VM_MAX_STATE_ON_STACK                   (sizeof(mp_uint_t) * 18)

// Floats are held in the object word, so float maths allocates nothing. They keep about six
// significant digits, so a float summed over hours drifts.
#define MICROPY_OBJ_REPR                        (MICROPY_OBJ_REPR_C)

// USB mass storage exposes only the FX drive's volume, the FAT region at the end of flash,
// whose offset and size mpconfigboard.cmake passes with the rest of the flash split. Defining
// the offset keeps the standard LittleFS boot; mounting the volume is board code's job. The
// volume stays invisible to the host until rp2.enable_msc() is called.
#define MICROPY_HW_USB_MSC                      (1)
#define MICROPY_HW_USB_MSC_INQUIRY_VENDOR_STRING   "Pimoroni"
#define MICROPY_HW_USB_MSC_INQUIRY_PRODUCT_STRING  "Plasma FX Drive"

// FAT file names pass to and from Python as UTF-8. A computer writes its long names in Unicode,
// and read through a code page one accented name breaks listing the whole folder.
#define MICROPY_FATFS_LFN_UNICODE               (2)

// A soft reset takes the drive back from the computer, as a cold boot leaves it
#define MICROPY_HW_USB_MSC_UNREADY_ON_SOFT_RESET (1)

// A soft reset keeps the USB connection up, so a console stays attached through it
#define MICROPY_HW_USB_KEEP_BUS_ON_SOFT_RESET   (1)
