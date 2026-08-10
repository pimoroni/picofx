// SPDX-License-Identifier: MIT
//
// A panel-agnostic SPI + DMA transport for the MightyFX display pipeline. One
// SPIDisplayBus per SPI port owns the peripheral, DMA channel and rate; any number
// of SPIDisplays on it own a panel each and stream a converted frame band-by-band,
// so conversion overlaps the in-flight DMA. Bringup stays in MicroPython.
//
// A display holds CS and DC masks rather than pins, so one write drives several
// panels and a broadcast group is a display carrying every member's bits.
//
// command() and update() both block and return with CS high and the shifter
// drained, so a multiplexer's select line can be set immediately before either.
// Each display claims its own band and column cache SRAM at construction, so
// ports share no buffers; update() still blocks, so a single-threaded caller
// streams one frame at a time and no synchronisation is needed.

#pragma once

#include <cstddef>
#include <cstdint>

#include "hardware/dma.h"
#include "hardware/spi.h"

#include "column_cache.hpp"
#include "scanline.hpp"

namespace spidisplay {

// Observed shape of a panel's tearing-effect signal. A short high_us against the
// period means the asserted level is vertical blanking, so the falling edge
// starts visible row 0. edges is the rising edges counted.
struct TeProbe {
    uint32_t period_us;
    uint32_t high_us;
    uint32_t edges;
};

// The signed phase between two panels' TE falls, captured from both lines in one
// loop so the edge sets share a clock. skew_us is the first panel's fall relative
// to the second's, folded to +-period/2. age_us is how long before the capture
// returned that its newest fall was seen, so a caller can price the drift since.
struct TePhase {
    bool ok;            // False when either line yielded too few falls in time
    int32_t skew_us;
    uint32_t age_us;
};

// Falling-edge timestamps from one panel's TE line, with the instant the capture
// stopped, all on time_us_32(). Where te_phase() reduces two lines to a phase in
// one loop, this keeps the raw edges of one, which is what a shared DC line needs:
// only one panel may assert at a time, so a hub is swept member by member and each
// fall is aged by that panel's own period to bring them onto a common instant.
struct TeCapture {
    static constexpr uint32_t MAX_EDGES = 8;
    uint32_t falls[MAX_EDGES];
    uint32_t count;
    uint32_t finished_us;
};

// One update()'s worth of instrumentation, microseconds but for the last field.
// Kicks are interrupt-driven, so stall_us measures the wire genuinely starving
// for conversion: near zero means the frame was wire-bound, growth means the
// conversion could not keep the ring fed. write_start_us is absolute, so the
// gap between two displays is their skew.
//
// The convert figures are wall time, which is what the wire competes against,
// and not CPU time: half of a row range goes to core1 (scanline.hpp).
struct FrameStats {
    uint32_t pre_us;             // Descriptor setup
    uint32_t convert_us;         // The first band alone
    uint32_t te_wait_us;
    uint32_t frame_us;           // DC low before RAMWR to CS high after the stream
    uint32_t convert_total_us;   // Every band
    uint32_t stall_us;           // Wire idle: completions that found no band ready,
                                 // to the recovering kick, plus the final drain
    uint32_t write_start_us;     // time_us_32() at the RAMWR that opened the frame
    uint32_t core1_rows;         // Rows of this frame core1 converted, 0 when the
                                 // split was off or every range was too short
};

class SPIDisplay;

class SPIDisplayBus {
public:
    SPIDisplayBus(uint spi_index, uint sck, uint mosi, uint baudrate);
    ~SPIDisplayBus();

private:
    friend class SPIDisplay;

    // Re-rate the bus, returning the rate the divider reached, and record the
    // request so the next display to transfer notices the bus moved. Takes effect
    // on the next transfer. Must not be called while a frame is streaming.
    uint32_t set_baudrate(uint32_t value);

    // Point the DMA channel at the SPI data register for the given frame width.
    // 16-bit frames go out most significant byte first, so the channel byte
    // swaps to keep the packed order on the wire.
    void configure_dma(int bits);
    void use_frame_bits(int bits) {
        if (dma_frame_bits != bits) {
            configure_dma(bits);
        }
    }

    spi_inst_t *spi;
    uint sck_pin;                 // Held so the destructor can hand them back as GPIO
    uint mosi_pin;
    int dma_chan;
    int dma_frame_bits;           // Width the DMA channel is currently configured for
    uint32_t requested_baudrate;  // What a display last asked for, for the compare
    uint32_t achieved_baudrate;   // What the divider reached for that request
};

class SPIDisplay {
public:
    // te < 0 reads the tearing-effect signal from the dc line (MightyFX), otherwise
    // it is a dedicated input GPIO. bitdepth is 12 (RGB444) or 16 (RGB565).
    // baudrate is this panel's own, asserted against the bus before every transfer,
    // so mixed panel types can share a port. band_lines is destination rows per DMA
    // band, clamped to [1, height]. cache_columns is source columns per column
    // cache window (see column_cache.hpp), clamped to [0, width], 0 to disable.
    //
    // stage_lines is the staging depth: the band buffers form a ring of
    // ceil(stage_lines / band_lines) slots, at least two, and conversion may run
    // the whole ring ahead of the wire, which is what lets a slow source convert
    // ahead during the TE wait and hold a head start against the wire's pace.
    //
    // Construction claims that many band slots plus cache_columns * width * 4
    // bytes of SRAM for the workspace; when the claim fails, has_sram() is false
    // and the wrapper raises rather than configuring GPIO.
    //
    // Wiring: cs must be unique per panel, being the only signal selecting one. dc
    // may be shared, but not by panels using TE: each breakout ties TE to that line
    // through a series resistor, so panels sharing it divide the line and the
    // asserted level is lost. Behind a multiplexer a dc line carrying TE needs an
    // analog mux to pass both directions; a demux or buffer fails quietly, the wait
    // timing out, te_timeouts() counting it, while the frame still streams.
    //
    // te_on and te_off are the controller's TEON and TEOFF opcodes, passed in for
    // the same reason ram_write is: the frame path emits them while the controller
    // module stays the authority on the values. te_mode is TEON's parameter byte,
    // sent explicitly since TEON without one leaves the mode bit as it was.
    SPIDisplay(SPIDisplayBus *bus, uint cs, uint dc, int te, uint8_t ram_write,
               uint8_t te_on, uint8_t te_off, uint8_t te_mode,
               int bitdepth, int width, int height, uint32_t baudrate,
               int band_lines, int cache_columns, int stage_lines);

    // A broadcast group starts as a copy of one member and add()s the rest. The
    // copy claims no GPIO, since the members own theirs, and is a snapshot: a
    // member that later re-rates itself moves only itself. It shares the member's
    // SRAM claim rather than taking its own; only the member releases it, so the
    // wrapper roots the member for the group's lifetime.
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

    // Whether another display can share a frame with this one: the same bus, and
    // agreement on everything the stream depends on. Register state bringup put in
    // the panel is not compared, MADCTL included, which is not licence to vary it:
    // the scan direction does not follow MADCTL, so a flipped panel tears.
    bool compatible_with(const SPIDisplay &other) const;

    // Interleaved displays need a bus each; a shared one is broadcast territory.
    bool shares_bus_with(const SPIDisplay &other) const { return bus == other.bus; }

    // Fold another member's CS and DC bits into this group's masks. Only
    // meaningful on a copy; check compatible_with() first.
    void add(const SPIDisplay &other);

    int width() const { return dst_w; }
    int height() const { return dst_h; }

    // Destination rows per DMA band, after the clamp the requested band_lines went
    // through. Fixed for the panel, so the band count is height() over this.
    int band_rows() const { return rows_per_band; }

    // Sample the TE line for ms milliseconds, zeroed if it never toggles, so a
    // panel that was never sent TEON reports rather than hanging. Must not be
    // called while a frame is streaming.
    TeProbe te_probe(uint32_t ms);

    // Falling edges on this display's TE line, up to TeCapture::MAX_EDGES of them,
    // with the instant the capture stopped. Must not be called while a frame is
    // staged or streaming, a staged frame owning the DC line TE is read from.
    TeCapture te_capture(uint32_t edges, uint32_t timeout_ms);

    // The GPIO this display's TE is read from: its own line where it has one, and
    // the DC line otherwise. Two displays resolving to the same one cannot be
    // phase-compared, there being one signal between them.
    uint te_line() const { return te_pin >= 0 ? (uint)te_pin : dc_pin; }

    // Capture edges falling edges on both displays' TE lines from one loop and
    // fold them onto period_us, so a pair's skew can be measured without writing
    // a frame. Copes with the ~47us TESCAN-narrowed pulse, which a Python
    // capture cannot. Neither display may hold a staged or streaming frame, a
    // staged frame owning the DC lines TE is read from.
    static TePhase te_phase(SPIDisplay &first, SPIDisplay &second,
                            uint32_t period_us, uint32_t edges, uint32_t timeout_ms);

    // Blocking raw register write: DC low, CS low, command, DC high, data,
    // CS high. Used for panel bringup from MicroPython.
    void command(const uint8_t *cmd, size_t cmd_len,
                 const uint8_t *data, size_t data_len);

    // Convert and stream a whole frame. src is RGBA8888, or one palette index
    // per pixel when palette is set; src_stride is its pitch in bytes (0 means
    // contiguous). palette is up to palette_len bytes of RGBA words, copied out
    // before this returns, each composited over bg by its own alpha; an RGBA
    // pixel's alpha is ignored. bg is also what the pixels the source does not
    // cover take. Each axis is centred, or placed by its off_x/off_y top-left.
    // Blocks until the frame has left over SPI.
    // sync_delay_us starts the stream that long after the TE wait releases, which
    // places a broadcast write inside every member's tearing margin instead of at
    // the synced member's own top edge. write_start_us moves with it.
    void update(const uint8_t *src, int src_w, int src_h, int src_stride,
                const uint8_t *palette, size_t palette_len,
                int rotation, int mirror, int pixel_double,
                uint32_t bg, bool centred_x, int off_x, bool centred_y, int off_y,
                bool v_sync, uint32_t timeout_us, uint32_t sync_delay_us = 0,
                uint64_t target_cs = 0, uint64_t target_dc = 0,
                uint64_t sync_cs = 0, uint64_t sync_dc = 0);

    // The resumable steps update() composes, exposed so an interleaver can drive
    // several displays through a frame concurrently: prepare(), arm(), poll_te()
    // until it fires, start_stream(), then step() until done(). Displays being
    // interleaved must sit on different buses; each call touches only its own.
    enum class FrameState : uint8_t { IDLE, PREPARED, ARMED, STREAMING };
    FrameState frame_state() const { return state; }

    // Descriptor, cache seeding, and conversion of the first band plus the
    // rest of the staged ring, so a staged display carries its head start out
    // of here whatever the TE phase does. Sets the bus rate and DMA frame
    // width, sends nothing, never waits on the bus.
    // target_cs and target_dc narrow the write to a subset of a group's members, 0
    // meaning every line this display drives. sync_cs and sync_dc name the one
    // member whose TE this frame waits on, which a shared DC line allows only one
    // of at a time. All four are arguments and not settings: the frame carries them
    // and going IDLE clears them, so no stale mask survives to write or to sync on
    // the wrong panel.
    //
    // A non-zero sync_cs also asks for the transient TE discipline: TEON to that
    // member as the wait begins, TEOFF as the frame goes idle. Zero leaves TE
    // alone, which is what a panel owning its own DC line wants.
    void prepare(const uint8_t *src, int src_w, int src_h, int src_stride,
                 const uint8_t *palette, size_t palette_len,
                 int rotation, int mirror, int pixel_double,
                 uint32_t bg, bool centred_x, int off_x, bool centred_y, int off_y,
                 uint64_t target_cs = 0, uint64_t target_dc = 0,
                 uint64_t sync_cs = 0, uint64_t sync_dc = 0);

    // Begin the TE wait without blocking: the TE line to input, the stale level
    // recorded, the timeout started. Without v_sync the wait is already fired.
    void arm(bool v_sync, uint32_t timeout_us);

    // One non-blocking sample of the rising-then-falling wait. True once the
    // frame may start, whether the edge arrived or the timeout expired;
    // te_timeouts() counts the expiries. step() may convert ahead meanwhile.
    bool poll_te();

    // RAMWR and the first band's DMA kick, timestamped for write-start skew.
    void start_stream();

    // Convert at most max_rows into the back band and kick it when it is full
    // and the channel is free; raise CS once everything has drained. Never
    // blocks. max_rows < 1 kicks and finishes only. True when anything advanced,
    // so an interleaver can tell progress from spinning.
    bool step(int max_rows);

    // Whether a convert slice would find room: rows remain and the ring has a
    // slot the wire is not still reading.
    bool wants_convert() const {
        if (state != FrameState::ARMED && state != FrameState::STREAMING) {
            return false;
        }
        return convert_room() > 0;
    }

    // Converted rows the wire has not yet been handed: the margin a burst on
    // another display drains at wire rate.
    int staged_rows() const { return rows_converted - rows_kicked; }

    // Rows the ring holds ahead of the wire when full, the reserved slot out.
    int stage_capacity_rows() const { return (slot_count - 1) * rows_per_band; }

    // Ring rows a conversion burst could fill right now. The kick count is
    // read once, so a concurrent kick only understates the room.
    int stage_free_rows() const {
        int kicked = bands_kicked;
        int free_rows = (kicked + slot_count - 1) * rows_per_band - rows_converted;
        int remaining = dst_h - rows_converted;
        if (free_rows > remaining) {
            free_rows = remaining;
        }
        return free_rows < 0 ? 0 : free_rows;
    }

    // Whether every row has been converted, distinguishing a finished source
    // from a momentarily full ring, which wants_convert() conflates.
    bool convert_done() const { return rows_converted >= dst_h; }

    // Conversion still owed for the staged frame, priced at the rate prepare()
    // just measured on these pixels, so the estimate follows the rotation, source
    // memory and cache width in front of it rather than a table. 0 before a frame
    // is staged, or once every row is converted.
    uint32_t convert_debt_us() const;

    // Wall time the staged frame's rows take on the wire, the measured per-band
    // overhead included.
    uint32_t wire_window_us() const;

    bool busy() const { return dma_channel_is_busy(bus->dma_chan); }
    bool done() const { return state == FrameState::IDLE; }

    // Rough microseconds until the in-flight transfer drains, 0 when the channel
    // is free: the interleaver gives its convert slice to the nearest deadline.
    uint32_t deadline_us() const;

    // Abandon a staged or streaming frame: DMA aborted, FIFO drained, CS raised,
    // DC returned to an output. The panel holds its GRAM pointer, so the next
    // full frame recovers the glass.
    void abort_frame();

    // The DMA_IRQ_2 handler's entry for this display: kick the next converted
    // band, or timestamp the wire starving. ISR context only, gated by the
    // channel owner table rather than by state, and it never touches state,
    // stats or MicroPython.
    void kick_from_isr();

    // The interleaver's no-progress hook, for the host harness to advance mock
    // time.
    void idle_wait() const {}

    // Whether the bus has given its DMA channel back, which shutdown() does so a
    // long-lived program can rebuild screens without exhausting the 16 channels.
    // Every transfer needs the channel, so both command() and update() are refused
    // once it is gone.
    bool released() const { return bus->dma_chan < 0; }

    // Whether this display still holds its SRAM claim, which its destructor gives
    // back. update() needs the workspace, so it is refused once the claim is gone.
    bool has_sram() const { return sram_claim != nullptr; }

    // Bytes of SRAM this display claimed for its band and cache workspace, fixed
    // at construction. A broadcast group reports its first member's shared claim.
    size_t sram_bytes() const { return sram_claim_bytes; }

    // Instrumentation from the most recent update().
    FrameStats stats() const { return last; }

    // Frames since construction that began without their TE edge, the wait having
    // hit its timeout. Cumulative, so not part of the frame snapshot. A frame still
    // goes out, so this is the only sign v_sync did not hold.
    uint32_t te_timeouts() const { return te_timeout_count; }

    // Frames whose wait ended on a pulse it watched rise and that fell too soon to be
    // a blanking, cumulative, all of which te_timeouts() reads as healthy. A pulse
    // train defeats it: TE mode 2 rises within 17us of the release, inside
    // JOINED_HIGH_US, so those waits book as joined instead and te_probe()'s period is
    // what names that fault (measured 2026-08-10).
    uint32_t te_short_waits() const { return te_short_wait_count; }

    // Frames whose wait began with the line already high, cumulative, so the pulse
    // it ended on started unobserved and has no length to judge. One a frame means a
    // line released from a high and decaying through the pull-down; the occasional
    // one is a held frame arming inside a blanking, which reaches a real fall late
    // and is no fault.
    uint32_t te_joined_waits() const { return te_joined_wait_count; }

    // What this panel's rate reached: the divider only gets to clk_peri/(2*n), so
    // a request is rounded down, sometimes a long way. Fixed at construction.
    uint32_t baudrate() const { return achieved_baudrate; }

    // The lines this display drives, so a caller can build a mask over a subset of
    // a group's members and hand it back to prepare().
    uint64_t cs_lines() const { return cs_mask; }
    uint64_t dc_lines() const { return dc_mask; }

private:
    // The ring slot a band index streams from.
    uint8_t *slot_ptr(int band_index) const {
        return sram_claim + (size_t)(band_index % slot_count) * band_bytes;
    }

    // Rows convertible into the current band right now. One slot stays reserved
    // for the transfer in flight whether or not the channel is busy: reclaiming
    // it on the live busy flag lets a whole-band conversion slip in at the very
    // moment a transfer completes, ahead of the waiting kick, and the wire
    // starves for that conversion (measured at 82us per band on an SRAM
    // source, up to a full band's convert on PSRAM).
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
    bool try_kick();
    bool finish_if_drained();

    SPIDisplay &operator=(const SPIDisplay &) = default;

    // One packed destination row's bytes at this width and depth.
    static size_t packed_row_bytes(int dst_w, int bitdepth) {
        return (bitdepth == 12) ? (size_t)(dst_w * 3 / 2) : (size_t)(dst_w * 2);
    }

    // Put the bus back on this panel's rate, which is one compare per transfer for
    // a panel that has the bus to itself.
    void use_baudrate() {
        if (bus->requested_baudrate != requested_baudrate) {
            achieved_baudrate = bus->set_baudrate(requested_baudrate);
        }
    }

    SPIDisplayBus *bus;
    uint64_t cs_mask;    // Every CS this display drives, so a group drives them together
    uint64_t dc_mask;    // Likewise DC, since a group's members may each have their own
    uint dc_pin;         // The single DC line TE is read from, when te_pin < 0
    int te_pin;
    uint8_t ram_write_cmd;
    uint8_t te_on_cmd;
    uint8_t te_off_cmd;
    uint8_t te_mode_byte;
    int fmt;             // Destination packer tag (RGB444::format / RGB565::format)
    int dst_w;           // The panel's own dimensions, fixed for its lifetime
    int dst_h;
    int rows_per_band;   // Destination rows per DMA band, clamped at construction
    int cache_columns;

    // Band ring, cache storage, then the colour table an indexed source is drawn
    // through (PALETTE_BYTES, scanline.hpp), one claim. The table is per display
    // because interleaving drives several through frames concurrently, and in
    // SRAM because a per-pixel indirection into PSRAM reintroduces the XIP miss
    // the column cache exists to remove.
    uint8_t *sram_claim = nullptr;
    size_t sram_claim_bytes = 0;
    size_t band_bytes = 0;          // One band buffer, rounded up to 4
    size_t full_row_bytes = 0;      // A whole panel row packed, which prices a frame
                                    // before one is staged
    int cache_capacity = 0;         // Cache storage in bytes
    bool owns_sram_claim = false;   // Cleared on a broadcast copy, which shares
    uint32_t requested_baudrate;
    uint32_t achieved_baudrate;
    FrameStats last = {};
    uint32_t te_timeout_count = 0;
    uint32_t te_short_wait_count = 0;
    uint32_t te_joined_wait_count = 0;

    // Under this, the pulse the wait ended on was not a blanking. Above TE mode 2's
    // 500us H-sync pulses and below the shortest measured blanking, 1,277us on the
    // 1.54 and 1,536us on the 2.80.
    static constexpr uint32_t SHORT_WAIT_US = 700;

    // A high settled this soon after the release was already up when the wait began.
    // Over the 14us an arm and its two settled samples cost, measured 2026-08-10, and
    // far under the thousands an arm during the active scan waits for a blanking. A
    // line pulsing faster than this reads as joined whatever it does, since its next
    // rise arrives inside the window.
    static constexpr uint32_t JOINED_HIGH_US = 50;

    int slot_count = 2;       // Band ring depth, from stage_lines at construction

    // The staged frame, living from prepare() until the stream drains. The
    // volatile members are shared with the DMA_IRQ_2 handler; everything else
    // is frozen from prepare() until IDLE, and state itself is thread-only
    // (the handler is gated by the channel owner table instead).
    FrameState state = FrameState::IDLE;
    Descriptor desc = {};

    // The lines this write drives, 0 meaning every line the display owns. Only
    // prepare() sets them and going IDLE clears them, so a narrowed write cannot
    // leave a mask behind for the next one.
    uint64_t target_cs_mask = 0;
    uint64_t target_dc_mask = 0;
    uint64_t write_cs() const { return target_cs_mask ? target_cs_mask : cs_mask; }
    uint64_t write_dc() const { return target_dc_mask ? target_dc_mask : dc_mask; }

    // The one member this frame waits on, and the discipline that goes with it.
    // Cleared alongside the target masks, so a TEON can never outlive the frame
    // that asked for it and leave a second panel reaching the shared line.
    uint64_t sync_cs_mask = 0;
    uint64_t sync_dc_mask = 0;
    void te_command(uint8_t opcode, const uint8_t *data, size_t data_len);
    ColumnCache cache{nullptr, 0, 0};
    size_t full_band_bytes = 0;
    bool wide_frames = false;
    int frame_shift = 0;
    volatile int rows_converted = 0;  // Rows converted, published after the pixels
    volatile int rows_kicked = 0;     // Rows handed to the DMA channel
    volatile int bands_kicked = 0;    // Kicks so far, naming the next slot to send
    uint32_t frame_started_us = 0;
    bool te_fired = false;
    bool te_high_seen = false;
    bool te_raw_prev = false;
    uint32_t te_started_us = 0;
    uint32_t te_high_started_us = 0;   // When the pulse the wait ends on began
    uint32_t te_timeout_budget_us = 0;
    volatile bool stall_pending = false;      // Wire starving or draining
    volatile uint32_t stall_started_us = 0;   // When the starvation was seen
};

}  // namespace spidisplay
