// SPDX-License-Identifier: MIT
//
// Module table and registration for the spidisplay C module. The SPIDisplayBus
// and SPIDisplay types are defined in spidisplay.cpp (extern "C").

#include "py/runtime.h"
#include "py/objarray.h"

extern const mp_obj_type_t SPIDisplayBus_type;
extern const mp_obj_type_t SPIDisplay_type;

// Linker symbols bounding the SRAM region the GC heap would occupy. The GC heap is
// PSRAM-only here, so this region is free for fast SRAM-backed framebuffers.
extern uint8_t __GcHeapStart[];
extern uint8_t __GcHeapEnd[];

// The region below the lowest display workspace claim (spidisplay.cpp): displays
// claim from the top, so the ceiling moves while the base stays put.
extern size_t spidisplay_sram_available(void);

// buffer(nbytes, offset=0) -> writable memoryview over the free SRAM region. Pass
// it to picovector's image(width, height, buffer) so rendering and conversion both
// run against SRAM instead of PSRAM, which halves the conversion cost.
//
// No allocator: a view always starts at offset, so two buffers that must coexist
// need explicit non-overlapping offsets. Staying stateless means a re-run of a
// script gets the same addresses back. Displays claim their band and cache
// workspace from the TOP of the region at construction, so build screens first
// and size canvases after; a screen's cost is its sram_bytes().
static mp_obj_t spidisplay_buffer(size_t n_args, const mp_obj_t *args) {
    mp_int_t nbytes = mp_obj_get_int(args[0]);
    mp_int_t offset = n_args > 1 ? mp_obj_get_int(args[1]) : 0;
    size_t available = spidisplay_sram_available();
    if (nbytes < 0 || offset < 0 || (size_t)offset > available
        || (size_t)nbytes > available - (size_t)offset) {
        mp_raise_ValueError(MP_ERROR_TEXT("buffer does not fit the SRAM below the display workspaces"));
    }
    return mp_obj_new_memoryview('B' | MP_OBJ_ARRAY_TYPECODE_FLAG_RW,
                                 (size_t)nbytes, __GcHeapStart + offset);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(spidisplay_buffer_obj, 1, 2, spidisplay_buffer);

// Bytes of SRAM buffer() can hand out, so a caller can size a canvas to fit.
// Shrinks while screens are alive and recovers when they release (shutdown(),
// or their finalisers via gc.collect()).
static mp_obj_t spidisplay_buffer_size(void) {
    return mp_obj_new_int_from_uint(spidisplay_sram_available());
}
static MP_DEFINE_CONST_FUN_OBJ_0(spidisplay_buffer_size_obj, spidisplay_buffer_size);

static const mp_rom_map_elem_t spidisplay_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_spidisplay) },
    { MP_ROM_QSTR(MP_QSTR_SPIDisplayBus), MP_ROM_PTR(&SPIDisplayBus_type) },
    { MP_ROM_QSTR(MP_QSTR_SPIDisplay), MP_ROM_PTR(&SPIDisplay_type) },
    { MP_ROM_QSTR(MP_QSTR_buffer), MP_ROM_PTR(&spidisplay_buffer_obj) },
    { MP_ROM_QSTR(MP_QSTR_buffer_size), MP_ROM_PTR(&spidisplay_buffer_size_obj) },
};
static MP_DEFINE_CONST_DICT(spidisplay_globals, spidisplay_globals_table);

const mp_obj_module_t spidisplay_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&spidisplay_globals,
};

MP_REGISTER_MODULE(MP_QSTR_spidisplay, spidisplay_user_cmodule);
