// SPDX-License-Identifier: MIT
//
// Module table and registration for the spidisplay C module. The SPIDisplay
// type is defined in spidisplay.cpp (extern "C").

#include "py/runtime.h"
#include "py/objarray.h"

extern const mp_obj_type_t SPIDisplay_type;

// Linker symbols bounding the SRAM region the GC heap would occupy. With
// MICROPY_GC_SPLIT_HEAP off the GC heap is PSRAM-only, so this region is free
// for fast SRAM-backed framebuffers.
extern uint8_t __GcHeapStart[];
extern uint8_t __GcHeapEnd[];

// buffer(nbytes) -> writable memoryview over the free SRAM region. Pass it to
// picovector's image(width, height, buffer) so rendering and the display
// conversion both run against SRAM instead of PSRAM.
static mp_obj_t spidisplay_buffer(mp_obj_t nbytes_in) {
    mp_int_t nbytes = mp_obj_get_int(nbytes_in);
    size_t available = (size_t)(__GcHeapEnd - __GcHeapStart);
    if (nbytes < 0 || (size_t)nbytes > available) {
        mp_raise_ValueError(MP_ERROR_TEXT("buffer size exceeds available SRAM"));
    }
    return mp_obj_new_memoryview('B' | MP_OBJ_ARRAY_TYPECODE_FLAG_RW,
                                 (size_t)nbytes, __GcHeapStart);
}
static MP_DEFINE_CONST_FUN_OBJ_1(spidisplay_buffer_obj, spidisplay_buffer);

static const mp_rom_map_elem_t spidisplay_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_spidisplay) },
    { MP_ROM_QSTR(MP_QSTR_SPIDisplay), MP_ROM_PTR(&SPIDisplay_type) },
    { MP_ROM_QSTR(MP_QSTR_buffer), MP_ROM_PTR(&spidisplay_buffer_obj) },
};
static MP_DEFINE_CONST_DICT(spidisplay_globals, spidisplay_globals_table);

const mp_obj_module_t spidisplay_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&spidisplay_globals,
};

MP_REGISTER_MODULE(MP_QSTR_spidisplay, spidisplay_user_cmodule);
