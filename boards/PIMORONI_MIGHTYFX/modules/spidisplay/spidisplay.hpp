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

namespace spidisplay {

// Observed shape of a panel's tearing-effect signal. A short high_us against the
// period means the asserted level is vertical blanking, so the falling edge
// starts visible row 0. edges is the rising edges counted.
struct TeProbe {
    uint32_t period_us;
    uint32_t high_us;
    uint32_t edges;
};

// One update()'s worth of instrumentation, all microseconds. convert_total_us
// against stall_us says where the frame went: conversion is the constraint when the
// stall is near zero, the wire when it dominates. write_start_us is absolute, so the
// gap between two displays is their skew.
struct FrameStats {
    uint32_t pre_us;             // Descriptor setup
    uint32_t convert_us;         // The first band alone
    uint32_t te_wait_us;
    uint32_t frame_us;           // DC low before RAMWR to CS high after the stream
    uint32_t convert_total_us;   // Every band
    uint32_t stall_us;           // Waiting on DMA
    uint32_t write_start_us;     // time_us_32() at the RAMWR that opened the frame
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
    // Construction claims 2 * band_lines * row_bytes + cache_columns * width * 4
    // bytes of SRAM for the band and cache workspace; when the claim fails,
    // has_sram() is false and the wrapper raises rather than configuring GPIO.
    //
    // Wiring: cs must be unique per panel, being the only signal selecting one. dc
    // may be shared, but not by panels using TE: each breakout ties TE to that line
    // through a series resistor, so panels sharing it divide the line and the
    // asserted level is lost. Behind a multiplexer a dc line carrying TE needs an
    // analog mux to pass both directions; a demux or buffer fails quietly, the wait
    // timing out while the frame still streams.
    SPIDisplay(SPIDisplayBus *bus, uint cs, uint dc, int te, uint8_t ram_write,
               int bitdepth, int width, int height, uint32_t baudrate,
               int band_lines, int cache_columns);

    // A broadcast group starts as a copy of one member and add()s the rest. The
    // copy claims no GPIO, since the members own theirs, and is a snapshot: a
    // member that later re-rates itself moves only itself. It shares the member's
    // SRAM claim rather than taking its own; only the member releases it, so the
    // wrapper roots the member for the group's lifetime.
    SPIDisplay(const SPIDisplay &member) {
        *this = member;
        owns_sram_claim = false;
    }

    ~SPIDisplay();

    // Whether another display can share a frame with this one: the same bus, and
    // agreement on everything the stream depends on. Register state bringup put in
    // the panel is not compared, so a group can carry a differing MADCTL.
    bool compatible_with(const SPIDisplay &other) const;

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

    // Blocking raw register write: DC low, CS low, command, DC high, data,
    // CS high. Used for panel bringup from MicroPython.
    void command(const uint8_t *cmd, size_t cmd_len,
                 const uint8_t *data, size_t data_len);

    // Convert and stream a whole frame. src is RGBA8888. Each axis is centred,
    // or placed by its off_x/off_y top-left. Blocks until the frame has left
    // over SPI.
    void update(const uint8_t *src, int src_w, int src_h,
                int rotation, int mirror, int pixel_double,
                uint32_t bg, bool centred_x, int off_x, bool centred_y, int off_y,
                bool v_sync, uint32_t timeout_us);

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

    // What this panel's rate reached: the divider only gets to clk_peri/(2*n), so
    // a request is rounded down, sometimes a long way. Fixed at construction.
    uint32_t baudrate() const { return achieved_baudrate; }

private:
    bool te_wait(uint32_t timeout_us);

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
    int fmt;             // Destination packer tag (RGB444::format / RGB565::format)
    int dst_w;           // The panel's own dimensions, fixed for its lifetime
    int dst_h;
    int rows_per_band;   // Destination rows per DMA band, clamped at construction
    int cache_columns;
    uint8_t *sram_claim = nullptr;  // Band pair then cache storage, one claim
    size_t sram_claim_bytes = 0;
    size_t band_bytes = 0;          // One band buffer, rounded up to 4
    int cache_capacity = 0;         // Cache storage in RGBA8888 pixels
    bool owns_sram_claim = false;   // Cleared on a broadcast copy, which shares
    uint32_t requested_baudrate;
    uint32_t achieved_baudrate;
    FrameStats last = {};
};

}  // namespace spidisplay
