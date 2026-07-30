// SPDX-License-Identifier: MIT
//
// SPIDisplayBus and SPIDisplay implementation and their MicroPython bindings. The
// C++ classes own the SPI/DMA/GPIO and the overlapped band pump; the extern "C"
// block wraps them as types. Module registration is in spidisplay_bindings.c.

#include <new>
#include <utility>

#include "hardware/gpio.h"
#include "hardware/regs/addressmap.h"
#include "hardware/spi.h"
#include "pico/time.h"

#include "column_cache.hpp"
#include "scanline.hpp"
#include "spidisplay.hpp"

namespace spidisplay {

// Two static SRAM band buffers: one is streamed by DMA while the CPU converts the
// next into the other. Sized for MAX_BAND_LINES rows at the widest in-scope panel
// (240px, 480 bytes/row at RGB565). SRAM is required, since the RP2350 M33 has no
// SRAM data cache, so DMA sees CPU writes without maintenance.
static constexpr int MAX_BAND_LINES = 16;
static constexpr size_t MAX_ROW_BYTES = 240 * 2;
static constexpr size_t BAND_BYTES = MAX_BAND_LINES * MAX_ROW_BYTES;
static uint8_t band_a[BAND_BYTES] __attribute__((aligned(4)));
static uint8_t band_b[BAND_BYTES] __attribute__((aligned(4)));

static constexpr uintptr_t PSRAM_WINDOW = 0x01000000;                   // 16 MB window per CS
static constexpr uintptr_t PSRAM_CACHED_BASE = XIP_BASE + PSRAM_WINDOW; // Start of PSRAM (0x11000000)

// SRAM scratch for the column cache (see column_cache.hpp). The budget is a pixel
// count, so a narrower window caches more rows. A destination wider than the
// widest panel in scope falls back to converting from the source.
static constexpr int MAX_CACHE_COLUMNS = 16;
static constexpr int MAX_CACHE_ROWS = 240;
static constexpr size_t CACHE_PIXELS = MAX_CACHE_ROWS * MAX_CACHE_COLUMNS;
static uint32_t column_cache_storage[CACHE_PIXELS] __attribute__((aligned(4)));


bool row_fits(int dst_w, int bitdepth) {
    size_t row_bytes = (bitdepth == 12) ? (size_t)(dst_w * 3 / 2) : (size_t)(dst_w * 2);
    return dst_w > 0 && row_bytes <= MAX_ROW_BYTES;
}


SPIDisplayBus::SPIDisplayBus(uint spi_index, uint sck, uint mosi, uint baudrate)
    : sck_pin(sck), mosi_pin(mosi), requested_baudrate(baudrate) {
    spi = spi_index == 0 ? spi0 : spi1;
    achieved_baudrate = spi_init(spi, baudrate);
    spi_set_format(spi, 8, SPI_CPOL_0, SPI_CPHA_0, SPI_MSB_FIRST);
    gpio_set_function(sck, GPIO_FUNC_SPI);
    gpio_set_function(mosi, GPIO_FUNC_SPI);

    dma_chan = dma_claim_unused_channel(true);
    configure_dma(8);
}

SPIDisplayBus::~SPIDisplayBus() {
    // Runs from the __del__ finaliser, including gc_sweep_all() on soft reset.
    // Release the channel so re-runs do not exhaust DMA, guarded so a double call
    // is a no-op.
    if (dma_chan >= 0) {
        dma_channel_abort(dma_chan);
        dma_channel_unclaim(dma_chan);
        dma_chan = -1;

        // The abort can land mid-transfer, so drain the shifter first. Then undo
        // what the constructor did: the 8-bit frame width a wide-frame update() may
        // have left set, and the SPI function on the clock and data lines. The
        // displays release their own CS.
        while (spi_is_busy(spi)) {
        }
        spi_set_format(spi, 8, SPI_CPOL_0, SPI_CPHA_0, SPI_MSB_FIRST);
        gpio_init(sck_pin);
        gpio_init(mosi_pin);
    }
}

uint32_t SPIDisplayBus::set_baudrate(uint32_t value) {
    // Takes effect on the next transfer. The divider only reaches
    // clk_peri/(2*n), so the rate reached is rounded down from the request.
    requested_baudrate = value;
    achieved_baudrate = spi_set_baudrate(spi, value);
    return achieved_baudrate;
}

void SPIDisplayBus::configure_dma(int bits) {
    dma_channel_config c = dma_channel_get_default_config(dma_chan);
    channel_config_set_transfer_data_size(&c, bits == 16 ? DMA_SIZE_16 : DMA_SIZE_8);
    channel_config_set_dreq(&c, spi_get_dreq(spi, true));
    channel_config_set_read_increment(&c, true);
    channel_config_set_write_increment(&c, false);
    channel_config_set_bswap(&c, bits == 16);
    dma_channel_configure(dma_chan, &c, &spi_get_hw(spi)->dr, nullptr, 0, false);
    dma_frame_bits = bits;
}


SPIDisplay::SPIDisplay(SPIDisplayBus *bus, uint cs, uint dc, int te, uint8_t ram_write,
                       int bitdepth, int width, int height, uint32_t baudrate,
                       int band_lines, int cache_columns, bool cache_wide_double,
                       int spi_frame_bits)
    : bus(bus), cs_mask(1ull << cs), dc_mask(1ull << dc), dc_pin(dc), te_pin(te),
      ram_write_cmd(ram_write),
      fmt(bitdepth == 12 ? RGB444::format : RGB565::format),
      dst_w(width), dst_h(height),
      cache_columns(cache_columns < 0 ? 0 : (cache_columns > MAX_CACHE_COLUMNS ? MAX_CACHE_COLUMNS : cache_columns)),
      cache_wide_double(cache_wide_double),
      spi_frame_bits(spi_frame_bits == 16 ? 16 : 8),
      requested_baudrate(baudrate) {
    // Banding is settled here, since it turns only on the request and the panel
    // height. A band always fits a buffer: row_fits() bounds the row to
    // MAX_ROW_BYTES, and BAND_BYTES is MAX_BAND_LINES of those.
    int requested = band_lines < 1 ? 1 : (band_lines > MAX_BAND_LINES ? MAX_BAND_LINES : band_lines);
    rows_per_band = requested > dst_h ? dst_h : requested;

    // One pin each here, since a group is built by copy and claims no GPIO. Value
    // before direction, so the panel's first CS edge is the one selecting it.
    gpio_init(cs);
    gpio_put(cs, 1);
    gpio_set_dir(cs, GPIO_OUT);

    gpio_init(dc);
    gpio_put(dc, 1);
    gpio_set_dir(dc, GPIO_OUT);

    if (te_pin >= 0) {
        gpio_init((uint)te_pin);
        gpio_set_dir((uint)te_pin, GPIO_IN);
    }

    achieved_baudrate = bus->set_baudrate(requested_baudrate);
}

SPIDisplay::~SPIDisplay() {
    // Release CS so the panel is not left holding a half-written frame open. The
    // bus's finaliser may have run already, so this touches nothing but GPIO.
    gpio_set_mask64(cs_mask);
    gpio_set_dir_masked64(dc_mask, dc_mask);
    gpio_set_mask64(dc_mask);
}

bool SPIDisplay::compatible_with(const SPIDisplay &other) const {
    return bus == other.bus
           && fmt == other.fmt
           && dst_w == other.dst_w
           && dst_h == other.dst_h
           && ram_write_cmd == other.ram_write_cmd
           && requested_baudrate == other.requested_baudrate
           && rows_per_band == other.rows_per_band
           && cache_columns == other.cache_columns
           && spi_frame_bits == other.spi_frame_bits;
}

void SPIDisplay::add(const SPIDisplay &other) {
    cs_mask |= other.cs_mask;
    dc_mask |= other.dc_mask;
}

void SPIDisplay::command(const uint8_t *cmd, size_t cmd_len,
                         const uint8_t *data, size_t data_len) {
    use_baudrate();
    gpio_set_dir_masked64(dc_mask, dc_mask);
    gpio_put_masked64(dc_mask, 0);
    gpio_clr_mask64(cs_mask);
    spi_write_blocking(bus->spi, cmd, cmd_len);
    if (data_len) {
        gpio_put_masked64(dc_mask, dc_mask);
        spi_write_blocking(bus->spi, data, data_len);
    }
    gpio_set_mask64(cs_mask);
}

bool SPIDisplay::te_wait(uint32_t timeout_us) {
    bool success = true;

    uint pin = (te_pin >= 0) ? (uint)te_pin : dc_pin;
    if (te_pin < 0) {
        gpio_set_dir(dc_pin, GPIO_IN);
    }

    uint32_t start = time_us_32();

    // Wait for the rising edge
    while (success && gpio_get(pin) == 0) {
        success = (time_us_32() - start < timeout_us);
    }

    // Wait for the falling edge, if the timeout has yet to be reached
    while (success && gpio_get(pin) != 0) {
        success = (time_us_32() - start < timeout_us);
    }

    if (te_pin < 0) {
        gpio_set_dir(dc_pin, GPIO_OUT);
    }

    return success;
}

TeProbe SPIDisplay::te_probe(uint32_t ms) {
    uint pin = te_pin >= 0 ? (uint)te_pin : dc_pin;
    if (te_pin < 0) {
        gpio_set_dir(dc_pin, GPIO_IN);
    }

    const uint32_t t_start = time_us_32();
    const uint32_t window_us = ms * 1000;
    uint32_t rises = 0, pulses = 0;
    uint32_t first_rise = 0, last_rise = 0, rise_at = 0;
    uint32_t high_total = 0;
    bool level = gpio_get(pin) != 0;

    while (time_us_32() - t_start < window_us) {
        bool now_level = gpio_get(pin) != 0;
        if (now_level == level) {
            continue;
        }
        uint32_t now = time_us_32();
        level = now_level;
        if (now_level) {
            if (rises == 0) {
                first_rise = now;
            }
            last_rise = now;
            rise_at = now;
            ++rises;
        } else if (rises > 0) {
            high_total += now - rise_at;
            ++pulses;
        }
    }

    if (te_pin < 0) {
        gpio_set_dir(dc_pin, GPIO_OUT);
    }

    TeProbe p = {0, 0, rises};
    if (rises > 1) {
        p.period_us = (last_rise - first_rise) / (rises - 1);
    }
    if (pulses > 0) {
        p.high_us = high_total / pulses;
    }
    return p;
}

void SPIDisplay::update(const uint8_t *src, int src_w, int src_h,
                        int rotation, int mirror, int pixel_double,
                        uint32_t bg, bool centred_x, int off_x, bool centred_y, int off_y,
                        bool v_sync, uint32_t timeout_us) {

    // ----- DESCRIPTOR CREATION -----
    uint32_t t_pre = time_us_32();

    use_baudrate();

    bool dbl = pixel_double != 0;

    Transform t = map_transform(rotation, mirror);
    Descriptor d = make_descriptor(src, src_w, src_h, dst_w, dst_h, t, dbl, bg, fmt,
                                   centred_x, off_x, centred_y, off_y);

    ConvertFn convert = select_convert(fmt, dbl);

    uint8_t *front = band_a;   // converted, DMA in flight
    uint8_t *back = band_b;    // converted next, while front streams

    const int band_rows = rows_per_band;

    // Every band is this size except a possibly-shorter final one
    const size_t full_band_bytes = (size_t)band_rows * d.dst_row_bytes;

    // Wider SPI frames cut the PL022's per-frame idle time, but a transfer has to
    // be a whole number of frames, which an odd packed row width does not give.
    const bool wide_frames = spi_frame_bits == 16 && (d.dst_row_bytes % 2) == 0;
    const int frame_shift = wide_frames ? 1 : 0;
    bus->use_frame_bits(wide_frames ? 16 : 8);
    const int dma_chan = bus->dma_chan;
    spi_inst_t *spi = bus->spi;

    // Check if the source address sits anywhere inside the 16MB hardware window for CS1
    uintptr_t src_addr = (uintptr_t)d.src;
    bool src_in_psram = (src_addr >= PSRAM_CACHED_BASE && src_addr < PSRAM_CACHED_BASE + PSRAM_WINDOW);

    // The cache decides here whether it applies, and stays live across bands so a
    // window seeded by one serves the next.
    ColumnCache cache(column_cache_storage, CACHE_PIXELS, cache_columns, cache_wide_double);
    cache.begin(d, convert, dbl, src_in_psram);

    last.pre_us = time_us_32() - t_pre;


    // ----- FIRST BAND CONVERSION -----
    uint32_t t_conv = time_us_32();

    cache.convert(front, 0, band_rows);

    last.convert_us = time_us_32() - t_conv;
    last.convert_total_us = last.convert_us;
    last.stall_us = 0;

    gpio_set_dir_masked64(dc_mask, dc_mask);
    uint32_t t_te = time_us_32();
    if (v_sync) {
        te_wait(timeout_us);
    }
    last.te_wait_us = time_us_32() - t_te;

    uint32_t t_frame = time_us_32();
    last.write_start_us = t_frame;
    gpio_put_masked64(dc_mask, 0);
    gpio_clr_mask64(cs_mask);
    spi_write_blocking(spi, &ram_write_cmd, 1);
    gpio_put_masked64(dc_mask, dc_mask);

    // RAMWR returned with the shifter idle, so widening here truncates nothing
    if (wide_frames) {
        spi_set_format(spi, 16, SPI_CPOL_0, SPI_CPHA_0, SPI_MSB_FIRST);
    }

    // Dispatch the first band
    dma_channel_set_read_addr(dma_chan, front, false);
    dma_channel_set_trans_count(dma_chan, full_band_bytes >> frame_shift, true);  // true starts it

    int row = band_rows;
    while (row < dst_h) {
        int rows = dst_h - row < band_rows ? dst_h - row : band_rows;

        uint32_t t_band = time_us_32();
        cache.convert(back, row, rows);
        uint32_t t_wait = time_us_32();

        dma_channel_wait_for_finish_blocking(dma_chan);
        uint32_t t_kick = time_us_32();
        last.convert_total_us += t_wait - t_band;
        last.stall_us += t_kick - t_wait;

        dma_channel_set_read_addr(dma_chan, back, false);
        size_t bytes = rows == band_rows ? full_band_bytes : (size_t)rows * d.dst_row_bytes;
        dma_channel_set_trans_count(dma_chan, bytes >> frame_shift, true);
        std::swap(front, back);
        row += rows;
    }
    uint32_t t_last = time_us_32();
    dma_channel_wait_for_finish_blocking(dma_chan);
    // The DMA finishes when the last bytes reach the SPI TX FIFO, not when they
    // leave the wire. Drain the FIFO before releasing CS or the final few pixels
    // (up to the 8-entry FIFO) are truncated.
    while (spi_is_busy(spi)) {
    }
    gpio_set_mask64(cs_mask);
    uint32_t t_end = time_us_32();
    last.stall_us += t_end - t_last;
    last.frame_us = t_end - t_frame;

    if (wide_frames) {
        spi_set_format(spi, 8, SPI_CPOL_0, SPI_CPHA_0, SPI_MSB_FIRST);
    }
}

}  // namespace spidisplay

extern "C" {

#include "py/mphal.h"
#include "py/objtuple.h"
#include "py/runtime.h"

// The C++ objects live inline in their mp_objs: one fewer allocation and a single
// lifetime to manage.
typedef struct _SPIDisplayBus_obj_t {
    mp_obj_base_t base;
    spidisplay::SPIDisplayBus bus;
} SPIDisplayBus_obj_t;

// bus_obj roots the bus against the GC, since the C++ object holds a bare pointer
// into it.
typedef struct _SPIDisplay_obj_t {
    mp_obj_base_t base;
    mp_obj_t bus_obj;
    spidisplay::SPIDisplay display;
} SPIDisplay_obj_t;

extern const mp_obj_type_t SPIDisplayBus_type;
extern const mp_obj_type_t SPIDisplay_type;

static mp_obj_t SPIDisplayBus_make_new(const mp_obj_type_t *type, size_t n_args,
                                       size_t n_kw, const mp_obj_t *all_args) {
    enum { ARG_spi, ARG_sck, ARG_mosi, ARG_baudrate };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_spi, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_sck, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_mosi, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_baudrate, MP_ARG_INT, {.u_int = 24000000} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args,
                              MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    if (args[ARG_baudrate].u_int < 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("baudrate must be positive"));
    }

    uint sck = mp_hal_get_pin_obj(args[ARG_sck].u_obj);
    uint mosi = mp_hal_get_pin_obj(args[ARG_mosi].u_obj);

    SPIDisplayBus_obj_t *self = mp_obj_malloc_with_finaliser(SPIDisplayBus_obj_t, type);
    new (&self->bus) spidisplay::SPIDisplayBus((uint)args[ARG_spi].u_int, sck, mosi,
                                               (uint)args[ARG_baudrate].u_int);
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t SPIDisplayBus___del__(mp_obj_t self_in) {
    SPIDisplayBus_obj_t *self = (SPIDisplayBus_obj_t *)MP_OBJ_TO_PTR(self_in);
    self->bus.~SPIDisplayBus();  // idempotent: the destructor guards on dma_chan
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplayBus___del___obj, SPIDisplayBus___del__);

// broadcast(display, display, ...) -> a display whose CS and DC masks carry every
// member's bit, so one frame lands on all of them. The members keep their
// identity, so each can still be brought up and updated on its own. Settings come
// from the first member, once, here.
static mp_obj_t SPIDisplayBus_broadcast(size_t n_args, const mp_obj_t *args) {
    if (n_args < 3) {
        mp_raise_ValueError(MP_ERROR_TEXT("a broadcast group needs at least two displays"));
    }

    for (size_t i = 1; i < n_args; ++i) {
        if (!mp_obj_is_type(args[i], &SPIDisplay_type)) {
            mp_raise_TypeError(MP_ERROR_TEXT("broadcast takes SPIDisplay objects"));
        }
        if (((SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[i]))->bus_obj != args[0]) {
            mp_raise_ValueError(MP_ERROR_TEXT("every member must be on this bus"));
        }
    }

    SPIDisplay_obj_t *first = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[1]);
    SPIDisplay_obj_t *group = mp_obj_malloc_with_finaliser(SPIDisplay_obj_t, &SPIDisplay_type);
    group->bus_obj = first->bus_obj;
    new (&group->display) spidisplay::SPIDisplay(first->display);

    for (size_t i = 2; i < n_args; ++i) {
        SPIDisplay_obj_t *member = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[i]);
        if (!group->display.compatible_with(member->display)) {
            mp_raise_ValueError(MP_ERROR_TEXT("members must agree on bit depth, dimensions, rate and tuning"));
        }
        group->display.add(member->display);
    }
    return MP_OBJ_FROM_PTR(group);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR(SPIDisplayBus_broadcast_obj, 2, SPIDisplayBus_broadcast);

static const mp_rom_map_elem_t SPIDisplayBus_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&SPIDisplayBus___del___obj) },
    { MP_ROM_QSTR(MP_QSTR_broadcast), MP_ROM_PTR(&SPIDisplayBus_broadcast_obj) },
};
static MP_DEFINE_CONST_DICT(SPIDisplayBus_locals_dict, SPIDisplayBus_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    SPIDisplayBus_type,
    MP_QSTR_SPIDisplayBus,
    MP_TYPE_FLAG_NONE,
    make_new, (const void *)SPIDisplayBus_make_new,
    locals_dict, &SPIDisplayBus_locals_dict
);

static mp_obj_t SPIDisplay_make_new(const mp_obj_type_t *type, size_t n_args,
                                    size_t n_kw, const mp_obj_t *all_args) {
    enum { ARG_bus, ARG_cs, ARG_dc, ARG_width, ARG_height, ARG_te, ARG_ram_write,
           ARG_bitdepth, ARG_baudrate, ARG_band_lines, ARG_cache_columns,
           ARG_cache_wide_double, ARG_spi_frame_bits };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_bus, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_cs, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_dc, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_width, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_height, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_te, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_ram_write, MP_ARG_INT, {.u_int = 0x2C} },
        { MP_QSTR_bitdepth, MP_ARG_INT, {.u_int = 16} },
        { MP_QSTR_baudrate, MP_ARG_INT, {.u_int = 24000000} },
        { MP_QSTR_band_lines, MP_ARG_INT, {.u_int = 16} },
        { MP_QSTR_cache_columns, MP_ARG_INT, {.u_int = 16} },
        { MP_QSTR_cache_wide_double, MP_ARG_BOOL, {.u_bool = true} },
        { MP_QSTR_spi_frame_bits, MP_ARG_INT, {.u_int = 16} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args,
                              MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    if (!mp_obj_is_type(args[ARG_bus].u_obj, &SPIDisplayBus_type)) {
        mp_raise_TypeError(MP_ERROR_TEXT("bus must be an SPIDisplayBus"));
    }

    if (args[ARG_height].u_int < 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("height must be positive"));
    }
    if (!spidisplay::row_fits(args[ARG_width].u_int, args[ARG_bitdepth].u_int)) {
        mp_raise_ValueError(MP_ERROR_TEXT("width too wide for the band buffer at this bit depth"));
    }
    if (args[ARG_baudrate].u_int < 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("baudrate must be positive"));
    }

    // te=None is the shared DC line; a Pin is a dedicated TE input.
    int te = -1;
    if (args[ARG_te].u_obj != mp_const_none) {
        te = (int)mp_hal_get_pin_obj(args[ARG_te].u_obj);
    }
    uint cs = mp_hal_get_pin_obj(args[ARG_cs].u_obj);
    uint dc = mp_hal_get_pin_obj(args[ARG_dc].u_obj);

    SPIDisplayBus_obj_t *bus = (SPIDisplayBus_obj_t *)MP_OBJ_TO_PTR(args[ARG_bus].u_obj);
    SPIDisplay_obj_t *self = mp_obj_malloc_with_finaliser(SPIDisplay_obj_t, type);
    self->bus_obj = args[ARG_bus].u_obj;
    new (&self->display) spidisplay::SPIDisplay(
        &bus->bus, cs, dc, te, (uint8_t)args[ARG_ram_write].u_int,
        args[ARG_bitdepth].u_int, args[ARG_width].u_int, args[ARG_height].u_int,
        (uint32_t)args[ARG_baudrate].u_int, args[ARG_band_lines].u_int,
        args[ARG_cache_columns].u_int, args[ARG_cache_wide_double].u_bool,
        args[ARG_spi_frame_bits].u_int);
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t SPIDisplay___del__(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    self->display.~SPIDisplay();  // idempotent: only releases GPIO
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay___del___obj, SPIDisplay___del__);

static mp_obj_t SPIDisplay_command(size_t n_args, const mp_obj_t *args) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[0]);

    uint8_t cmd_byte;
    const uint8_t *cmd;
    size_t cmd_len;
    mp_buffer_info_t cbuf;
    if (mp_obj_is_int(args[1])) {
        cmd_byte = (uint8_t)mp_obj_get_int(args[1]);
        cmd = &cmd_byte;
        cmd_len = 1;
    } else {
        mp_get_buffer_raise(args[1], &cbuf, MP_BUFFER_READ);
        cmd = (const uint8_t *)cbuf.buf;
        cmd_len = cbuf.len;
    }

    uint8_t data_byte;
    const uint8_t *data = nullptr;
    size_t data_len = 0;
    mp_buffer_info_t dbuf;
    if (n_args > 2 && args[2] != mp_const_none) {
        if (mp_obj_is_int(args[2])) {
            data_byte = (uint8_t)mp_obj_get_int(args[2]);
            data = &data_byte;
            data_len = 1;
        } else {
            mp_get_buffer_raise(args[2], &dbuf, MP_BUFFER_READ);
            data = (const uint8_t *)dbuf.buf;
            data_len = dbuf.len;
        }
    }

    self->display.command(cmd, cmd_len, data, data_len);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(SPIDisplay_command_obj, 2, 3, SPIDisplay_command);

static mp_obj_t SPIDisplay_update(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    enum { ARG_self, ARG_image,
           ARG_rotation, ARG_mirror, ARG_pixel_double, ARG_bg, ARG_offset, ARG_v_sync, ARG_timeout_us };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_image, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_rotation, MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_mirror, MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_pixel_double, MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_bg, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_offset, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_v_sync, MP_ARG_BOOL, {.u_bool = false} },
        { MP_QSTR_timeout_us, MP_ARG_INT, {.u_int = 50000} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args, pos_args, kw_args,
                     MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[ARG_self].u_obj);

    mp_buffer_info_t buf;
    mp_get_buffer_raise(args[ARG_image].u_obj, &buf, MP_BUFFER_READ);
    int src_w = mp_obj_get_int(mp_load_attr(args[ARG_image].u_obj, MP_QSTR_width));
    int src_h = mp_obj_get_int(mp_load_attr(args[ARG_image].u_obj, MP_QSTR_height));

    // An empty or negative extent converts to a background-filled frame, since the
    // covered box comes out empty and no source pixel is read. Report it instead.
    if (src_w < 1 || src_h < 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("image width and height must be positive"));
    }

    // The kernel walks the source by the strides these dimensions imply, so a
    // buffer shorter than they claim is read out of bounds and an empty one locks
    // the board. Do not delete this as dead: it is inert only because picovector
    // reports an image's nominal size and discards the length of the buffer it
    // wrapped, so buf.len is already src_w * src_h * 4 and this compares a number
    // with itself. It costs one comparison and works as soon as a source reports a
    // real length.
    size_t src_bytes = (size_t)src_w * (size_t)src_h * spidisplay::RGBA8888::bytes;
    if (buf.len < src_bytes) {
        mp_raise_ValueError(MP_ERROR_TEXT("image buffer is shorter than its dimensions at RGBA8888"));
    }

    // A packed colour carries alpha in the top byte, so it can exceed a signed
    // machine word; truncate to 32 bits (only the low 24 are used).
    uint32_t bg = 0;
    if (args[ARG_bg].u_obj != mp_const_none) {
        bg = (uint32_t)mp_obj_get_int_truncated(args[ARG_bg].u_obj);
    }

    // offset=None centres both axes; an (x, y) pair places the top-left, where
    // either element may be None to centre just that axis.
    bool centred_x = true;
    bool centred_y = true;
    int off_x = 0;
    int off_y = 0;
    if (args[ARG_offset].u_obj != mp_const_none) {
        size_t len;
        mp_obj_t *items;
        mp_obj_get_array(args[ARG_offset].u_obj, &len, &items);
        if (len != 2) {
            mp_raise_ValueError(MP_ERROR_TEXT("offset must be an (x, y) pair"));
        }
        if (items[0] != mp_const_none) {
            centred_x = false;
            off_x = mp_obj_get_int(items[0]);
        }
        if (items[1] != mp_const_none) {
            centred_y = false;
            off_y = mp_obj_get_int(items[1]);
        }
    }

    self->display.update((const uint8_t *)buf.buf, src_w, src_h,
        args[ARG_rotation].u_int,
        args[ARG_mirror].u_int, args[ARG_pixel_double].u_int,
        bg, centred_x, off_x, centred_y, off_y,
        args[ARG_v_sync].u_bool, args[ARG_timeout_us].u_int);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_KW(SPIDisplay_update_obj, 2, SPIDisplay_update);

// The panel's own dimensions, fixed when it was built.
static mp_obj_t SPIDisplay_size(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    mp_obj_t items[2] = {
        mp_obj_new_int(self->display.width()),
        mp_obj_new_int(self->display.height()),
    };
    return mp_obj_new_tuple(2, items);
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_size_obj, SPIDisplay_size);

// Read the pixel-doubled cache window depth, or set it with an argument. Takes
// effect on the next update().
static mp_obj_t SPIDisplay_cache_wide_double(size_t n_args, const mp_obj_t *args) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[0]);
    if (n_args > 1) {
        self->display.set_wide_double(mp_obj_is_true(args[1]));
    }
    return mp_obj_new_bool(self->display.wide_double());
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(SPIDisplay_cache_wide_double_obj, 1, 2,
                                           SPIDisplay_cache_wide_double);

// Read the SPI data frame width for the pixel stream, or set it with an
// argument. 8 or 16; takes effect on the next update().
static mp_obj_t SPIDisplay_spi_frame_bits(size_t n_args, const mp_obj_t *args) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[0]);
    if (n_args > 1) {
        mp_int_t bits = mp_obj_get_int(args[1]);
        if (bits != 8 && bits != 16) {
            mp_raise_ValueError(MP_ERROR_TEXT("spi_frame_bits must be 8 or 16"));
        }
        self->display.set_frame_bits((int)bits);
    }
    return mp_obj_new_int(self->display.frame_bits());
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(SPIDisplay_spi_frame_bits_obj, 1, 2,
                                           SPIDisplay_spi_frame_bits);

// What this panel's rate reached, which is not the request: the divider rounds
// down. Panels on one port each carry their own.
static mp_obj_t SPIDisplay_baudrate(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int_from_uint(self->display.baudrate());
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_baudrate_obj, SPIDisplay_baudrate);

// The most recent update() as one snapshot, reachable by name or by index. See
// FrameStats for what each field means. What the frame went out at, and how it was
// banded, are not here, being fixed at construction: read baudrate() and band_rows().
static mp_obj_t SPIDisplay_stats(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    static const qstr fields[] = {
        MP_QSTR_pre_us, MP_QSTR_convert_us, MP_QSTR_te_wait_us, MP_QSTR_frame_us,
        MP_QSTR_convert_total_us, MP_QSTR_stall_us, MP_QSTR_write_start_us,
    };
    spidisplay::FrameStats s = self->display.stats();
    mp_obj_t items[MP_ARRAY_SIZE(fields)] = {
        mp_obj_new_int_from_uint(s.pre_us),
        mp_obj_new_int_from_uint(s.convert_us),
        mp_obj_new_int_from_uint(s.te_wait_us),
        mp_obj_new_int_from_uint(s.frame_us),
        mp_obj_new_int_from_uint(s.convert_total_us),
        mp_obj_new_int_from_uint(s.stall_us),
        mp_obj_new_int_from_uint(s.write_start_us),
    };
    return mp_obj_new_attrtuple(fields, MP_ARRAY_SIZE(fields), items);
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_stats_obj, SPIDisplay_stats);

// Destination rows per DMA band, after the clamp the request went through, so the
// band count is height over this. Fixed at construction.
static mp_obj_t SPIDisplay_band_rows(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(self->display.band_rows());
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_band_rows_obj, SPIDisplay_band_rows);

// te_probe(ms=250) -> (period_us, high_us, edges). A short high against the
// period means the asserted level is vertical blanking.
static mp_obj_t SPIDisplay_te_probe(size_t n_args, const mp_obj_t *args) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[0]);
    mp_int_t ms = n_args > 1 ? mp_obj_get_int(args[1]) : 250;
    if (ms < 1 || ms > 5000) {
        mp_raise_ValueError(MP_ERROR_TEXT("ms must be 1..5000"));
    }
    spidisplay::TeProbe p = self->display.te_probe((uint32_t)ms);
    mp_obj_t items[3] = {
        mp_obj_new_int_from_uint(p.period_us),
        mp_obj_new_int_from_uint(p.high_us),
        mp_obj_new_int_from_uint(p.edges),
    };
    return mp_obj_new_tuple(3, items);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(SPIDisplay_te_probe_obj, 1, 2, SPIDisplay_te_probe);

static const mp_rom_map_elem_t SPIDisplay_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&SPIDisplay___del___obj) },
    { MP_ROM_QSTR(MP_QSTR_command), MP_ROM_PTR(&SPIDisplay_command_obj) },
    { MP_ROM_QSTR(MP_QSTR_update), MP_ROM_PTR(&SPIDisplay_update_obj) },
    { MP_ROM_QSTR(MP_QSTR_size), MP_ROM_PTR(&SPIDisplay_size_obj) },
    { MP_ROM_QSTR(MP_QSTR_band_rows), MP_ROM_PTR(&SPIDisplay_band_rows_obj) },
    { MP_ROM_QSTR(MP_QSTR_cache_wide_double), MP_ROM_PTR(&SPIDisplay_cache_wide_double_obj) },
    { MP_ROM_QSTR(MP_QSTR_spi_frame_bits), MP_ROM_PTR(&SPIDisplay_spi_frame_bits_obj) },
    { MP_ROM_QSTR(MP_QSTR_baudrate), MP_ROM_PTR(&SPIDisplay_baudrate_obj) },
    { MP_ROM_QSTR(MP_QSTR_stats), MP_ROM_PTR(&SPIDisplay_stats_obj) },
    { MP_ROM_QSTR(MP_QSTR_te_probe), MP_ROM_PTR(&SPIDisplay_te_probe_obj) },
};
static MP_DEFINE_CONST_DICT(SPIDisplay_locals_dict, SPIDisplay_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    SPIDisplay_type,
    MP_QSTR_SPIDisplay,
    MP_TYPE_FLAG_NONE,
    make_new, (const void *)SPIDisplay_make_new,
    locals_dict, &SPIDisplay_locals_dict
);

}  // extern "C"
