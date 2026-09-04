// SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
//
// SPDX-License-Identifier: MIT
//
// SPIDisplayBus and SPIDisplay, which own the SPI, DMA and GPIO and the overlapped
// band streaming. Nothing here knows about MicroPython, bar the extern "C" block at
// the end, whose calls reach state private to this file. The types wrapping these
// classes are in spidisplay_bindings.cpp.

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

// Every display claims its band ring and column cache from here at construction, from
// the top so buffer() views keep their bottom-up addresses. The M33 has no SRAM data
// cache, so DMA sees CPU writes without maintenance.
static SRAMAllocator sram;
static bool sram_bound = false;

static SRAMAllocator &allocator() {
    if (!sram_bound) {
        sram.init(__GcHeapStart, __GcHeapEnd);
        sram_bound = true;
    }
    return sram;
}

// Kicks are interrupt-driven on DMA_IRQ_2, which nothing else in this firmware
// touches: rp2.DMA, PWMCluster and I2S(0) share IRQ 0 and I2S(1) has IRQ 1. It is
// taken exclusively and refcounted by bus lifetimes. irq_owner maps a channel to its
// display only while that display streams, so the owner table gates the handler,
// not FrameState. Priority sits above the 0x80 everything else uses, since a
// kick of a few microseconds must not wait behind tens of them of audio.
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

// The packers write every 16-bit pixel big-endian in memory, the order the wire wants.
// A 16-bit DMA word reads little-endian, so the channel swaps the bytes back; an 8-bit
// word carries them in memory order and needs no swap. The pixel format is untouched.
void SPIDisplayBus::configure_dma(int bits) {
    dma_channel_config c = dma_channel_get_default_config(dma_chan);
    channel_config_set_transfer_data_size(&c, bits == 16 ? DMA_SIZE_16 : DMA_SIZE_8);
    channel_config_set_dreq(&c, spi_get_dreq(spi, true));
    channel_config_set_read_increment(&c, true);
    channel_config_set_write_increment(&c, false);
    channel_config_set_bswap(&c, bits == 16);
    dma_channel_configure(dma_chan, &c, &spi_get_hw(spi)->dr, nullptr, 0, false);
    dma_word_bits = bits;
}


SPIDisplay::SPIDisplay(SPIDisplayBus *bus, uint cs, uint dc, int te, uint8_t ram_write,
                       uint8_t te_on, uint8_t te_off, uint8_t te_mode,
                       int bitdepth, int width, int height, uint32_t baudrate,
                       int band_lines, int cache_columns, int stage_lines)
    : bus(bus), cs_mask(1ull << cs), dc_mask(1ull << dc), dc_pin(dc), te_pin(te),
      ram_write_cmd(ram_write), te_on_cmd(te_on), te_off_cmd(te_off),
      te_mode_byte(te_mode),
      fmt(format_for_bitdepth(bitdepth)),
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
    full_row_bytes = packed_row_bytes(fmt, dst_w);
    band_bytes = (rows_per_band * full_row_bytes + 3) & ~(size_t)3;
    cache_capacity = this->cache_columns * dst_w * 4;
    sram_claim_bytes = (size_t)slot_count * band_bytes + (size_t)cache_capacity + PALETTE_BYTES;
    sram_claim = allocator().claim_high(sram_claim_bytes);
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
// display drives. On a shared DC net a second panel at TEON adds its blanking to
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

    // Every DC line in the group is driven low; only the one TE is read from flips
    // to an input below. Low before the release: the data phase leaves it high, and a
    // released line decaying through the pull-down reads as a completed blanking.
    // This is also the level the RAMWR command phase needs, and CS is high here so
    // no panel is listening.
    gpio_set_dir_masked64(dc_mask, dc_mask);
    gpio_put_masked64(dc_mask, 0);
    te_started_us = time_us_32();
    te_timeout_budget_us = timeout_us;
    te_fired = !v_sync;
    te_high_seen = false;
    if (v_sync) {
        uint pin = te_line();
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
    uint pin = te_line();
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
            // length is unknown and only one seen to rise is judged short.
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
    uint pin = te_line();
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
        pins[i] = displays[i]->te_line();
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

    // Each line's falls fold onto one period against a shared reference, the median
    // taken so a missed or doubled edge cannot swing the answer: the upper median, so
    // two falls give the later one and an odd count its middle. The difference goes
    // signed before the reduction, 2**32 not being a multiple of a TE period.
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
                         bool tile_x, bool tile_y,
                         bool tile_mirror_x, bool tile_mirror_y, uint32_t bg,
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

    Transform t = {rotation, mirror != 0};
    desc = make_descriptor(src, src_w, src_h, dst_w, dst_h, fmt, t, dbl,
                           centred_x, off_x, centred_y, off_y,
                           tile_x, tile_y, tile_mirror_x, tile_mirror_y, bg,
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

    // Wider SPI words, frames in the PL022's datasheet, cut its idle time between them,
    // 1.5 clocks whatever the width. A transfer has to be a whole number of words, so an odd
    // packed row width, RGB444 at half the possible widths, falls back to 8-bit words.
    wide_words = (desc.dst_row_bytes % 2) == 0;
    word_shift = wide_words ? 1 : 0;
    bus->use_word_bits(wide_words ? 16 : 8);

    // Check if the source address sits anywhere inside the 16MB hardware window for CS1
    uintptr_t src_addr = (uintptr_t)desc.src;
    bool src_in_psram = (src_addr >= PSRAM_CACHED_BASE && src_addr < PSRAM_CACHED_BASE + PSRAM_WINDOW);

    // Whether the cache applies is settled here, and it stays live across bands so a
    // window seeded by one serves the next
    cache = ColumnCache((uint32_t *)(sram_claim + (size_t)slot_count * band_bytes),
                        cache_capacity, cache_columns);
    cache.begin(desc, convert, src_in_psram);

    last.pre_us = time_us_32() - t_pre;
    last.convert_total_us = 0;
    last.stall_us = 0;
    last.core1_rows = 0;
    last.stall_row = -1;

    rows_converted = 0;
    rows_kicked = 0;
    bands_kicked = 0;
    stall_pending = false;
    stall_started_row = -1;
    state = FrameState::PREPARED;

    // The first band, then the whole ring: a staged display carries its head start
    // out of prepare(), since a TE edge landing right after arm() would otherwise
    // start the stream with only what the wait happened to convert. The ring room
    // rule holds this to band 0 when stage_lines is 0.
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
    if (wide_words) {
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
    dma_channel_set_trans_count(bus->dma_chan, full_band_bytes >> word_shift, true);  // true starts it
}

// The interrupt-side kick; try_kick() is the same dispatch from the thread, for a
// band that finished converting after the completion came and went. In RAM for the
// same QMI-contention reason as the handler. Busy means the completion this entry
// answers was already serviced by a masked thread kick, so touching the registers
// would corrupt the band in flight.
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
        // The wire is starving; the thread's next kick closes the clock and books
        // the row it waited for.
        if (!stall_pending) {
            stall_pending = true;
            stall_started_us = time_us_32();
            stall_started_row = rows_kicked;
        }
        return;
    }

    int band = bands_kicked;
    rows_kicked = rows_kicked + next;
    bands_kicked = band + 1;
    dma_channel_set_read_addr(bus->dma_chan, slot_ptr(band), false);
    size_t bytes = next == rows_per_band ? full_band_bytes
                                         : (size_t)next * desc.dst_row_bytes;
    dma_channel_set_trans_count(bus->dma_chan, bytes >> word_shift, true);
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

// The thread-side kick, the fallback for a band that finishes converting while
// the channel already sits idle; completions themselves kick from kick_from_isr()
// above, the same dispatch. The check-ack-kick runs under PRIMASK so the handler
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
        if (last.stall_row < 0) {
            last.stall_row = stall_started_row;    // the frame's first starvation
        }
        stall_pending = false;
    }

    int band = bands_kicked;
    rows_kicked = rows_kicked + next;
    bands_kicked = band + 1;
    dma_channel_set_read_addr(bus->dma_chan, slot_ptr(band), false);
    size_t bytes = next == rows_per_band ? full_band_bytes
                                         : (size_t)next * desc.dst_row_bytes;
    dma_channel_set_trans_count(bus->dma_chan, bytes >> word_shift, true);
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
            stall_started_row = -1;     // a drain, not a starvation
        }
        return false;
    }

    gpio_set_mask64(write_cs());
    uint32_t t_end = time_us_32();
    if (stall_pending) {
        last.stall_us += t_end - stall_started_us;
        if (last.stall_row < 0) {
            last.stall_row = stall_started_row;
        }
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

    if (wide_words) {
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
    uint32_t word_bits = 8u << word_shift;
    return (uint32_t)(((uint64_t)remaining * word_bits * 1000000u) / achieved_baudrate);
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
    // Plus the per-band overhead, measured the same on both panel sizes. A 320-row
    // frame streams in 42,016us against 38,400 of pure bits.
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
        if (wide_words) {
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
                        bool tile_x, bool tile_y,
                        bool tile_mirror_x, bool tile_mirror_y, uint32_t bg,
                        bool v_sync, uint32_t timeout_us, uint32_t sync_delay_us,
                        uint64_t target_cs, uint64_t target_dc,
                        uint64_t sync_cs, uint64_t sync_dc) {
    prepare(src, src_w, src_h, src_stride, palette, palette_len,
            rotation, mirror, pixel_double,
            centred_x, off_x, centred_y, off_y,
            tile_x, tile_y, tile_mirror_x, tile_mirror_y, bg,
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

// Whether a conversion is halved across both cores, for the module's dual_convert().
// A build without the core1 worker always reports off, so reading it back also
// reports whether this firmware has a second core to convert on.
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

}  // extern "C"
