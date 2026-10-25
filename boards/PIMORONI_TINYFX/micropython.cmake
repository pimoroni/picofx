if(NOT DEFINED PIMORONI_PICO_PATH)
message(FATAL_ERROR "PIMORONI_PICO_PATH must be set!")
endif()
include(${PIMORONI_PICO_PATH}/pimoroni_pico_import.cmake)

include_directories(${PIMORONI_PICO_PATH}/micropython)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../../")
list(APPEND CMAKE_MODULE_PATH "${PIMORONI_PICO_PATH}/micropython")
list(APPEND CMAKE_MODULE_PATH "${PIMORONI_PICO_PATH}/micropython/modules")

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# Essential
include(pimoroni_i2c/micropython)

# Sensors & Breakouts
include(micropython-common-breakouts)

# LEDs & Matrices
include(plasma/micropython)

# Servos & Motors
include(pwm/micropython)
include(servo/micropython)
include(encoder/micropython)
include(motor/micropython)

# Utility
include(adcfft/micropython)

# C++ Magic Memory
include(cppmem/micropython)

# Disable build-busting C++ exceptions
include(micropython-disable-exceptions)

# Fail the link where the firmware would run into the FX drive or the filesystem. A linker script
# given as a link input adds to the port's own
target_link_options(usermod INTERFACE
    "-Wl,--defsym=__board_firmware_bytes__=${FIRMWARE_SIZE_BYTES}"
    "${CMAKE_CURRENT_LIST_DIR}/../firmware_size.ld")