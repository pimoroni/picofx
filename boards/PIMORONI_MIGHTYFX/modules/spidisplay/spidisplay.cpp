// SPDX-License-Identifier: MIT
//
// SPIDisplayBus and SPIDisplay implementation and their MicroPython bindings. The
// C++ classes own the SPI/DMA/GPIO and the overlapped band streaming; the extern
// "C" block wraps them as types. Module registration is in spidisplay_bindings.c.

#include <new>

#include "hardware/gpio.h"
#include "hardware/irq.h"
#include "hardware/regs/addressmap.h"
#include "hardware/spi.h"
#include "hardware/sync.h"
#include "pico/platform.h"
#include "pico/time.h"

#include "column_cache.hpp"
#include "interleaver.hpp"
#include "scanline.hpp"
#include "spidisplay.hpp"
#include "sram_allocator.hpp"

// The free SRAM the GC never receives, between these linker symbols; C linkage,
// since spidisplay_bindings.c names the same pair.
extern "C" {
extern uint8_t __GcHeapStart[];
extern uint8_t __GcHeapEnd[];
}

namespace spidisplay {

static constexpr uintptr_t PSRAM_WINDOW = 0x01000000;                   // 16 MB window per CS
static constexpr uintptr_t PSRAM_CACHED_BASE = XIP_BASE + PSRAM_WINDOW; // Start of PSRAM (0x11000000)

// Every display claims its band ring and column cache scratch from here at
// construction. SRAM is required, since the RP2350 M33 has no SRAM data cache, so
// DMA sees CPU writes without maintenance. Claims come from the top of the region,
// so the module's buffer() views keep their bottom-up addresses.
static SRAMAllocator sram;
static bool sram_bound = false;

static SRAMAllocator &allocator() {
    if (!sram_bound) {
        sram.init(__GcHeapStart, __GcHeapEnd);
        sram_bound = true;
    }
    return sram;
}

// Kicks are interrupt-driven on DMA_IRQ_2, a line nothing else in this
// firmware touches (rp2.DMA, PWMCluster and I2S(0) share IRQ 0; I2S(1) has
// IRQ 1), taken exclusively and refcounted by bus lifetimes. irq_owner maps a
// channel to its display only while that display is streaming, so the owner
// table, not FrameState, is what gates the handler. Priority sits above the
// 0x80 everything else uses: this handler is a few microseconds, the I2S one
// runs tens, and a kick must not wait behind audio.
static_assert(NUM_DMA_IRQS > 2, "the interleaver's kicks need DMA_IRQ_2");
static constexpr uint DMA_IRQ2_INDEX = 2;
static constexpr uint8_t DMA_IRQ2_PRIORITY = 0x40;
static SPIDisplay *volatile irq_owner[NUM_DMA_CHANNELS];
static int irq2_handler_refcount = 0;

// In RAM: flash shares the QMI bus with PSRAM, and an XIP miss during a PSRAM
// conversion burst would cost the latency this handler exists to remove. Ack
// before servicing, so a completion of the band kicked below latches fresh.
static void __not_in_flash_func(dma_irq2_handler)(void) {
    uint32_t ints = dma_hw->irq_ctrl[DMA_IRQ2_INDEX].ints;
    dma_hw->irq_ctrl[DMA_IRQ2_INDEX].ints = ints;
    while (ints != 0) {
        uint channel = (uint)__builtin_ctz(ints);
        ints &= ints - 1;
        SPIDisplay *display = irq_owner[channel];
        if (display != nullptr) {
            display->kick_from_isr();
        }
    }
}


#if SPIDISPLAY_PV_CORE1
// The shared worker launches on its first job, and a multicore launch inside a
// stream would starve the wire, so a display pays for it at construction.
// picovector may have launched it already, leaving just the one handshake.
static void core1_nop() {}

static void warm_core1() {
    static bool warmed = false;
    if (!warmed) {
        pv_core1_run(core1_nop);
        pv_core1_join();
        warmed = true;
    }
}
#else
static void warm_core1() {}
#endif


SPIDisplayBus::SPIDisplayBus(uint spi_index, uint sck, uint mosi, uint baudrate)
    : sck_pin(sck), mosi_pin(mosi), requested_baudrate(baudrate) {
    spi = spi_index == 0 ? spi0 : spi1;
    achieved_baudrate = spi_init(spi, baudrate);
    spi_set_format(spi, 8, SPI_CPOL_0, SPI_CPHA_0, SPI_MSB_FIRST);
    gpio_set_function(sck, GPIO_FUNC_SPI);
    gpio_set_function(mosi, GPIO_FUNC_SPI);

    dma_chan = dma_claim_unused_channel(true);
    configure_dma(8);

    // A freshly claimed channel can carry a stale completion latch from a
    // previous owner (rp2.DMA user code, an earlier soft-reset epoch).
    irq_owner[dma_chan] = nullptr;
    dma_irqn_acknowledge_channel(DMA_IRQ2_INDEX, dma_chan);
    if (irq2_handler_refcount++ == 0) {
        irq_set_exclusive_handler(DMA_IRQ_2, dma_irq2_handler);
        irq_set_priority(DMA_IRQ_2, DMA_IRQ2_PRIORITY);
        irq_set_enabled(DMA_IRQ_2, true);
    }
}

SPIDisplayBus::~SPIDisplayBus() {
    // Runs from the __del__ finaliser, including gc_sweep_all() on soft reset.
    // Release the channel so re-runs do not exhaust DMA, guarded so a double call
    // is a no-op.
    if (dma_chan >= 0) {
        // Unroute and disown before the abort, so the handler cannot run for
        // this channel once teardown starts; ack after, so a completion racing
        // the abort cannot re-latch behind it.
        uint32_t save = save_and_disable_interrupts();
        dma_irqn_set_channel_enabled(DMA_IRQ2_INDEX, dma_chan, false);
        irq_owner[dma_chan] = nullptr;
        restore_interrupts_from_disabled(save);
        dma_channel_abort(dma_chan);
        dma_irqn_acknowledge_channel(DMA_IRQ2_INDEX, dma_chan);
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

        if (--irq2_handler_refcount == 0) {
            irq_set_enabled(DMA_IRQ_2, false);
            irq_remove_handler(DMA_IRQ_2, dma_irq2_handler);
        }
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
                       uint8_t te_on, uint8_t te_off, uint8_t te_mode,
                       int bitdepth, int width, int height, uint32_t baudrate,
                       int band_lines, int cache_columns, int stage_lines)
    : bus(bus), cs_mask(1ull << cs), dc_mask(1ull << dc), dc_pin(dc), te_pin(te),
      ram_write_cmd(ram_write), te_on_cmd(te_on), te_off_cmd(te_off),
      te_mode_byte(te_mode),
      fmt(bitdepth == 12 ? RGB444::format : RGB565::format),
      dst_w(width), dst_h(height),
      cache_columns(cache_columns < 0 ? 0 : (cache_columns > width ? width : cache_columns)),
      requested_baudrate(baudrate) {
    // Banding is settled here, since it turns only on the request and the panel
    // height; the workspace claim below is sized for whatever it settles on.
    int requested = band_lines < 1 ? 1 : band_lines;
    rows_per_band = requested > dst_h ? dst_h : requested;

    // The staging depth in whole bands plus the reserved in-flight slot, at
    // least the double buffer and no more than the frame plus that spare.
    slot_count = stage_lines < 1
        ? 2 : 1 + (stage_lines + rows_per_band - 1) / rows_per_band;
    int frame_bands = (dst_h + rows_per_band - 1) / rows_per_band;
    if (slot_count > frame_bands + 1) {
        slot_count = frame_bands + 1;
    }
    if (slot_count < 2) {
        slot_count = 2;
    }

    // The band ring, the cache scratch, then the palette, one claim. Rounding
    // the band to 4 keeps every slot and the cache word-aligned. The cache is
    // sized by width: a window caches up to dst_w source rows of its columns
    // (column_cache.hpp), so height would under-provision a landscape panel.
    full_row_bytes = packed_row_bytes(dst_w, bitdepth);
    band_bytes = (rows_per_band * full_row_bytes + 3) & ~(size_t)3;
    cache_capacity = this->cache_columns * dst_w * 4;
    sram_claim_bytes = (size_t)slot_count * band_bytes + (size_t)cache_capacity + PALETTE_BYTES;
    sram_claim = allocator().claim(sram_claim_bytes);
    owns_sram_claim = sram_claim != nullptr;
    if (!owns_sram_claim) {
        // The wrapper raises on has_sram(); no GPIO is configured, so the
        // half-built object's destructor has nothing to undo but the claim.
        achieved_baudrate = 0;
        return;
    }

    // One pin each here, since a group is built by copy and claims no GPIO. Value
    // before direction, so the panel's first CS edge is the one selecting it.
    gpio_init(cs);
    gpio_put(cs, 1);
    gpio_set_dir(cs, GPIO_OUT);

    gpio_init(dc);
    gpio_put(dc, 1);
    gpio_set_dir(dc, GPIO_OUT);

    // A diode-fitted breakout cannot drive the shared line low, so reading TE off
    // DC needs the pad to restore it. Harmless against an actively driven TE.
    gpio_pull_down(dc);

    if (te_pin >= 0) {
        gpio_init((uint)te_pin);
        gpio_set_dir((uint)te_pin, GPIO_IN);
    }

    achieved_baudrate = bus->set_baudrate(requested_baudrate);
    warm_core1();
}

SPIDisplay::~SPIDisplay() {
    // A finaliser can run while a channel still names this display; scan by
    // slot index, since the bus's own finaliser may already have taken it and
    // this destructor never dereferences bus.
    for (uint channel = 0; channel < NUM_DMA_CHANNELS; ++channel) {
        if (irq_owner[channel] == this) {
            uint32_t save = save_and_disable_interrupts();
            dma_irqn_set_channel_enabled(DMA_IRQ2_INDEX, channel, false);
            irq_owner[channel] = nullptr;
            restore_interrupts_from_disabled(save);
            dma_irqn_acknowledge_channel(DMA_IRQ2_INDEX, channel);
        }
    }

    // Give the workspace back, guarded so a second destruction is a no-op and a
    // broadcast copy (which shares its member's claim) releases nothing. Both
    // owner and sharer drop the pointer, so update() is refused afterwards.
    if (owns_sram_claim) {
        allocator().release(sram_claim);
        owns_sram_claim = false;
    }
    sram_claim = nullptr;

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
           && slot_count == other.slot_count;
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

// TEON and TEOFF reach the one member the sync masks name, not every line this
// display drives: on a shared DC net a second panel at TEON adds its blanking to
// the one being waited on, and the wait locks to whichever came first.
void SPIDisplay::te_command(uint8_t opcode, const uint8_t *data, size_t data_len) {
    use_baudrate();
    gpio_set_dir_masked64(sync_dc_mask, sync_dc_mask);
    gpio_put_masked64(sync_dc_mask, 0);
    gpio_clr_mask64(sync_cs_mask);
    spi_write_blocking(bus->spi, &opcode, 1);
    if (data_len) {
        gpio_put_masked64(sync_dc_mask, sync_dc_mask);
        spi_write_blocking(bus->spi, data, data_len);
    }
    gpio_set_mask64(sync_cs_mask);
}

void SPIDisplay::arm(bool v_sync, uint32_t timeout_us) {
    if (state != FrameState::PREPARED) {
        return;
    }

    // TEON before the line is released, since the command's data phase drives DC
    // high and the wait would otherwise begin on a level this display just set.
    if (sync_cs_mask != 0) {
        te_command(te_on_cmd, &te_mode_byte, 1);
    }

    gpio_set_dir_masked64(dc_mask, dc_mask);
    // Drive DC low before the release below: the data phase leaves it high, and a
    // released line decaying through the pull-down reads as a completed blanking.
    // This is also the level the RAMWR command phase needs, and CS is high here so
    // no panel is listening.
    gpio_put_masked64(dc_mask, 0);
    te_started_us = time_us_32();
    te_timeout_budget_us = timeout_us;
    te_fired = !v_sync;
    te_high_seen = false;
    if (v_sync) {
        uint pin = (te_pin >= 0) ? (uint)te_pin : dc_pin;
        if (te_pin < 0) {
            gpio_set_dir(dc_pin, GPIO_IN);
        }
        te_raw_prev = gpio_get(pin) != 0;
    } else {
        last.te_wait_us = 0;
    }
    state = FrameState::ARMED;
}

void SPIDisplay::te_fire(uint32_t now) {
    if (te_pin < 0) {
        gpio_set_dir(dc_pin, GPIO_OUT);
    }
    last.te_wait_us = now - te_started_us;
    te_fired = true;
}

bool SPIDisplay::poll_te() {
    if (state != FrameState::ARMED) {
        return false;
    }
    if (te_fired) {
        return true;
    }

    uint32_t now = time_us_32();
    uint pin = (te_pin >= 0) ? (uint)te_pin : dc_pin;
    bool level = gpio_get(pin) != 0;

    // TE shares the DC node, so the level right after the direction flip can
    // still be settling: an edge counts only when two consecutive samples agree.
    bool settled = level == te_raw_prev;
    te_raw_prev = level;
    if (settled) {
        if (level) {
            if (!te_high_seen) {
                te_high_started_us = now;
            }
            te_high_seen = true;
        } else if (te_high_seen) {
            // A pulse already up when the wait began started unobserved, so its
            // length says nothing and only one seen to rise is judged short.
            if (te_high_started_us - te_started_us < JOINED_HIGH_US) {
                ++te_joined_wait_count;
            } else if (now - te_high_started_us < SHORT_WAIT_US) {
                ++te_short_wait_count;
            }
            te_fire(now);
            return true;
        }
    }

    if (now - te_started_us >= te_timeout_budget_us) {
        ++te_timeout_count;
        te_fire(now);
        return true;
    }
    return false;
}

TeProbe SPIDisplay::te_probe(uint32_t ms) {
    uint pin = te_pin >= 0 ? (uint)te_pin : dc_pin;
    if (te_pin < 0) {
        // The probe starts from a genuine low for the same reason arm() does
        gpio_put(dc_pin, 0);
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

TeCapture SPIDisplay::te_capture(uint32_t edges, uint32_t timeout_ms) {
    if (edges > TeCapture::MAX_EDGES) {
        edges = TeCapture::MAX_EDGES;
    }

    uint pin = te_line();
    if (te_pin < 0) {
        // The capture starts from a genuine low for the same reason arm() does
        gpio_put(dc_pin, 0);
        gpio_set_dir(dc_pin, GPIO_IN);
    }

    TeCapture out = {};
    bool level = gpio_get(pin) != 0;
    bool raw_prev = level;
    bool high_seen = false;

    const uint32_t t_start = time_us_32();
    const uint32_t budget_us = timeout_ms * 1000;
    while (out.count < edges) {
        if (time_us_32() - t_start >= budget_us) {
            break;
        }
        bool raw = gpio_get(pin) != 0;
        // An edge counts only when two consecutive samples agree and only after a
        // genuine high, as poll_te() does: the level right after the direction flip
        // can still be settling on a shared node.
        bool settled = raw == raw_prev;
        raw_prev = raw;
        if (!settled || raw == level) {
            continue;
        }
        level = raw;
        if (raw) {
            high_seen = true;
        } else if (high_seen) {
            out.falls[out.count++] = time_us_32();
        }
    }
    out.finished_us = time_us_32();

    if (te_pin < 0) {
        gpio_set_dir(dc_pin, GPIO_OUT);
    }
    return out;
}

TePhase SPIDisplay::te_phase(SPIDisplay &first, SPIDisplay &second,
                             uint32_t period_us, uint32_t edges, uint32_t timeout_ms) {
    constexpr uint32_t MAX_EDGES = 8;
    if (edges > MAX_EDGES) {
        edges = MAX_EDGES;
    }

    SPIDisplay *displays[2] = {&first, &second};
    uint pins[2];
    for (int i = 0; i < 2; ++i) {
        pins[i] = displays[i]->te_pin >= 0 ? (uint)displays[i]->te_pin : displays[i]->dc_pin;
        if (displays[i]->te_pin < 0) {
            // The capture starts from a genuine low for the same reason arm() does
            gpio_put(displays[i]->dc_pin, 0);
            gpio_set_dir(displays[i]->dc_pin, GPIO_IN);
        }
    }

    uint32_t falls[2][MAX_EDGES];
    uint32_t counts[2] = {0, 0};
    bool levels[2], raw_prev[2];
    bool high_seen[2] = {false, false};
    for (int i = 0; i < 2; ++i) {
        levels[i] = raw_prev[i] = gpio_get(pins[i]) != 0;
    }

    const uint32_t t_start = time_us_32();
    const uint32_t budget_us = timeout_ms * 1000;
    while (counts[0] < edges || counts[1] < edges) {
        if (time_us_32() - t_start >= budget_us) {
            break;
        }
        for (int i = 0; i < 2; ++i) {
            if (counts[i] >= edges) {
                continue;
            }
            bool raw = gpio_get(pins[i]) != 0;
            // TE shares the DC node, so the level right after the direction flip
            // can still be settling: an edge counts only when two consecutive
            // samples agree, as poll_te() does, and only after a genuine high.
            bool settled = raw == raw_prev[i];
            raw_prev[i] = raw;
            if (!settled || raw == levels[i]) {
                continue;
            }
            levels[i] = raw;
            if (raw) {
                high_seen[i] = true;
            } else if (high_seen[i]) {
                falls[i][counts[i]++] = time_us_32();
            }
        }
    }
    const uint32_t finished = time_us_32();

    for (int i = 0; i < 2; ++i) {
        if (displays[i]->te_pin < 0) {
            gpio_set_dir(displays[i]->dc_pin, GPIO_OUT);
        }
    }

    TePhase result = {false, 0, 0};
    if (counts[0] < 2 || counts[1] < 2) {
        return result;
    }

    // Each line's falls fold onto one period against a shared reference, the
    // median taken so a missed or doubled edge cannot swing the answer. The
    // difference goes signed before the reduction: 2**32 is not a multiple of a
    // TE period, so reducing an unsigned wrap would bias every fall that
    // precedes the reference.
    const uint32_t ref = falls[0][0];
    uint32_t offsets[2];
    for (int i = 0; i < 2; ++i) {
        uint32_t values[MAX_EDGES];
        for (uint32_t k = 0; k < counts[i]; ++k) {
            int32_t folded = (int32_t)(falls[i][k] - ref) % (int32_t)period_us;
            if (folded < 0) {
                folded += period_us;
            }
            values[k] = (uint32_t)folded;
        }
        for (uint32_t k = 1; k < counts[i]; ++k) {
            uint32_t value = values[k];
            uint32_t j = k;
            while (j > 0 && values[j - 1] > value) {
                values[j] = values[j - 1];
                --j;
            }
            values[j] = value;
        }
        offsets[i] = values[counts[i] / 2];
    }

    int64_t skew = ((int64_t)offsets[0] - (int64_t)offsets[1]) % (int64_t)period_us;
    if (skew < 0) {
        skew += period_us;
    }
    if (skew > (int64_t)(period_us / 2)) {
        skew -= period_us;
    }

    const uint32_t last_a = falls[0][counts[0] - 1];
    const uint32_t last_b = falls[1][counts[1] - 1];
    const uint32_t newest = (int32_t)(last_a - last_b) >= 0 ? last_a : last_b;
    result.ok = true;
    result.skew_us = (int32_t)skew;
    result.age_us = finished - newest;
    return result;
}

void SPIDisplay::prepare(const uint8_t *src, int src_w, int src_h, int src_stride,
                         const uint8_t *palette, size_t palette_len,
                         int rotation, int mirror, int pixel_double,
                         bool centred_x, int off_x, bool centred_y, int off_y,
                         bool tile_x, bool tile_y, uint32_t bg,
                         uint64_t target_cs, uint64_t target_dc,
                         uint64_t sync_cs, uint64_t sync_dc) {
    uint32_t t_pre = time_us_32();

    // This write owns its lines from here until IDLE clears them. A caller naming
    // lines this display does not drive is refused at the binding.
    target_cs_mask = target_cs;
    target_dc_mask = target_dc;
    sync_cs_mask = sync_cs;
    sync_dc_mask = sync_dc;

    use_baudrate();

    bool dbl = pixel_double != 0;
    bool indexed = palette != nullptr;

    Transform t = map_transform(rotation, mirror);
    desc = make_descriptor(src, src_w, src_h, dst_w, dst_h, fmt, t, dbl,
                           centred_x, off_x, centred_y, off_y,
                           tile_x, tile_y, bg,
                           src_stride,
                           indexed ? Indexed8::bytes : RGBA8888::bytes);

    // The table is built every frame, unconditionally: upstream assigns palette
    // entries in place, so a cached copy would go stale silently, and the work is
    // a fraction of a percent of a convert. Compositing the entries here is what
    // makes an indexed source's transparency free per pixel.
    if (indexed) {
        uint8_t *table = sram_claim + (size_t)slot_count * band_bytes + (size_t)cache_capacity;
        prepare_palette(table, palette, palette_len, desc.bg_r, desc.bg_g, desc.bg_b);
        desc.palette = table;
    }

    ConvertFn convert = select_convert(fmt, indexed);

    // Every band is this size except a possibly-shorter final one
    full_band_bytes = (size_t)rows_per_band * desc.dst_row_bytes;

    // Wider SPI frames cut the PL022's per-frame idle time (1.5 clocks between
    // frames whatever their width, 7.9% of frame time at 8 bits), but a transfer
    // has to be a whole number of frames, so an odd packed row width - RGB444 at
    // half the possible widths - falls back to 8-bit frames by itself.
    wide_frames = (desc.dst_row_bytes % 2) == 0;
    frame_shift = wide_frames ? 1 : 0;
    bus->use_frame_bits(wide_frames ? 16 : 8);

    // Check if the source address sits anywhere inside the 16MB hardware window for CS1
    uintptr_t src_addr = (uintptr_t)desc.src;
    bool src_in_psram = (src_addr >= PSRAM_CACHED_BASE && src_addr < PSRAM_CACHED_BASE + PSRAM_WINDOW);

    // The cache decides here whether it applies, and stays live across bands so a
    // window seeded by one serves the next.
    cache = ColumnCache((uint32_t *)(sram_claim + (size_t)slot_count * band_bytes),
                        cache_capacity, cache_columns);
    cache.begin(desc, convert, src_in_psram);

    last.pre_us = time_us_32() - t_pre;
    last.convert_total_us = 0;
    last.stall_us = 0;
    last.core1_rows = 0;

    rows_converted = 0;
    rows_kicked = 0;
    bands_kicked = 0;
    stall_pending = false;
    state = FrameState::PREPARED;

    // The first band, then the whole ring: a staged display must carry its
    // head start out of prepare(), since a TE edge landing right after arm()
    // would otherwise start the stream with whatever the wait happened to
    // allow. The ring room rule holds this to band 0 when stage_lines is 0.
    uint32_t t_conv = time_us_32();
    step_convert(rows_per_band);
    last.convert_us = time_us_32() - t_conv;
    while (step_convert(rows_per_band)) {
    }
}

void SPIDisplay::start_stream() {
    if (state != FrameState::ARMED || !te_fired) {
        return;
    }

    uint32_t t_frame = time_us_32();
    frame_started_us = t_frame;
    last.write_start_us = t_frame;
    gpio_put_masked64(write_dc(), 0);
    gpio_clr_mask64(write_cs());
    spi_write_blocking(bus->spi, &ram_write_cmd, 1);
    gpio_put_masked64(write_dc(), write_dc());

    // RAMWR returned with the shifter idle, so widening here truncates nothing
    if (wide_frames) {
        spi_set_format(bus->spi, 16, SPI_CPOL_0, SPI_CPHA_0, SPI_MSB_FIRST);
    }

    // Own the channel, then route it, then dispatch the first band, with the
    // counters and state settled before the trigger so a completion can never
    // observe pre-kick values. The ack clears any latch a missed teardown left.
    dma_irqn_acknowledge_channel(DMA_IRQ2_INDEX, bus->dma_chan);
    irq_owner[bus->dma_chan] = this;
    dma_irqn_set_channel_enabled(DMA_IRQ2_INDEX, bus->dma_chan, true);
    rows_kicked = rows_per_band;
    bands_kicked = 1;
    state = FrameState::STREAMING;
    dma_channel_set_read_addr(bus->dma_chan, slot_ptr(0), false);
    dma_channel_set_trans_count(bus->dma_chan, full_band_bytes >> frame_shift, true);  // true starts it
}

// In RAM for the same QMI-contention reason as the handler. Busy means the
// completion this entry answers was already serviced by a masked thread kick,
// so touching the registers would corrupt the band in flight.
void __not_in_flash_func(SPIDisplay::kick_from_isr)() {
    if (dma_channel_is_busy(bus->dma_chan)) {
        return;
    }
    if (rows_kicked >= dst_h) {
        return;   // The final band's completion; the polled finish owns CS
    }

    int next = dst_h - rows_kicked < rows_per_band ? dst_h - rows_kicked
                                                   : rows_per_band;
    if (rows_converted - rows_kicked < next) {
        // The wire is starving; the thread's next kick closes the clock.
        if (!stall_pending) {
            stall_pending = true;
            stall_started_us = time_us_32();
        }
        return;
    }

    int band = bands_kicked;
    rows_kicked = rows_kicked + next;
    bands_kicked = band + 1;
    dma_channel_set_read_addr(bus->dma_chan, slot_ptr(band), false);
    size_t bytes = next == rows_per_band ? full_band_bytes
                                         : (size_t)next * desc.dst_row_bytes;
    dma_channel_set_trans_count(bus->dma_chan, bytes >> frame_shift, true);
}

bool SPIDisplay::step_convert(int max_rows) {
    if (state != FrameState::PREPARED && state != FrameState::ARMED
        && state != FrameState::STREAMING) {
        return false;
    }
    if (max_rows < 1) {
        return false;
    }
    int room = convert_room();
    if (room < 1) {
        return false;
    }

    int rows = max_rows < room ? max_rows : room;
    int write_band = rows_converted / rows_per_band;
    int fill = rows_converted - write_band * rows_per_band;
    uint32_t t_band = time_us_32();
    uint32_t core1_before = core1_rows_total;
    cache.convert(slot_ptr(write_band) + (size_t)fill * desc.dst_row_bytes,
                  rows_converted, rows);
    last.convert_total_us += time_us_32() - t_band;
    last.core1_rows += core1_rows_total - core1_before;
    // The counter publishes these rows to the DMA_IRQ_2 handler, so the pixel
    // stores must not be reordered past it.
    __compiler_memory_barrier();
    rows_converted = rows_converted + rows;
    return true;
}

// The thread-side kick, now the fallback for bands that finish converting
// while the channel already sits idle; completions themselves kick from the
// DMA_IRQ_2 handler. The check-ack-kick runs under PRIMASK so the handler
// cannot interleave with it, and the ack retires the pended completion this
// idleness came from so a stale handler entry finds nothing.
bool SPIDisplay::try_kick() {
    if (state != FrameState::STREAMING || rows_kicked >= dst_h) {
        return false;
    }

    uint32_t save = save_and_disable_interrupts();
    int next = dst_h - rows_kicked < rows_per_band ? dst_h - rows_kicked
                                                   : rows_per_band;
    if (rows_converted - rows_kicked < next
        || dma_channel_is_busy(bus->dma_chan)) {
        restore_interrupts_from_disabled(save);
        return false;
    }
    dma_irqn_acknowledge_channel(DMA_IRQ2_INDEX, bus->dma_chan);

    if (stall_pending) {
        last.stall_us += time_us_32() - stall_started_us;
        stall_pending = false;
    }

    int band = bands_kicked;
    rows_kicked = rows_kicked + next;
    bands_kicked = band + 1;
    dma_channel_set_read_addr(bus->dma_chan, slot_ptr(band), false);
    size_t bytes = next == rows_per_band ? full_band_bytes
                                         : (size_t)next * desc.dst_row_bytes;
    dma_channel_set_trans_count(bus->dma_chan, bytes >> frame_shift, true);
    restore_interrupts_from_disabled(save);
    return true;
}

bool SPIDisplay::finish_if_drained() {
    if (state != FrameState::STREAMING || rows_kicked < dst_h) {
        return false;
    }

    uint32_t now = time_us_32();
    // The DMA finishes when the last bytes reach the SPI TX FIFO, not when they
    // leave the wire. Drain the FIFO before releasing CS or the final few pixels
    // (up to the 8-entry FIFO) are truncated.
    if (dma_channel_is_busy(bus->dma_chan) || spi_is_busy(bus->spi)) {
        if (!stall_pending) {
            stall_pending = true;
            stall_started_us = now;
        }
        return false;
    }

    gpio_set_mask64(write_cs());
    uint32_t t_end = time_us_32();
    if (stall_pending) {
        last.stall_us += t_end - stall_started_us;
        stall_pending = false;
    }
    last.frame_us = t_end - frame_started_us;

    // Unroute before going IDLE, so the final band's completion, if its
    // handler entry is still pended, finds no status and no owner.
    uint32_t save = save_and_disable_interrupts();
    dma_irqn_set_channel_enabled(DMA_IRQ2_INDEX, bus->dma_chan, false);
    irq_owner[bus->dma_chan] = nullptr;
    dma_irqn_acknowledge_channel(DMA_IRQ2_INDEX, bus->dma_chan);
    restore_interrupts_from_disabled(save);

    if (wide_frames) {
        spi_set_format(bus->spi, 8, SPI_CPOL_0, SPI_CPHA_0, SPI_MSB_FIRST);
    }

    // After the format is back to 8 bits, and before the masks are dropped. Every
    // route out of a frame passes through here or abort_frame(), so a panel cannot
    // be left reaching the shared line.
    if (sync_cs_mask != 0) {
        te_command(te_off_cmd, nullptr, 0);
    }

    target_cs_mask = 0;
    target_dc_mask = 0;
    sync_cs_mask = 0;
    sync_dc_mask = 0;
    state = FrameState::IDLE;
    return true;
}

bool SPIDisplay::step(int max_rows) {
    bool advanced = try_kick();
    advanced |= step_convert(max_rows);
    advanced |= try_kick();
    advanced |= finish_if_drained();
    return advanced;
}

uint32_t SPIDisplay::deadline_us() const {
    if (state != FrameState::STREAMING || !dma_channel_is_busy(bus->dma_chan)) {
        return 0;
    }
    uint32_t remaining = dma_channel_hw_addr(bus->dma_chan)->transfer_count;
    uint32_t frame_bits = 8u << frame_shift;
    return (uint32_t)(((uint64_t)remaining * frame_bits * 1000000u) / achieved_baudrate);
}

uint32_t SPIDisplay::convert_debt_us() const {
    int done = rows_converted;
    int remaining = dst_h - done;
    if (done <= 0 || remaining <= 0 || last.convert_total_us == 0) {
        return 0;
    }
    return (uint32_t)(((uint64_t)last.convert_total_us * (uint64_t)remaining) / (uint64_t)done);
}

uint32_t SPIDisplay::wire_window_us() const {
    if (achieved_baudrate == 0) {
        return 0;
    }
    // A staged frame's own row width, or the whole panel's when nothing is staged,
    // so a tearing margin can be priced at construction and not only after a frame.
    uint64_t row_bytes = desc.dst_row_bytes > 0 ? (uint64_t)desc.dst_row_bytes
                                                : (uint64_t)full_row_bytes;
    uint64_t bits = row_bytes * 8u * (uint64_t)dst_h;
    uint64_t us = (bits * 1000000u) / achieved_baudrate;
    // Plus the per-band overhead, measured the same on both panel sizes: a 320-row
    // frame streams in 42,016us against 38,400 of pure bits, and a 240-row one in
    // 31,512 against 28,800.
    return (uint32_t)((us * 1094u) / 1000u);
}

void SPIDisplay::abort_frame() {
    if (state == FrameState::IDLE) {
        return;
    }
    if (state == FrameState::STREAMING) {
        // Unroute and disown before the abort so the handler cannot kick into
        // it; ack after, so a completion racing the abort cannot re-latch.
        uint32_t save = save_and_disable_interrupts();
        dma_irqn_set_channel_enabled(DMA_IRQ2_INDEX, bus->dma_chan, false);
        irq_owner[bus->dma_chan] = nullptr;
        restore_interrupts_from_disabled(save);
        dma_channel_abort(bus->dma_chan);
        dma_irqn_acknowledge_channel(DMA_IRQ2_INDEX, bus->dma_chan);
        while (spi_is_busy(bus->spi)) {
        }
        if (wide_frames) {
            spi_set_format(bus->spi, 8, SPI_CPOL_0, SPI_CPHA_0, SPI_MSB_FIRST);
        }
    }
    // An armed display's TE line is an input until the edge fires.
    if (state == FrameState::ARMED && !te_fired && te_pin < 0) {
        gpio_set_dir(dc_pin, GPIO_OUT);
    }
    gpio_set_mask64(write_cs());
    gpio_set_dir_masked64(write_dc(), write_dc());
    gpio_set_mask64(write_dc());

    // Sent whether or not arm() reached TEON, a repeat costing one opcode where a
    // panel left asserting costs the next wait its edge.
    if (sync_cs_mask != 0 && !released()) {
        te_command(te_off_cmd, nullptr, 0);
    }

    stall_pending = false;
    target_cs_mask = 0;
    target_dc_mask = 0;
    sync_cs_mask = 0;
    sync_dc_mask = 0;
    state = FrameState::IDLE;
}

void SPIDisplay::update(const uint8_t *src, int src_w, int src_h, int src_stride,
                        const uint8_t *palette, size_t palette_len,
                        int rotation, int mirror, int pixel_double,
                        bool centred_x, int off_x, bool centred_y, int off_y,
                        bool tile_x, bool tile_y, uint32_t bg,
                        bool v_sync, uint32_t timeout_us, uint32_t sync_delay_us,
                        uint64_t target_cs, uint64_t target_dc,
                        uint64_t sync_cs, uint64_t sync_dc) {
    prepare(src, src_w, src_h, src_stride, palette, palette_len,
            rotation, mirror, pixel_double,
            centred_x, off_x, centred_y, off_y,
            tile_x, tile_y, bg,
            target_cs, target_dc, sync_cs, sync_dc);
    arm(v_sync, timeout_us);
    while (!poll_te()) {
    }
    if (v_sync && sync_delay_us) {
        const uint32_t released = time_us_32();
        while (time_us_32() - released < sync_delay_us) {
        }
    }
    start_stream();
    while (state != FrameState::IDLE) {
        step(rows_per_band);
    }
}

}  // namespace spidisplay

extern "C" {

#include "py/mphal.h"
#include "py/objtuple.h"
#include "py/runtime.h"

// What the module's buffer()/buffer_size() can offer: the span between the canvas
// claims and the display claims. Defined here so spidisplay_bindings.c needs no
// C++ types.
size_t spidisplay_sram_available(void) {
    return spidisplay::allocator().available();
}

// Bytes from the region base to the lowest display claim, which an explicitly
// placed view is measured against.
size_t spidisplay_sram_headroom(void) {
    return spidisplay::allocator().headroom();
}

// Claim a canvas from the bottom of the region, reporting its offset from the base
// so the binding can build a view without a pointer. -1 when it does not fit.
long long spidisplay_sram_claim_low(size_t bytes) {
    uint8_t *base = spidisplay::allocator().claim_low(bytes);
    if (base == nullptr) {
        return -1;
    }
    return (long long)spidisplay::allocator().low_offset(base);
}

void spidisplay_sram_release_low(void) {
    spidisplay::allocator().release_low();
}

// Whether a conversion is halved across both cores, for the module's
// dual_convert(). Reading it back is what a tool records alongside its timings, and
// what tells a caller whether this firmware has a second core to convert on at all:
// a build without the core1 worker always reports off.
int spidisplay_dual_convert(void) {
#if SPIDISPLAY_PV_CORE1
    return spidisplay::dual_convert ? 1 : 0;
#else
    return 0;
#endif
}

void spidisplay_set_dual_convert(int enable) {
    spidisplay::dual_convert = enable != 0;
}

// The C++ objects live inline in their mp_objs: one fewer allocation and a single
// lifetime to manage.
typedef struct _SPIDisplayBus_obj_t {
    mp_obj_base_t base;
    spidisplay::SPIDisplayBus bus;
} SPIDisplayBus_obj_t;

// bus_obj roots the bus against the GC, since the C++ object holds a bare pointer
// into it. sram_owner_obj roots the member whose SRAM claim a broadcast group
// shares, so the owner cannot be finalised under the group; none elsewhere.
// staged_image roots a prepare()d frame's source: the staged Descriptor holds a
// raw pointer and Python runs between prepare() and update_all().
typedef struct _SPIDisplay_obj_t {
    mp_obj_base_t base;
    mp_obj_t bus_obj;
    mp_obj_t sram_owner_obj;
    mp_obj_t staged_image;
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
    // One member is allowed: the group is then a copy of that display, which is the
    // same frame the member's own update writes, so a wall written for a hub still
    // runs where a single panel answered.
    if (n_args < 2) {
        mp_raise_ValueError(MP_ERROR_TEXT("a broadcast group needs at least one display"));
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
    group->staged_image = mp_const_none;
    // The copy shares the first member's SRAM claim, so root that member for the
    // group's lifetime. Explicitly deleting the member still dangles the group,
    // the same misuse as deleting the bus under a display.
    group->sram_owner_obj = args[1];
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
           ARG_te_on, ARG_te_off, ARG_te_mode,
           ARG_bitdepth, ARG_baudrate, ARG_band_lines, ARG_cache_columns,
           ARG_stage_lines };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_bus, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_cs, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_dc, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_width, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_height, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_te, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_ram_write, MP_ARG_INT, {.u_int = 0x2C} },
        { MP_QSTR_te_on, MP_ARG_INT, {.u_int = 0x35} },
        { MP_QSTR_te_off, MP_ARG_INT, {.u_int = 0x34} },
        { MP_QSTR_te_mode, MP_ARG_INT, {.u_int = 0x00} },
        { MP_QSTR_bitdepth, MP_ARG_INT, {.u_int = 16} },
        { MP_QSTR_baudrate, MP_ARG_INT, {.u_int = 24000000} },
        { MP_QSTR_band_lines, MP_ARG_INT, {.u_int = 16} },
        { MP_QSTR_cache_columns, MP_ARG_INT, {.u_int = 16} },
        { MP_QSTR_stage_lines, MP_ARG_INT, {.u_int = 0} },
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
    if (args[ARG_width].u_int < 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("width must be positive"));
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
    self->sram_owner_obj = mp_const_none;
    self->staged_image = mp_const_none;
    new (&self->display) spidisplay::SPIDisplay(
        &bus->bus, cs, dc, te, (uint8_t)args[ARG_ram_write].u_int,
        (uint8_t)args[ARG_te_on].u_int, (uint8_t)args[ARG_te_off].u_int,
        (uint8_t)args[ARG_te_mode].u_int,
        args[ARG_bitdepth].u_int, args[ARG_width].u_int, args[ARG_height].u_int,
        (uint32_t)args[ARG_baudrate].u_int, args[ARG_band_lines].u_int,
        args[ARG_cache_columns].u_int, args[ARG_stage_lines].u_int);

    // A failed claim configured no GPIO, so the orphan's finaliser has nothing to
    // undo; raise with both sides of the shortfall.
    if (!self->display.has_sram()) {
        mp_raise_msg_varg(&mp_type_ValueError,
            MP_ERROR_TEXT("display workspace needs %u bytes but only %u are free;"
                          " release old screens (shutdown() then gc.collect())"
                          " or reduce band_lines/cache_columns"),
            (unsigned)self->display.sram_bytes(),
            (unsigned)spidisplay::allocator().available());
    }
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t SPIDisplay___del__(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    self->display.~SPIDisplay();  // idempotent: releases the SRAM claim and GPIO
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay___del___obj, SPIDisplay___del__);

static mp_obj_t SPIDisplay_command(size_t n_args, const mp_obj_t *args) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[0]);
    if (self->display.released()) {
        mp_raise_ValueError(MP_ERROR_TEXT("this screen's bus has been released by shutdown()"));
    }
    // A staged or streaming frame owns DC, which a command would force low.
    if (self->display.frame_state() != spidisplay::SPIDisplay::FrameState::IDLE) {
        mp_raise_ValueError(MP_ERROR_TEXT("a frame is staged or streaming; update_all() or abort_frame() first"));
    }

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

// update()'s arguments after parsing and validation, shared with prepare().
typedef struct _FrameArgs {
    SPIDisplay_obj_t *self;
    mp_obj_t image;
    mp_buffer_info_t buf;
    int src_w, src_h, src_stride;
    const uint8_t *palette;
    size_t palette_len;
    mp_int_t rotation, mirror, pixel_double;
    bool centred_x, centred_y;
    int off_x, off_y;
    bool tile_x, tile_y;
    uint32_t bg;
    bool v_sync;
    mp_int_t timeout_us;
    mp_int_t sync_delay_us;
    uint64_t target_cs, target_dc;    // 0 for every line this display drives
    uint64_t sync_cs, sync_dc;        // 0 to leave TE alone
} FrameArgs;

// with_sync parses the trailing v_sync, timeout_us and sync_delay_us; prepare()
// leaves them out, since the TE wait belongs to update_all(), and they raise as
// unknown keywords there.
static void SPIDisplay_parse_frame(size_t n_args, const mp_obj_t *pos_args,
                                   mp_map_t *kw_args, bool with_sync, FrameArgs *out) {
    enum { ARG_self, ARG_image,
           ARG_rotation, ARG_mirror, ARG_pixel_double, ARG_offset, ARG_tile,
           ARG_bg, ARG_to, ARG_sync, ARG_v_sync, ARG_timeout_us, ARG_sync_delay_us };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_image, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_rotation, MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_mirror, MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_pixel_double, MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_offset, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_tile, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_bg, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_to, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_sync, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_v_sync, MP_ARG_BOOL, {.u_bool = false} },
        { MP_QSTR_timeout_us, MP_ARG_INT, {.u_int = 50000} },
        { MP_QSTR_sync_delay_us, MP_ARG_INT, {.u_int = 0} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)] = {};
    size_t n_allowed = MP_ARRAY_SIZE(allowed_args) - (with_sync ? 0 : 3);
    mp_arg_parse_all(n_args, pos_args, kw_args, n_allowed, allowed_args, args);

    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[ARG_self].u_obj);
    if (self->display.released()) {
        mp_raise_ValueError(MP_ERROR_TEXT("this screen's bus has been released by shutdown()"));
    }
    if (!self->display.has_sram()) {
        mp_raise_ValueError(MP_ERROR_TEXT("this screen has been deleted and its SRAM released"));
    }

    mp_buffer_info_t buf;
    mp_get_buffer_raise(args[ARG_image].u_obj, &buf, MP_BUFFER_READ);
    int src_w = mp_obj_get_int(mp_load_attr(args[ARG_image].u_obj, MP_QSTR_width));
    int src_h = mp_obj_get_int(mp_load_attr(args[ARG_image].u_obj, MP_QSTR_height));
    int src_stride = mp_obj_get_int(mp_load_attr(args[ARG_image].u_obj, MP_QSTR_stride));

    // An empty or negative extent converts to a background-filled frame, since the
    // covered box comes out empty and no source pixel is read. Report it instead.
    if (src_w < 1 || src_h < 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("image width and height must be positive"));
    }
    // A palettised source is one index byte per pixel, drawn through its colour
    // table; the table's bytes are reachable here by reference and are copied
    // per frame into the display's own SRAM before this call returns.
    mp_obj_t palette_obj = mp_load_attr(args[ARG_image].u_obj, MP_QSTR_palette);
    const uint8_t *palette = NULL;
    size_t palette_len = 0;
    if (palette_obj != mp_const_none) {
        mp_buffer_info_t pbuf;
        mp_get_buffer_raise(palette_obj, &pbuf, MP_BUFFER_READ);
        palette = (const uint8_t *)pbuf.buf;
        palette_len = pbuf.len;
    }
    int px_bytes = palette != NULL ? spidisplay::Indexed8::bytes
                                   : spidisplay::RGBA8888::bytes;

    if (src_stride < src_w * px_bytes) {
        mp_raise_ValueError(MP_ERROR_TEXT("image stride is narrower than its width"));
    }

    // The kernel walks src_h rows of the pitch the image reports, so a buffer
    // shorter than that is read out of bounds and an empty one locks the board.
    // The bound is exactly the extent a strided view reports for itself.
    size_t src_bytes = (size_t)(src_h - 1) * (size_t)src_stride
                     + (size_t)src_w * px_bytes;
    if (buf.len < src_bytes) {
        mp_raise_ValueError(MP_ERROR_TEXT("image buffer is shorter than its dimensions"));
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

    // tile=True repeats the source on both of its own axes, an (x, y) pair on
    // one each: the read wraps at the source's size, so any offset is valid.
    bool tile_x = false;
    bool tile_y = false;
    if (args[ARG_tile].u_obj != mp_const_none) {
        if (mp_obj_is_bool(args[ARG_tile].u_obj)) {
            tile_x = tile_y = mp_obj_is_true(args[ARG_tile].u_obj);
        } else {
            size_t len;
            mp_obj_t *items;
            mp_obj_get_array(args[ARG_tile].u_obj, &len, &items);
            if (len != 2) {
                mp_raise_ValueError(MP_ERROR_TEXT("tile is one value for both axes, or an (x, y) pair"));
            }
            tile_x = mp_obj_is_true(items[0]);
            tile_y = mp_obj_is_true(items[1]);
        }
    }

    // A packed colour carries alpha in the top byte, so it can exceed a signed
    // machine word; truncate to 32 bits (only the low 24 are used).
    uint32_t bg = 0;
    if (args[ARG_bg].u_obj != mp_const_none) {
        bg = (uint32_t)mp_obj_get_int_truncated(args[ARG_bg].u_obj);
    }

    out->self = self;
    out->image = args[ARG_image].u_obj;
    out->buf = buf;
    out->src_w = src_w;
    out->src_h = src_h;
    out->src_stride = src_stride;
    out->palette = palette;
    out->palette_len = palette_len;
    out->rotation = args[ARG_rotation].u_int;
    out->mirror = args[ARG_mirror].u_int;
    out->pixel_double = args[ARG_pixel_double].u_int;
    out->bg = bg;
    out->centred_x = centred_x;
    out->centred_y = centred_y;
    out->off_x = off_x;
    out->off_y = off_y;
    out->tile_x = tile_x;
    out->tile_y = tile_y;
    out->v_sync = with_sync ? args[ARG_v_sync].u_bool : false;
    out->timeout_us = with_sync ? args[ARG_timeout_us].u_int : 0;
    out->sync_delay_us = with_sync ? args[ARG_sync_delay_us].u_int : 0;
    if (out->sync_delay_us < 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("sync_delay_us cannot be negative, since the wait cannot release before the tearing edge"));
    }

    // to= narrows the write to some of a group's members, named as displays so
    // the 64-bit masks never cross into Python. Each must be one of this
    // display's own, which is what stops a subset writing a panel its group does
    // not own, and the masks go no further than the staged frame.
    out->target_cs = 0;
    out->target_dc = 0;
    if (args[ARG_to].u_obj != mp_const_none) {
        size_t n_to;
        mp_obj_t *members;
        mp_obj_get_array(args[ARG_to].u_obj, &n_to, &members);
        if (n_to == 0) {
            mp_raise_ValueError(MP_ERROR_TEXT("to= names no displays, so there is nothing to write"));
        }
        for (size_t i = 0; i < n_to; ++i) {
            if (!mp_obj_is_type(members[i], &SPIDisplay_type)) {
                mp_raise_TypeError(MP_ERROR_TEXT("to= takes SPIDisplay objects"));
            }
            spidisplay::SPIDisplay &member = ((SPIDisplay_obj_t *)MP_OBJ_TO_PTR(members[i]))->display;
            if (member.cs_lines() & ~self->display.cs_lines()) {
                mp_raise_ValueError(MP_ERROR_TEXT("to= names a display this one does not drive, so it is not a member of this group"));
            }
            out->target_cs |= member.cs_lines();
            out->target_dc |= member.dc_lines();
        }
    }

    // sync= names the one member whose TE this frame waits on, and with it asks for
    // the transient TEON and TEOFF around the wait. One display and not a tuple: a
    // shared DC line carries one panel's blanking at a time, which is the whole
    // reason the discipline exists.
    out->sync_cs = 0;
    out->sync_dc = 0;
    if (args[ARG_sync].u_obj != mp_const_none) {
        if (!mp_obj_is_type(args[ARG_sync].u_obj, &SPIDisplay_type)) {
            mp_raise_TypeError(MP_ERROR_TEXT("sync= takes one SPIDisplay"));
        }
        spidisplay::SPIDisplay &member =
            ((SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[ARG_sync].u_obj))->display;
        uint64_t lines = member.cs_lines();
        if (lines & ~self->display.cs_lines()) {
            mp_raise_ValueError(MP_ERROR_TEXT("sync= names a display this one does not drive, so it is not a member of this group"));
        }
        if (lines & (lines - 1)) {
            mp_raise_ValueError(MP_ERROR_TEXT("sync= names one panel to wait on, and this one drives several"));
        }
        out->sync_cs = lines;
        out->sync_dc = member.dc_lines();
    }
}

static mp_obj_t SPIDisplay_update(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    FrameArgs a;
    SPIDisplay_parse_frame(n_args, pos_args, kw_args, true, &a);
    a.self->display.update((const uint8_t *)a.buf.buf, a.src_w, a.src_h, a.src_stride,
        a.palette, a.palette_len,
        a.rotation, a.mirror, a.pixel_double,
        a.centred_x, a.off_x, a.centred_y, a.off_y,
        a.tile_x, a.tile_y, a.bg,
        a.v_sync, a.timeout_us, (uint32_t)a.sync_delay_us,
        a.target_cs, a.target_dc, a.sync_cs, a.sync_dc);
    a.self->staged_image = mp_const_none;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_KW(SPIDisplay_update_obj, 2, SPIDisplay_update);

// fill(colour=black) streams one solid frame, which is update()'s path with no
// source: an empty extent covers no destination pixel, so every one takes the
// background. For putting a panel in a known state at bringup, where no image exists
// yet and the frame is wanted before a canvas is worth claiming.
static mp_obj_t SPIDisplay_fill(size_t n_args, const mp_obj_t *args) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[0]);
    if (self->display.released()) {
        mp_raise_ValueError(MP_ERROR_TEXT("this screen's bus has been released by shutdown()"));
    }
    if (!self->display.has_sram()) {
        mp_raise_ValueError(MP_ERROR_TEXT("this screen has been deleted and its SRAM released"));
    }

    uint32_t bg = 0;
    if (n_args > 1 && args[1] != mp_const_none) {
        bg = (uint32_t)mp_obj_get_int_truncated(args[1]);
    }
    self->display.update(nullptr, 0, 0, 0, nullptr, 0,
                         0, 0, 0,
                         true, 0, true, 0,
                         false, false, bg,
                         false, 0, 0, 0, 0, 0, 0);
    self->staged_image = mp_const_none;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(SPIDisplay_fill_obj, 1, 2, SPIDisplay_fill);

// prepare(image, ...) stages a frame for update_all(): descriptor, cache and
// the first band's conversion, no bus traffic. The image is rooted on the
// display until the stream completes or abort_frame(), since the staged
// descriptor holds a raw pointer into it.
static mp_obj_t SPIDisplay_prepare(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    FrameArgs a;
    SPIDisplay_parse_frame(n_args, pos_args, kw_args, false, &a);
    a.self->display.prepare((const uint8_t *)a.buf.buf, a.src_w, a.src_h, a.src_stride,
        a.palette, a.palette_len,
        a.rotation, a.mirror, a.pixel_double,
        a.centred_x, a.off_x, a.centred_y, a.off_y,
        a.tile_x, a.tile_y, a.bg,
        a.target_cs, a.target_dc, a.sync_cs, a.sync_dc);
    a.self->staged_image = a.image;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_KW(SPIDisplay_prepare_obj, 2, SPIDisplay_prepare);

// Abandon a staged or streaming frame and release the image root. The panel
// keeps its GRAM write pointer, so the next full frame recovers the glass.
static mp_obj_t SPIDisplay_abort_frame(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    self->display.abort_frame();
    self->staged_image = mp_const_none;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_abort_frame_obj, SPIDisplay_abort_frame);

// update_all(*displays, v_sync=False, timeout_us=50000, slice_rows=8,
// hysteresis_rows=-1): stream every prepared display's frame concurrently,
// each starting on its own TE edge. The displays must sit on different buses;
// one bus driving several panels is what broadcast() is for. Kicks are
// interrupt-driven, so slice_rows only bounds the TE poll latency; the
// default keeps one slice's conversion under the TE pulse width so an edge
// cannot slip past, and smaller values just spend more loop overhead.
// hysteresis_rows is the free ring room a display needs to take the convert
// burst from another (interleaver.hpp); negative selects half its ring.
mp_obj_t spidisplay_update_all(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    enum { ARG_v_sync, ARG_timeout_us, ARG_slice_rows, ARG_hysteresis_rows };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_v_sync, MP_ARG_KW_ONLY | MP_ARG_BOOL, {.u_bool = false} },
        { MP_QSTR_timeout_us, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 50000} },
        { MP_QSTR_slice_rows, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 8} },
        { MP_QSTR_hysteresis_rows, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = -1} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(0, NULL, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    if (n_args < 1 || n_args > 4) {
        mp_raise_ValueError(MP_ERROR_TEXT("update_all takes 1 to 4 displays"));
    }
    if (args[ARG_slice_rows].u_int < 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("slice_rows must be positive"));
    }

    SPIDisplay_obj_t *objs[4];
    spidisplay::SPIDisplay *displays[4];
    for (size_t i = 0; i < n_args; ++i) {
        if (!mp_obj_is_type(pos_args[i], &SPIDisplay_type)) {
            mp_raise_TypeError(MP_ERROR_TEXT("update_all takes SPIDisplay objects"));
        }
        SPIDisplay_obj_t *obj = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(pos_args[i]);
        if (obj->display.released()) {
            mp_raise_ValueError(MP_ERROR_TEXT("this screen's bus has been released by shutdown()"));
        }
        if (obj->display.frame_state() != spidisplay::SPIDisplay::FrameState::PREPARED) {
            mp_raise_ValueError(MP_ERROR_TEXT("prepare() every display before update_all()"));
        }
        for (size_t j = 0; j < i; ++j) {
            if (obj == objs[j]) {
                mp_raise_ValueError(MP_ERROR_TEXT("a display is listed twice"));
            }
            if (obj->display.shares_bus_with(objs[j]->display)) {
                mp_raise_ValueError(MP_ERROR_TEXT("displays must be on different buses; broadcast() shares one"));
            }
        }
        objs[i] = obj;
        displays[i] = &obj->display;
    }

    // Will the conversion keep every wire fed? Each display prices its own
    // remaining rows at the rate prepare() measured on them, so this follows the
    // real rotation, source memory and cache rather than a table of constants. The
    // longest wire window is the deadline, every row having to be converted by the
    // time the last stream drains.
    uint32_t debt_us = 0;
    uint32_t window_us = 0;
    for (size_t i = 0; i < n_args; ++i) {
        debt_us += displays[i]->convert_debt_us();
        uint32_t window = displays[i]->wire_window_us();
        if (window > window_us) {
            window_us = window;
        }
    }
    if (window_us > 0 && debt_us > window_us) {
        mp_raise_msg_varg(&mp_type_ValueError,
                          MP_ERROR_TEXT("conversion cannot keep the wires fed: %u us still to convert against a %u us frame, so it would tear. Build the screens with a deeper stage_lines, or halve the source and pass pixel_double"),
                          (unsigned)debt_us, (unsigned)window_us);
    }

    // Everything that can raise has; the interleaver runs without the GC or NLR.
    spidisplay::interleave(displays, (int)n_args, args[ARG_v_sync].u_bool,
                           (uint32_t)args[ARG_timeout_us].u_int,
                           (int)args[ARG_slice_rows].u_int,
                           (int)args[ARG_hysteresis_rows].u_int);

    for (size_t i = 0; i < n_args; ++i) {
        objs[i]->staged_image = mp_const_none;
    }
    return mp_const_none;
}
// Declared extern first: a const object compiled as C++ takes internal linkage
// otherwise, and spidisplay_bindings.c links against this name.
extern const mp_obj_fun_builtin_var_t spidisplay_update_all_obj;
MP_DEFINE_CONST_FUN_OBJ_KW(spidisplay_update_all_obj, 1, spidisplay_update_all);

// te_phase(first, second, period_us, edges=2, timeout_ms=500) -> (skew_us, age_us),
// or None when either TE line yields too few falls in time. The pair's phase
// without writing a frame: skew_us is first's falling edge relative to second's,
// folded to +-period_us/2, and age_us is how old the capture already is at
// return, so a caller can price the drift since. Neither display may hold a
// staged or streaming frame, a staged frame owning the DC lines TE is read from.
mp_obj_t spidisplay_te_phase(size_t n_args, const mp_obj_t *args) {
    if (!mp_obj_is_type(args[0], &SPIDisplay_type) || !mp_obj_is_type(args[1], &SPIDisplay_type)) {
        mp_raise_TypeError(MP_ERROR_TEXT("te_phase takes two SPIDisplay objects"));
    }
    SPIDisplay_obj_t *first = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[0]);
    SPIDisplay_obj_t *second = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[1]);
    if (first == second) {
        mp_raise_ValueError(MP_ERROR_TEXT("te_phase needs two different displays"));
    }
    // Two panels sharing a DC line resolve to one signal, so a capture from both
    // reads the same edges and folds to a meaningless zero. Sweep them one at a
    // time with te_capture() instead, ageing each fall by that panel's own period.
    if (first->display.te_line() == second->display.te_line()) {
        mp_raise_ValueError(MP_ERROR_TEXT("these displays read TE from one line, so there is no phase between them. Sweep them with te_capture(), one panel at TEON at a time"));
    }
    if (first->display.frame_state() != spidisplay::SPIDisplay::FrameState::IDLE
        || second->display.frame_state() != spidisplay::SPIDisplay::FrameState::IDLE) {
        mp_raise_ValueError(MP_ERROR_TEXT("te_phase cannot run with a frame staged, since a staged frame owns the DC lines"));
    }
    mp_int_t period_us = mp_obj_get_int(args[2]);
    if (period_us < 1000) {
        mp_raise_ValueError(MP_ERROR_TEXT("period_us must be at least 1000"));
    }
    mp_int_t edges = n_args > 3 ? mp_obj_get_int(args[3]) : 2;
    if (edges < 2 || edges > 8) {
        mp_raise_ValueError(MP_ERROR_TEXT("edges must be 2..8"));
    }
    mp_int_t timeout_ms = n_args > 4 ? mp_obj_get_int(args[4]) : 500;
    if (timeout_ms < 1 || timeout_ms > 5000) {
        mp_raise_ValueError(MP_ERROR_TEXT("timeout_ms must be 1..5000"));
    }

    spidisplay::TePhase p = spidisplay::SPIDisplay::te_phase(
        first->display, second->display,
        (uint32_t)period_us, (uint32_t)edges, (uint32_t)timeout_ms);
    if (!p.ok) {
        return mp_const_none;
    }
    mp_obj_t items[2] = {
        mp_obj_new_int(p.skew_us),
        mp_obj_new_int_from_uint(p.age_us),
    };
    return mp_obj_new_tuple(2, items);
}
extern const mp_obj_fun_builtin_var_t spidisplay_te_phase_obj;
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(spidisplay_te_phase_obj, 3, 5, spidisplay_te_phase);

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
        MP_QSTR_core1_rows,
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
        mp_obj_new_int_from_uint(s.core1_rows),
    };
    return mp_obj_new_attrtuple(fields, MP_ARRAY_SIZE(fields), items);
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_stats_obj, SPIDisplay_stats);

// Frames whose TE wait timed out. Zero is the only healthy value on a panel wired
// for v_sync.
static mp_obj_t SPIDisplay_te_timeouts(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int_from_uint(self->display.te_timeouts());
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_te_timeouts_obj, SPIDisplay_te_timeouts);

// Frames whose wait ended on a pulse it watched rise and that fell too soon to be a
// blanking, which te_timeouts() reads as healthy. A pulse train books as joined
// instead, its next rise landing inside JOINED_HIGH_US, so te_probe() names TE mode 2.
static mp_obj_t SPIDisplay_te_short_waits(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int_from_uint(self->display.te_short_waits());
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_te_short_waits_obj, SPIDisplay_te_short_waits);

// Frames whose wait began with the line already high, so the pulse it ended on has
// no length to judge. One a frame is a line decaying through the pull-down; the
// occasional one is a frame arming inside a blanking, which is no fault.
static mp_obj_t SPIDisplay_te_joined_waits(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int_from_uint(self->display.te_joined_waits());
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_te_joined_waits_obj, SPIDisplay_te_joined_waits);

// What a full frame costs on this wire, the measured per-band overhead included, so
// a tearing margin can be priced before any frame has gone out. stats().frame_us is
// the same figure once one has.
static mp_obj_t SPIDisplay_wire_window(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int_from_uint(self->display.wire_window_us());
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_wire_window_obj, SPIDisplay_wire_window);

// Destination rows per DMA band, after the clamp the request went through, so the
// band count is height over this. Fixed at construction.
static mp_obj_t SPIDisplay_band_rows(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(self->display.band_rows());
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_band_rows_obj, SPIDisplay_band_rows);

// Bytes of SRAM this display claimed for its band and cache workspace, fixed at
// construction: what buffer_size() dropped by when it was built. A broadcast
// group reports its first member's shared claim.
static mp_obj_t SPIDisplay_sram_bytes(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int_from_uint(self->display.sram_bytes());
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_sram_bytes_obj, SPIDisplay_sram_bytes);

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

// te_capture(edges=4, timeout_ms=250) -> (falls, finished_us), the fall timestamps
// and the instant the capture stopped, both on the ticks_us clock. Fewer falls than
// asked for means the timeout ran out. A shared DC line carries one panel's TE at a
// time, so a hub is swept member by member and each fall aged by its own period to
// bring the set onto one instant; te_probe() discards the timestamps and te_phase()
// needs two lines.
static mp_obj_t SPIDisplay_te_capture(size_t n_args, const mp_obj_t *args) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[0]);
    if (self->display.frame_state() != spidisplay::SPIDisplay::FrameState::IDLE) {
        mp_raise_ValueError(MP_ERROR_TEXT("te_capture cannot run with a frame staged, since a staged frame owns the DC line"));
    }
    mp_int_t edges = n_args > 1 ? mp_obj_get_int(args[1]) : 4;
    mp_int_t timeout_ms = n_args > 2 ? mp_obj_get_int(args[2]) : 250;
    if (edges < 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("te_capture needs at least one edge"));
    }

    spidisplay::TeCapture c = self->display.te_capture((uint32_t)edges, (uint32_t)timeout_ms);
    mp_obj_t falls = mp_obj_new_tuple(0, nullptr);
    if (c.count > 0) {
        mp_obj_t items[spidisplay::TeCapture::MAX_EDGES];
        for (uint32_t i = 0; i < c.count; ++i) {
            items[i] = mp_obj_new_int_from_uint(c.falls[i]);
        }
        falls = mp_obj_new_tuple(c.count, items);
    }
    mp_obj_t out[2] = {falls, mp_obj_new_int_from_uint(c.finished_us)};
    return mp_obj_new_tuple(2, out);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(SPIDisplay_te_capture_obj, 1, 3, SPIDisplay_te_capture);

static const mp_rom_map_elem_t SPIDisplay_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&SPIDisplay___del___obj) },
    { MP_ROM_QSTR(MP_QSTR_command), MP_ROM_PTR(&SPIDisplay_command_obj) },
    { MP_ROM_QSTR(MP_QSTR_update), MP_ROM_PTR(&SPIDisplay_update_obj) },
    { MP_ROM_QSTR(MP_QSTR_fill), MP_ROM_PTR(&SPIDisplay_fill_obj) },
    { MP_ROM_QSTR(MP_QSTR_prepare), MP_ROM_PTR(&SPIDisplay_prepare_obj) },
    { MP_ROM_QSTR(MP_QSTR_abort_frame), MP_ROM_PTR(&SPIDisplay_abort_frame_obj) },
    { MP_ROM_QSTR(MP_QSTR_size), MP_ROM_PTR(&SPIDisplay_size_obj) },
    { MP_ROM_QSTR(MP_QSTR_band_rows), MP_ROM_PTR(&SPIDisplay_band_rows_obj) },
    { MP_ROM_QSTR(MP_QSTR_sram_bytes), MP_ROM_PTR(&SPIDisplay_sram_bytes_obj) },
    { MP_ROM_QSTR(MP_QSTR_baudrate), MP_ROM_PTR(&SPIDisplay_baudrate_obj) },
    { MP_ROM_QSTR(MP_QSTR_stats), MP_ROM_PTR(&SPIDisplay_stats_obj) },
    { MP_ROM_QSTR(MP_QSTR_te_probe), MP_ROM_PTR(&SPIDisplay_te_probe_obj) },
    { MP_ROM_QSTR(MP_QSTR_te_capture), MP_ROM_PTR(&SPIDisplay_te_capture_obj) },
    { MP_ROM_QSTR(MP_QSTR_te_timeouts), MP_ROM_PTR(&SPIDisplay_te_timeouts_obj) },
    { MP_ROM_QSTR(MP_QSTR_te_short_waits), MP_ROM_PTR(&SPIDisplay_te_short_waits_obj) },
    { MP_ROM_QSTR(MP_QSTR_te_joined_waits), MP_ROM_PTR(&SPIDisplay_te_joined_waits_obj) },
    { MP_ROM_QSTR(MP_QSTR_wire_window_us), MP_ROM_PTR(&SPIDisplay_wire_window_obj) },
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
