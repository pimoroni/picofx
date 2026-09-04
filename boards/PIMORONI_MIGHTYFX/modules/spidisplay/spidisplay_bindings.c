// SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
//
// SPDX-License-Identifier: MIT
//
// The spidisplay module table, and the module functions belonging to neither type.
// The Python surface is documented in README.md.

#include "py/runtime.h"
#include "py/objarray.h"

#include "spidisplay_bindings.h"

/***** Module functions *****/
static mp_obj_t spidisplay_buffer(size_t n_args, const mp_obj_t *args) {
    mp_int_t nbytes = mp_obj_get_int(args[0]);
    if (nbytes < 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("a buffer needs a positive size"));
    }

    if (n_args > 1) {
        // An offset places the view by hand, so it is bounded but not claimed
        mp_int_t offset = mp_obj_get_int(args[1]);
        size_t headroom = spidisplay_sram_headroom();
        if (offset < 0 || (size_t)offset > headroom
            || (size_t)nbytes > headroom - (size_t)offset) {
            mp_raise_ValueError(MP_ERROR_TEXT("buffer does not fit the SRAM below the display workspaces"));
        }
        return mp_obj_new_memoryview('B' | MP_OBJ_ARRAY_TYPECODE_FLAG_RW,
                                     (size_t)nbytes, __GcHeapStart + offset);
    }

    long long claimed = spidisplay_sram_claim_low((size_t)nbytes);
    if (claimed < 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("buffer does not fit the SRAM left between the canvases and the display workspaces"));
    }
    return mp_obj_new_memoryview('B' | MP_OBJ_ARRAY_TYPECODE_FLAG_RW,
                                 (size_t)nbytes, __GcHeapStart + claimed);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(spidisplay_buffer_obj, 1, 2, spidisplay_buffer);

static mp_obj_t spidisplay_buffer_size(void) {
    return mp_obj_new_int_from_uint(spidisplay_sram_available());
}
static MP_DEFINE_CONST_FUN_OBJ_0(spidisplay_buffer_size_obj, spidisplay_buffer_size);

static mp_obj_t spidisplay_release_buffers(void) {
    spidisplay_sram_release_low();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(spidisplay_release_buffers_obj, spidisplay_release_buffers);

static mp_obj_t spidisplay_dual_convert_obj_fn(size_t n_args, const mp_obj_t *args) {
    if (n_args > 0) {
        spidisplay_set_dual_convert(mp_obj_is_true(args[0]) ? 1 : 0);
    }
    return mp_obj_new_bool(spidisplay_dual_convert());
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(spidisplay_dual_convert_obj, 0, 1, spidisplay_dual_convert_obj_fn);

/***** Module *****/
static const mp_rom_map_elem_t spidisplay_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_spidisplay) },
    { MP_ROM_QSTR(MP_QSTR_SPIDisplayBus), MP_ROM_PTR(&SPIDisplayBus_type) },
    { MP_ROM_QSTR(MP_QSTR_SPIDisplay), MP_ROM_PTR(&SPIDisplay_type) },
    { MP_ROM_QSTR(MP_QSTR_buffer), MP_ROM_PTR(&spidisplay_buffer_obj) },
    { MP_ROM_QSTR(MP_QSTR_buffer_size), MP_ROM_PTR(&spidisplay_buffer_size_obj) },
    { MP_ROM_QSTR(MP_QSTR_release_buffers), MP_ROM_PTR(&spidisplay_release_buffers_obj) },
    { MP_ROM_QSTR(MP_QSTR_dual_convert), MP_ROM_PTR(&spidisplay_dual_convert_obj) },
    { MP_ROM_QSTR(MP_QSTR_update_all), MP_ROM_PTR(&spidisplay_update_all_obj) },
    { MP_ROM_QSTR(MP_QSTR_te_phase), MP_ROM_PTR(&spidisplay_te_phase_obj) },
};
static MP_DEFINE_CONST_DICT(spidisplay_globals, spidisplay_globals_table);

const mp_obj_module_t spidisplay_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&spidisplay_globals,
};

MP_REGISTER_MODULE(MP_QSTR_spidisplay, spidisplay_user_cmodule);
