// SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
//
// SPDX-License-Identifier: MIT
//
// The pixel formats a conversion reads and writes. A source trait says how to load a
// pixel and a destination packer how to pack one. Adding a format is adding a struct
// here, then teaching select_convert and the two kernels in scanline.hpp about it.
//
// Each source trait carries a Loader built outside the pixel loop. Only an indexed
// source is composited over the background, its palette being the one thing that can
// be composited ahead of that loop, so an RGBA source's alpha is ignored and its
// colour taken as premultiplied. Blending every pixel was measured to roughly double
// a panel-sized frame's conversion, so it no longer keeps up with the wire.

#pragma once

#include <cstdint>
#include <cstring>

#include "descriptor.hpp"

namespace spidisplay {

// A direct source, its Loader empty and compiling away
struct RGBA8888 {
    static constexpr int bytes = 4;

    struct Loader {
        explicit Loader(const Descriptor &) {}

        inline void load(const uint8_t *p, uint8_t &r, uint8_t &g, uint8_t &b) const {
            r = p[0];
            g = p[1];
            b = p[2];
        }
    };
};

// An indexed source, its Loader reading a colour table of RGBA words
struct Indexed8 {
    static constexpr int bytes = 1;

    struct Loader {
        explicit Loader(const Descriptor &desc) : pal(desc.palette) {}

        inline void load(const uint8_t *p, uint8_t &r, uint8_t &g, uint8_t &b) const {
            const uint8_t *entry = pal + ((size_t)*p << 2);
            r = entry[0];
            g = entry[1];
            b = entry[2];
        }

        const uint8_t *pal;
    };
};

// Composite one channel of a premultiplied source over the background, there being no
// destination pixel to read back from a panel. picovector stores colour already
// multiplied by its alpha, so the source is added and not scaled, matching its
// blend_over_premul() byte for byte. The clamp only engages on an over-bright entry.
inline uint8_t composite_over(int src, int bg, int alpha) {
    if (alpha == 0) {
        return (uint8_t)bg;
    }
    if (alpha == 255) {
        return (uint8_t)src;
    }
    const int value = src + ((bg * (255 - alpha) + 128) >> 8);
    return (uint8_t)(value > 255 ? 255 : value);
}

static constexpr size_t PALETTE_BYTES = 256 * 4;    // Bytes in a full colour table

// Prepare a source's palette once a frame, compositing it over the background
inline void prepare_palette(uint8_t *table, const uint8_t *palette, size_t palette_len,
                            uint8_t bg_r, uint8_t bg_g, uint8_t bg_b) {
    // A longer table is truncated, since no source pixel can reach past 256 entries
    if (palette_len > PALETTE_BYTES) {
        palette_len = PALETTE_BYTES;
    }
    memcpy(table, palette, palette_len);

    // Zero the entries the source does not fill, so a pixel naming one past its
    // palette reads as transparent instead of as stale colour
    memset(table + palette_len, 0, PALETTE_BYTES - palette_len);
    for (size_t i = 0; i < PALETTE_BYTES; i += 4) {
        const int alpha = table[i + 3];
        table[i] = composite_over(table[i], bg_r, alpha);
        table[i + 1] = composite_over(table[i + 1], bg_g, alpha);
        table[i + 2] = composite_over(table[i + 2], bg_b, alpha);
    }
}

// Pixels in the block below, and so the fewest a caller should hand fill_bg_pairs
constexpr int BG_BLOCK_PIXELS = 8;

// Fill a run of background pixels in a pair format. A pair packs to three bytes, so a
// 12-byte block is the shortest span that is both whole pairs and whole words, copied
// until fewer than BG_BLOCK_PIXELS remain. Kept out of line because inlining it into
// convert_band cost the covered path 1% in register pressure. pixels has to be even.
__attribute__((noinline))
inline uint8_t *fill_bg_pairs(uint8_t *dst_ptr, int pixels, const uint8_t *bg_packed) {
    constexpr int PAIR_BYTES = 3;
    constexpr int BLOCK_BYTES = 12;

    uint8_t block[BLOCK_BYTES];
    for (int i = 0; i < BLOCK_BYTES; ++i) {
        block[i] = bg_packed[i % PAIR_BYTES];
    }
    int i = 0;
    for (; i + BG_BLOCK_PIXELS - 1 < pixels; i += BG_BLOCK_PIXELS) {
        memcpy(dst_ptr, block, BLOCK_BYTES);
        dst_ptr += BLOCK_BYTES;
    }
    for (; i < pixels; i += 2) {
        dst_ptr[0] = bg_packed[0];
        dst_ptr[1] = bg_packed[1];
        dst_ptr[2] = bg_packed[2];
        dst_ptr += PAIR_BYTES;
    }
    return dst_ptr;
}

// Destination packers. format tags a packer and bitdepth the panel depth it serves,
// and a tag neither packer owns is treated as RGB565.

// Two pixels packed into three bytes
struct RGB444 {
    static constexpr int format = 444;
    static constexpr int bitdepth = 12;
    static constexpr bool pairs = true;
    static constexpr int group_pixels = 2;
    static constexpr int group_bytes = 3;

    static inline void pack2(uint8_t *out,
                             uint8_t r0, uint8_t g0, uint8_t b0,
                             uint8_t r1, uint8_t g1, uint8_t b1) {
        out[0] = (r0 & 0xf0) | (g0 >> 4);   // R0 | G0
        out[1] = (b0 & 0xf0) | (r1 >> 4);   // B0 | R1
        out[2] = (g1 & 0xf0) | (b1 >> 4);   // G1 | B1
    }
};

// One pixel packed into two big-endian bytes
struct RGB565 {
    static constexpr int format = 565;
    static constexpr int bitdepth = 16;
    static constexpr bool pairs = false;
    static constexpr int group_pixels = 1;
    static constexpr int group_bytes = 2;

    static inline void pack1(uint8_t *out, uint8_t r, uint8_t g, uint8_t b) {
        const uint16_t value = (uint16_t)__builtin_bswap16(
            ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3));
        memcpy(out, &value, 2);
    }
};

// The packer tag for a panel bit depth, 0 where no packer exists for it
inline int format_for_bitdepth(int bitdepth) {
    if (bitdepth == RGB444::bitdepth) {
        return RGB444::format;
    }
    if (bitdepth == RGB565::bitdepth) {
        return RGB565::format;
    }
    return 0;
}

// Pixels a row width has to be a multiple of, so a packed row ends on a whole group
inline int pixels_per_group(int format) {
    return format == RGB444::format ? RGB444::group_pixels : RGB565::group_pixels;
}

// One packed destination row's bytes, a part group at the end of a width being lost
inline int packed_row_bytes(int format, int dst_w) {
    return format == RGB444::format
        ? dst_w / RGB444::group_pixels * RGB444::group_bytes
        : dst_w / RGB565::group_pixels * RGB565::group_bytes;
}

}  // namespace spidisplay
