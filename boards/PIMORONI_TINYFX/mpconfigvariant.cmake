set(PICO_BOARD "pimoroni_tinyfx")

# Override the MicroPython board name
list(APPEND MICROPY_DEF_BOARD
    MICROPY_HW_BOARD_NAME="Pimoroni TinyFX 2MB"
)