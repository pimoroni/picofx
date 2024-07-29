set(PICO_BOARD "pimoroni_tinyfx_4mb")

# Override the MicroPython board name
list(APPEND MICROPY_DEF_BOARD
    MICROPY_HW_BOARD_NAME="Pimoroni TinyFX 4MB"
)