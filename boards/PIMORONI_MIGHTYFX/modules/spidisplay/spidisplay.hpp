// SPDX-License-Identifier: MIT
//
// SPIDisplay: a panel-agnostic SPI + DMA transport for the MightyFX display
// pipeline. It owns the SPI peripheral, the CS/DC (and optional TE) GPIOs, and
// a DMA channel, and streams a converted frame band-by-band so conversion
// overlaps the in-flight DMA. Panel bringup stays in MicroPython via command().
// See boards/PIMORONI_MIGHTYFX/DISPLAY_PIPELINE_PLAN.md.

#pragma once

#include <cstddef>
#include <cstdint>

#include "hardware/dma.h"
#include "hardware/spi.h"

namespace spidisplay {

class SPIDisplay {
public:
    // te < 0 means the tearing-effect signal shares the DC line (MightyFX);
    // otherwise te is a dedicated input GPIO. ram_write is the panel's
    // memory-write opcode. bitdepth is the panel's 12 (RGB444) or 16 (RGB565).
    // band_lines is destination rows per DMA band: larger bands amortise the
    // per-band setup overhead (tune up as SPI frequency rises), clamped to the
    // static buffer's capacity.
    SPIDisplay(uint spi_index, uint sck, uint mosi, uint cs, uint dc,
               uint baudrate, int te, uint8_t ram_write, int bitdepth, int band_lines);
    ~SPIDisplay();

    // Blocking raw register write: DC low, CS low, command, DC high, data,
    // CS high. Used for panel bringup from MicroPython.
    void command(const uint8_t *cmd, size_t cmd_len,
                 const uint8_t *data, size_t data_len);

    // Convert and stream a whole frame. src is RGBA8888. centred places the
    // source in the middle of the panel, otherwise off_x/off_y are its top-left.
    // Blocks until the frame has left over SPI.
    void update(const uint8_t *src, int src_w, int src_h,
                int dst_w, int dst_h,
                int rotation, int mirror, int pixel_double,
                uint32_t bg, bool centred, int off_x, int off_y, bool v_sync);

private:
    void te_wait();

    spi_inst_t *spi;
    uint cs_pin;
    uint dc_pin;
    int te_pin;
    uint8_t ram_write_cmd;
    int fmt;             // Destination packer tag (RGB444::format / RGB565::format)
    int band_lines;      // Destination rows per DMA band
    int dma_chan;
};

}  // namespace spidisplay
