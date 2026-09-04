// SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
//
// SPDX-License-Identifier: MIT
//
// The pixel formats a conversion reads and writes. A source trait says how to load a
// pixel, a destination packer how to pack one. Adding a format is adding a struct
// here, then teaching select_convert and the two kernels in scanline.hpp about it.

#pragma once

#include <cstdint>
#include <cstring>

#include "descriptor.hpp"

namespace spidisplay {

// Source format traits, each carrying a Loader built once per band. RGBA8888's is
// empty and compiles away. Indexed8's reads the colour table, whose words sit in
// memory as RGBA bytes like a direct pixel.
//
// Only an indexed source composites, its table being the one thing compositable
// ahead of the pixel loop. So an RGBA source's alpha is ignored and its colour
// taken as premultiplied. Blending per pixel was measured to roughly double a
// panel-sized frame's conversion, taking it off its wire bound.
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

// One channel of a premultiplied source over the background, the panel holding no
// destination pixels to read back.
//
// picovector stores colour already multiplied by its alpha, so the source is added
// and not scaled. Scaling again would darken a translucent entry by up to a quarter
// of the range. The arithmetic matches its blend_over_premul() byte for byte,
// rounding bias included.
//
// The clamp never engages on a valid entry. It is here because palette is
// caller-supplied, where an over-bright entry would carry into the next channel.
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

// An index byte reaches all 256 entries whatever the source's table length, so
// prepare_palette zeroes the rest and an index past the source reads transparent.
static constexpr size_t PALETTE_BYTES = 256 * 4;

inline void prepare_palette(uint8_t *table, const uint8_t *palette, size_t palette_len,
                            uint8_t bg_r, uint8_t bg_g, uint8_t bg_b) {
    if (palette_len > PALETTE_BYTES) {
        palette_len = PALETTE_BYTES;
    }
    memcpy(table, palette, palette_len);
    memset(table + palette_len, 0, PALETTE_BYTES - palette_len);
    for (size_t i = 0; i < PALETTE_BYTES; i += 4) {
        const int alpha = table[i + 3];
        table[i] = composite_over(table[i], bg_r, alpha);
        table[i + 1] = composite_over(table[i + 1], bg_g, alpha);
        table[i + 2] = composite_over(table[i + 2], bg_b, alpha);
    }
}

// A wide pair-format background fill, four packed pixel pairs per 12-byte piece.
// A separate function deliberately: held in convert_band's body, block or loops,
// it cost the covered path 1% in register pressure. The count is even, as every
// fill's is.
__attribute__((noinline))
inline uint8_t *fill_bg_pairs(uint8_t *dst_ptr, int pixels, const uint8_t *bg_packed) {
    uint8_t block[12];
    for (int i = 0; i < 12; ++i) {
        block[i] = bg_packed[i % 3];
    }
    int i = 0;
    for (; i + 7 < pixels; i += 8) {
        memcpy(dst_ptr, block, 12);
        dst_ptr += 12;
    }
    for (; i < pixels; i += 2) {
        dst_ptr[0] = bg_packed[0];
        dst_ptr[1] = bg_packed[1];
        dst_ptr[2] = bg_packed[2];
        dst_ptr += 3;
    }
    return dst_ptr;
}

// Destination packers. RGB444 packs two pixels into three bytes; RGB565 packs one
// into two big-endian bytes. format is the runtime tag, and the panel bit depth.
// The three functions below are where a format is selected and its row priced. The
// kernels still carry each group's byte count as literals, and a tag neither packer
// owns is treated as RGB565, so a third packer touches convert_band and
// convert_wrapped_row as well as this block.
struct RGB444 {
    static constexpr int format = 444;
    static constexpr int bitdepth = 12;
    static constexpr bool pairs = true;
    static constexpr int group_pixels = 2;
    static constexpr int group_bytes = 3;

    static inline void pack2(uint8_t *out,
                             uint8_t r0, uint8_t g0, uint8_t b0,
                             uint8_t r1, uint8_t g1, uint8_t b1) {
        out[0] = (r0 & 0xf0) | (g0 >> 4);   // R1 | G1
        out[1] = (b0 & 0xf0) | (r1 >> 4);   // B1 | R2
        out[2] = (g1 & 0xf0) | (b1 >> 4);   // G2 | B2
    }
};

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

// One packed destination row's bytes at this width
inline int packed_row_bytes(int format, int dst_w) {
    return format == RGB444::format
        ? dst_w / RGB444::group_pixels * RGB444::group_bytes
        : dst_w / RGB565::group_pixels * RGB565::group_bytes;
}

}  // namespace spidisplay
