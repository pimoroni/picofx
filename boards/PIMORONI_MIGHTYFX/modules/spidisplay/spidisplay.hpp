// SPDX-License-Identifier: MIT
//
// SPIDisplay: a panel-agnostic SPI + DMA transport for the MightyFX display
// pipeline. It holds an SPI peripheral, the CS/DC (and optional TE) GPIOs, and
// a DMA channel, and streams a converted frame band-by-band so conversion
// overlaps the in-flight DMA. Panel bringup stays in MicroPython via command().
//
// One instance per SPI port owns that bus; panel objects live above it in
// MicroPython. It drives a single CS/DC pair, so it addresses one panel, or
// several wired in parallel as one load. Both command() and update() block and
// return with CS high and the shifter drained, so a multiplexer's select line can
// be set immediately before either call and holds for its duration, and
// set_baudrate() can re-rate the bus between calls.
//
// The band and column cache buffers are file-scope, so the instances on separate
// ports share them and frames cannot overlap: one streams at a time.

#pragma once

#include <cstddef>
#include <cstdint>

#include "hardware/dma.h"
#include "hardware/spi.h"

namespace spidisplay {

// Observed shape of a panel's tearing-effect signal. high_us is the mean time
// the line spends asserted, which identifies the polarity: a short high against
// the period is the vertical blanking pulse, so the falling edge is the start of
// visible row 0. edges is the rising edges counted, for a sanity check against
// the panel's configured frame rate.
struct TeProbe {
    uint32_t period_us;
    uint32_t high_us;
    uint32_t edges;
};

class SPIDisplay {
public:
    // te < 0 means the tearing-effect signal shares the DC line (MightyFX);
    // otherwise te is a dedicated input GPIO. ram_write is the panel's
    // memory-write opcode. bitdepth is the panel's 12 (RGB444) or 16 (RGB565).
    // band_lines is destination rows per DMA band: larger bands amortise the
    // per-band setup overhead (tune up as SPI frequency rises), clamped to the
    // static buffer's capacity. cache_columns is source columns per column cache
    // window (see column_cache.hpp); 0 disables the cache. cache_wide_double
    // deepens the window so pixel-doubled frames still fill it. spi_frame_bits
    // is the SPI data frame width used for the pixel stream, 8 or 16.
    //
    // On the wiring side, panels sharing a bus need a unique cs each, since that
    // is the only signal selecting one. dc may be shared by panels that never use
    // v_sync, because a panel samples it only while its own cs is asserted. With
    // te < 0 it cannot be: the DC GPIO becomes an input to read TE, and TE is
    // free-running once the panel is sent TEON, so a shared line ties two panel
    // outputs together and the read is meaningless. A dedicated te frees dc again
    // for the same GPIO count, which only wins where some panels forgo v_sync.
    //
    // Behind a multiplexer, a dc line carrying TE has to pass both directions: an
    // analog mux does, a demux or buffer does not, and the failure is quiet, as
    // the wait times out and the frame still streams.
    SPIDisplay(uint spi_index, uint sck, uint mosi, uint cs, uint dc,
               uint baudrate, int te, uint8_t ram_write, int bitdepth,
               int band_lines, int cache_columns, bool cache_wide_double,
               int spi_frame_bits);
    ~SPIDisplay();

    // Toggle the pixel-doubled window depth between frames, for profiling.
    bool wide_double() const { return cache_wide_double; }
    void set_wide_double(bool value) { cache_wide_double = value; }

    // SPI data frame width for the pixel stream. The PL022 spends exactly 1.5
    // idle clocks between frames whatever their width, so 16-bit frames halve
    // that per byte pair and cut frame time by 7.9%; 8 is the reference.
    // Commands are always 8-bit. Takes effect on the next update().
    int frame_bits() const { return spi_frame_bits; }
    void set_frame_bits(int value) { spi_frame_bits = (value == 16) ? 16 : 8; }

    // Sample the TE line for ms milliseconds. Returns zeroed fields if the line
    // never toggles, so a panel that was never sent TEON reports rather than
    // hanging. Must not be called while a frame is streaming.
    TeProbe te_probe(uint32_t ms);

    // Whether one packed destination row of this width fits a band buffer. The
    // buffers are sized for the widest panel in scope at the shallower bit
    // depth, so a wider or deeper destination has to be rejected.
    bool row_fits(int dst_w) const;

    // Blocking raw register write: DC low, CS low, command, DC high, data,
    // CS high. Used for panel bringup from MicroPython.
    void command(const uint8_t *cmd, size_t cmd_len,
                 const uint8_t *data, size_t data_len);

    // Convert and stream a whole frame. src is RGBA8888. Each axis is centred,
    // or placed by its off_x/off_y top-left. Blocks until the frame has left
    // over SPI.
    void update(const uint8_t *src, int src_w, int src_h,
                int dst_w, int dst_h,
                int rotation, int mirror, int pixel_double,
                uint32_t bg, bool centred_x, int off_x, bool centred_y, int off_y,
                bool v_sync, uint32_t timeout_us);

    // Microsecond timings from the most recent update(): the first convert, TE/vsync wait,
    // and the whole frame emit (DC low before RAMWR to CS high after the stream).
    uint32_t pre_us() const { return last_pre_us; }
    uint32_t convert_us() const { return last_convert_us; }
    uint32_t te_wait_us() const { return last_te_wait_us; }
    uint32_t frame_us() const { return last_frame_us; }

    // Whole-frame instrumentation from the most recent update(). convert_total_us
    // covers every band; stall_us is time spent waiting on DMA, so conversion is
    // the constraint when it is near zero and the wire is when it dominates.
    uint32_t convert_total_us() const { return last_convert_total_us; }
    uint32_t stall_us() const { return last_stall_us; }
    uint32_t bands() const { return last_bands; }

    // time_us_32() at the RAMWR that opened the most recent frame. Absolute, so
    // the gap between two displays is their write-start skew.
    uint32_t write_start_us() const { return last_write_start_us; }

    // What the bus actually runs at: the divider only reaches clk_peri/(2*n), so
    // a requested rate is rounded down, sometimes a long way.
    uint32_t baudrate() const { return achieved_baudrate; }

    // Re-rate the bus, for panels on one port that want different rates. Takes
    // effect on the next transfer, so a driver sets it before command() or
    // update(). Must not be called while a frame is streaming.
    void set_baudrate(uint32_t value);

private:
    bool te_wait(uint32_t timeout_us);

    // Point the DMA channel at the SPI data register for the given frame width.
    // 16-bit frames go out most significant byte first, so the channel byte
    // swaps to keep the packed order on the wire.
    void configure_dma(int bits);

    spi_inst_t *spi;
    uint cs_pin;
    uint dc_pin;
    int te_pin;
    uint8_t ram_write_cmd;
    int fmt;             // Destination packer tag (RGB444::format / RGB565::format)
    int band_lines;      // Destination rows per DMA band
    int cache_columns;
    bool cache_wide_double;
    int spi_frame_bits;  // SPI data frame width for pixels (8 or 16)
    int dma_frame_bits;  // Width the DMA channel is currently configured for
    int dma_chan;
    uint32_t achieved_baudrate;  // What the divider reached for the request
    uint32_t last_pre_us = 0;
    uint32_t last_convert_us = 0;
    uint32_t last_te_wait_us = 0;
    uint32_t last_frame_us = 0;
    uint32_t last_convert_total_us = 0;
    uint32_t last_stall_us = 0;
    uint32_t last_bands = 0;
    uint32_t last_write_start_us = 0;
};

}  // namespace spidisplay
