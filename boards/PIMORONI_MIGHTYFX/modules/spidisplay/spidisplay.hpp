// SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
//
// SPDX-License-Identifier: MIT
//
// A general purpose DMA-backed SPI display driver, focused on the transmission of
// data to a panel only, with register configuration left to the caller.
//
// One SPIDisplayBus per SPI port owns the peripheral, its DMA channel and its rate.
// Each SPIDisplay on that bus streams a converted frame band by band, driving its own
// CS and DC masks, so a broadcast group is one display carrying every member's bits.

#pragma once

#include <cstddef>
#include <cstdint>

#include "hardware/dma.h"
#include "hardware/spi.h"

#include "column_cache.hpp"
#include "descriptor.hpp"

namespace spidisplay {

// A panel's tearing-effect signal as observed, a short high_us being its blanking
struct TeProbe {
    uint32_t period_us;
    uint32_t high_us;
    uint32_t edges;
};

// The first panel's TE fall relative to the second's, folded to +-period/2
struct TePhase {
    bool ok;            // False when either line yielded too few falls in time
    int32_t skew_us;
    uint32_t age_us;
};

// Falling-edge timestamps from one panel's TE line and the instant the capture stopped
struct TeCapture {
    static constexpr uint32_t MAX_EDGES = 8;
    uint32_t falls[MAX_EDGES];
    uint32_t count;
    uint32_t finished_us;
};

// One update()'s instrumentation, microseconds except core1_rows and stall_row. The
// convert figures are wall time, half of a row range going to core1.
struct FrameStats {
    uint32_t pre_us;             // Descriptor setup
    uint32_t convert_us;         // The first band alone
    uint32_t te_wait_us;
    uint32_t frame_us;           // DC low before RAMWR to CS high after the stream
    uint32_t convert_total_us;   // Every band
    uint32_t stall_us;           // Wire idle, from a completion that found no band
                                 // ready to the recovering kick, plus the final drain
    uint32_t write_start_us;     // time_us_32() at the RAMWR that opened the frame
    uint32_t core1_rows;         // Rows of this frame core1 converted, 0 when the
                                 // split was off, the source was not SRAM, or no
                                 // range held two rows
    int32_t stall_row;           // The row the wire first waited for, always a band
                                 // boundary, and -1 when it never starved, the final
                                 // drain not counting
};

class SPIDisplay;

class SPIDisplayBus {
    friend class SPIDisplay;

    //--------------------------------------------------
    // Variables
    //--------------------------------------------------
private:
    spi_inst_t *spi;
    uint sck_pin;                 // Held so the destructor can hand them back as GPIO
    uint mosi_pin;
    int dma_chan;
    int dma_word_bits;            // Width the DMA channel is currently configured for
    uint32_t requested_baudrate;  // What a display last asked for, for the compare
    uint32_t achieved_baudrate;   // What the divider reached for that request

    //--------------------------------------------------
    // Constructors/Destructor
    //--------------------------------------------------
public:
    SPIDisplayBus(uint spi_index, uint sck, uint mosi, uint baudrate);
    ~SPIDisplayBus();

    //--------------------------------------------------
    // Methods
    //--------------------------------------------------
private:
    // Re-rate the bus, returning the rate the divider reached. Takes effect on the
    // next transfer, so never while a frame streams.
    uint32_t set_baudrate(uint32_t value);

    // The DMA word width, 8 or 16 bits. A 16-bit word has its bytes swapped
    void configure_dma(int bits);
    void use_word_bits(int bits) {
        if (dma_word_bits != bits) {
            configure_dma(bits);
        }
    }
};

class SPIDisplay {
    //--------------------------------------------------
    // Enums
    //--------------------------------------------------
public:
    // The states a frame passes through under update()'s steps. PREPARED and ARMED are
    // called staged, converted ahead and owning their lines but not yet on the wire.
    enum class FrameState : uint8_t { IDLE, PREPARED, ARMED, STREAMING };

    //--------------------------------------------------
    // Constants
    //--------------------------------------------------
private:
    // A pulse shorter than this was not a blanking
    static constexpr uint32_t SHORT_WAIT_US = 700;

    // A high found this soon after the wait began had already started, length unknown
    static constexpr uint32_t JOINED_HIGH_US = 50;

    //--------------------------------------------------
    // Variables
    //--------------------------------------------------
private:
    SPIDisplayBus *bus;
    uint64_t cs_mask;   // Every CS this display drives, so a group drives them together
    uint64_t dc_mask;   // Likewise DC, since a group's members may each have their own
    uint dc_pin;        // The single DC line TE is read from, when te_pin < 0
    int te_pin;
    uint8_t ram_write_cmd;
    uint8_t te_on_cmd;
    uint8_t te_off_cmd;
    uint8_t te_mode_byte;
    int fmt;            // Destination packer tag (RGB444::format / RGB565::format)
    int dst_w;          // The panel's own dimensions, fixed for its lifetime
    int dst_h;
    int rows_per_band;  // Destination rows per DMA band, clamped at construction
    int cache_columns;  // Column cache width, clamped to the panel at construction

    // Band ring, cache storage, then an indexed source's palette, in one claim
    uint8_t *sram_claim = nullptr;
    size_t sram_claim_bytes = 0;
    size_t band_bytes = 0;          // One band buffer, rounded up to 4
    size_t full_row_bytes = 0;      // A whole panel row packed, which prices a frame
                                    // before one is staged
    int cache_capacity = 0;         // Cache storage in bytes
    bool owns_sram_claim = false;   // False on a copy, which shares the member's claim
    uint32_t requested_baudrate;    // What this display asks the bus for
    uint32_t achieved_baudrate;     // What the divider gave it
    FrameStats last = {};
    uint32_t te_timeout_count = 0;
    uint32_t te_short_wait_count = 0;
    uint32_t te_joined_wait_count = 0;
    int slot_count = 2;         // Band ring depth including the reserved in-flight slot

    // The staged frame
    FrameState state = FrameState::IDLE;
    Descriptor desc = {};

    // The lines this write drives, 0 meaning all. Set by prepare(), cleared at IDLE
    uint64_t target_cs_mask = 0;
    uint64_t target_dc_mask = 0;

    // The one member this frame waits on, cleared with the target masks
    uint64_t sync_cs_mask = 0;
    uint64_t sync_dc_mask = 0;

    ColumnCache cache{nullptr, 0, 0};
    size_t full_band_bytes = 0;         // A full band's packed bytes, set per frame
    bool wide_words = false;            // 16-bit DMA words, for an even packed row
    int word_shift = 0;                 // Bytes to words, 1 for wide and 0 for 8-bit

    // Shared with the DMA_IRQ_2 handler, which is why they are volatile. The handler
    // books a stall that the thread later closes.
    volatile int rows_converted = 0;            // Rows converted, published last
    volatile int rows_kicked = 0;               // Rows handed to the DMA channel
    volatile int bands_kicked = 0;              // Kicks so far, naming the next slot
    volatile bool stall_pending = false;        // Wire starving or draining
    volatile uint32_t stall_started_us = 0;     // When the starvation was seen
    volatile int32_t stall_started_row = -1;    // The row it waited for, -1 for a drain

    // The TE wait's own state, from arm() until the edge fires or the timeout runs out
    uint32_t frame_started_us = 0;
    bool te_fired = false;
    bool te_high_seen = false;
    bool te_raw_prev = false;           // Last raw TE sample, for the settling test
    uint32_t te_started_us = 0;
    uint32_t te_high_started_us = 0;    // When the pulse the wait ends on began
    uint32_t te_timeout_budget_us = 0;  // This wait's timeout, from arm()

    //--------------------------------------------------
    // Constructors/Destructor
    //--------------------------------------------------
public:
    // Construct a display on a bus, from its pins, the panel's register opcodes and its
    // geometry. The band ring and cache are claimed from SRAM here, which has_sram()
    // reports on. te < 0 reads the tearing-effect signal from the dc line rather than
    // its own input. band_lines is rows per DMA band, stage_lines the ring depth in
    // rows and cache_columns the column cache width, 0 to disable.
    SPIDisplay(SPIDisplayBus *bus, uint cs, uint dc, int te, uint8_t ram_write,
               uint8_t te_on, uint8_t te_off, uint8_t te_mode,
               int bitdepth, int width, int height, uint32_t baudrate,
               int band_lines, int cache_columns, int stage_lines);

    // Construct a copy of an existing display as a broadcast group, claiming nothing
    SPIDisplay(const SPIDisplay &member) {
        *this = member;
        owns_sram_claim = false;
        state = FrameState::IDLE;  // A group never inherits a member's staged frame
        target_cs_mask = 0;        // nor the lines that frame was narrowed to write
        target_dc_mask = 0;
        sync_cs_mask = 0;          // nor the member that frame waited on
        sync_dc_mask = 0;
    }

    ~SPIDisplay();

    //--------------------------------------------------
    // Methods
    //--------------------------------------------------
public:
    // Check if this and another display agree on the bus and all the stream depends on
    bool compatible_with(const SPIDisplay &other) const;

    // Check if this and another display share a bus, which only broadcast() allows
    bool shares_bus_with(const SPIDisplay &other) const { return bus == other.bus; }

    // Add another display's CS and DC bits to this group's masks, after compatible_with()
    void add(const SPIDisplay &other);

    int width() const { return dst_w; }
    int height() const { return dst_h; }

    // Destination rows per DMA band, after the clamp
    int band_rows() const { return rows_per_band; }

    // Sample the TE line for ms milliseconds, zeroed if it never toggles. Not mid-stream.
    TeProbe te_probe(uint32_t ms);

    // Capture falling edges on this display's TE line, with no frame staged or
    // streaming. A shared DC line carries one panel's TE at a time, so sweep a hub
    // member by member and age each fall by that panel's own period onto one instant.
    TeCapture te_capture(uint32_t edges, uint32_t timeout_ms);

    // The pin TE is read from, its own line where it has one and the DC line otherwise
    uint te_line() const { return te_pin >= 0 ? (uint)te_pin : dc_pin; }

    // Measure a pair's skew without a frame, both TE lines read in one loop and
    // neither holding one. skew_us is first's fall relative to second's, and age_us how
    // old the capture is at return, so a caller can price the drift since. Two panels
    // on one DC line resolve to one signal, so sweep those with te_capture() instead.
    static TePhase te_phase(SPIDisplay &first, SPIDisplay &second,
                            uint32_t period_us, uint32_t edges, uint32_t timeout_ms);

    // Perform a blocking register write. Command on DC low, data on DC high
    void command(const uint8_t *cmd, size_t cmd_len,
                 const uint8_t *data, size_t data_len);

    // Convert and stream a whole frame, blocking until it has left. src is RGBA8888, or
    // one palette index per pixel with palette set, whose table is composited over the
    // background into the display's own SRAM before this returns.
    //
    // Each axis is centred or placed by its offset, and tiling wraps the read at the
    // source's size, so any offset is valid. mirror flips the whole output, while
    // tile_mirror_x and tile_mirror_y reflect every other repeat of their own axis.
    //
    // v_sync holds the frame until the panel's tearing edge, timeout_us bounding that
    // wait and sync_delay_us delaying the start. The masks are as prepare() describes.
    void update(const uint8_t *src, int src_w, int src_h, int src_stride,
                const uint8_t *palette, size_t palette_len,
                int rotation, int mirror, int pixel_double,
                bool centred_x, int off_x, bool centred_y, int off_y,
                bool tile_x, bool tile_y,
                bool tile_mirror_x, bool tile_mirror_y, uint32_t bg,
                bool v_sync, uint32_t timeout_us, uint32_t sync_delay_us = 0,
                uint64_t target_cs = 0, uint64_t target_dc = 0,
                uint64_t sync_cs = 0, uint64_t sync_dc = 0);

    FrameState frame_state() const { return state; }

    // Stage a frame, building the descriptor, seeding the cache and filling the ring's
    // head start, but sending nothing. target_cs and target_dc narrow the write to some
    // of a group's members. sync_cs and sync_dc name the member whose TE the frame
    // waits on, which is sent TEON and TEOFF.
    void prepare(const uint8_t *src, int src_w, int src_h, int src_stride,
                 const uint8_t *palette, size_t palette_len,
                 int rotation, int mirror, int pixel_double,
                 bool centred_x, int off_x, bool centred_y, int off_y,
                 bool tile_x, bool tile_y,
                 bool tile_mirror_x, bool tile_mirror_y, uint32_t bg,
                 uint64_t target_cs = 0, uint64_t target_dc = 0,
                 uint64_t sync_cs = 0, uint64_t sync_dc = 0);

    // Begin the TE wait without blocking, which without v_sync has already fired
    void arm(bool v_sync, uint32_t timeout_us);

    // Sample the TE wait once, true when the frame may start, by edge or by timeout
    bool poll_te();

    // Start the stream with RAMWR and the first band's DMA kick, timestamped for skew
    void start_stream();

    // Convert at most max_rows, kick a full band and raise CS once drained, true when
    // anything advanced. A max_rows of 0 services the wire and converts nothing.
    bool step(int max_rows);

    // Whether a convert slice would find room
    bool wants_convert() const {
        if (state != FrameState::ARMED && state != FrameState::STREAMING) {
            return false;
        }
        return convert_room() > 0;
    }

    // Converted rows the wire has not yet been handed
    int staged_rows() const { return rows_converted - rows_kicked; }

    // Rows the ring holds ahead of the wire when full, less the reserved slot
    int stage_capacity_rows() const { return (slot_count - 1) * rows_per_band; }

    // Ring rows a slice could fill now, a concurrent kick only understating it. The
    // ring rule, shared with convert_room(), is that converted rows lead kicked rows
    // by at most slot_count - 1 bands, the last slot being the transfer in flight.
    int stage_free_rows() const {
        int kicked = bands_kicked;
        int free_rows = (kicked + slot_count - 1) * rows_per_band - rows_converted;
        int remaining = dst_h - rows_converted;
        if (free_rows > remaining) {
            free_rows = remaining;
        }
        return free_rows < 0 ? 0 : free_rows;
    }

    // Every row converted, which wants_convert() cannot tell from a full ring
    bool convert_done() const { return rows_converted >= dst_h; }

    // Conversion still owed for the staged frame, 0 with none staged
    uint32_t convert_debt_us() const;

    // Wall time the staged frame's rows take on the wire, per-band overhead included,
    // which stats().frame_us reports once a frame has gone out
    uint32_t wire_window_us() const;

    bool busy() const { return dma_channel_is_busy(bus->dma_chan); }
    bool done() const { return state == FrameState::IDLE; }

    // Microseconds until the in-flight transfer drains, 0 when the channel is free
    uint32_t deadline_us() const;

    // Abandon a staged or streaming frame, the next full frame recovering the glass
    void abort_frame();

    // Kick the next band from the DMA_IRQ_2 handler, allocating nothing and touching no
    // state a thread owns. try_kick() is the same dispatch from the thread instead.
    void kick_from_isr();

    // Wait when the interleaver made no progress, for a caller driving a simulated clock
    void idle_wait() const {}

    // Whether the bus has given its DMA channel back, refusing command() and update()
    bool released() const { return bus->dma_chan < 0; }

    // Whether the SRAM claim is still held, update() being refused once it is gone
    bool has_sram() const { return sram_claim != nullptr; }

    // Bytes claimed for the band and cache workspace, a group reporting its first's
    size_t sram_bytes() const { return sram_claim_bytes; }

    // Instrumentation from the most recent update()
    FrameStats stats() const { return last; }

    // Frames that began without their TE edge, cumulative, the only sign v_sync slipped
    uint32_t te_timeouts() const { return te_timeout_count; }

    // Frames whose wait ended on a pulse shorter than SHORT_WAIT_US, cumulative. A
    // pulse train books as joined instead, so te_probe() names TE mode 2.
    uint32_t te_short_waits() const { return te_short_wait_count; }

    // Frames whose wait began with the line already high, cumulative. One a frame is
    // the pull-down decaying, an occasional one a frame arming inside a blanking.
    uint32_t te_joined_waits() const { return te_joined_wait_count; }

    // What this panel's rate reached, the divider rounding a request down
    uint32_t baudrate() const { return achieved_baudrate; }

    // The lines this display drives, for a mask over some of a group's members
    uint64_t cs_lines() const { return cs_mask; }
    uint64_t dc_lines() const { return dc_mask; }

private:
    // The ring slot a band index streams from
    uint8_t *slot_ptr(int band_index) const {
        return sram_claim + (size_t)(band_index % slot_count) * band_bytes;
    }

    // Rows convertible into the current band now, under the ring rule at
    // stage_free_rows(). The write band may lead the kicked count by slot_count - 2,
    // the reserved slot being the transfer in flight whether the channel is busy or not.
    int convert_room() const {
        if (rows_converted >= dst_h) {
            return 0;
        }
        int write_band = rows_converted / rows_per_band;
        if (write_band - bands_kicked > slot_count - 2) {
            return 0;
        }
        int band_start = write_band * rows_per_band;
        int band_size = dst_h - band_start < rows_per_band ? dst_h - band_start
                                                           : rows_per_band;
        return band_size - (rows_converted - band_start);
    }

    void te_fire(uint32_t now);
    bool step_convert(int max_rows);

    // Kick from the thread, the fallback for a band that finishes converting while the
    // channel already sits idle, a completion kicking from kick_from_isr() instead
    bool try_kick();
    bool finish_if_drained();

    SPIDisplay &operator=(const SPIDisplay &) = default;

    // Re-rate the bus only when this display's request differs from the last
    void use_baudrate() {
        if (bus->requested_baudrate != requested_baudrate) {
            achieved_baudrate = bus->set_baudrate(requested_baudrate);
        }
    }

    // The lines a write drives, its target masks where it has them
    uint64_t write_cs() const { return target_cs_mask ? target_cs_mask : cs_mask; }
    uint64_t write_dc() const { return target_dc_mask ? target_dc_mask : dc_mask; }

    // Send a TE opcode to the one member the sync masks name, not every line this
    // display drives, since a second panel at TEON would add its own blanking
    void te_command(uint8_t opcode, const uint8_t *data, size_t data_len);
};

}  // namespace spidisplay
