// SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
//
// SPDX-License-Identifier: MIT
//
// A Descriptor stores how a frame's pixels land on a panel, calculated once a frame
// and then read by every conversion that frame does. It carries the placement, the
// rotation, the mirror and any repeat of the source frame, reduced to an affine form
// the pixel loops can walk with no per-pixel calculation of their own.

#pragma once

#include <cstdint>

namespace spidisplay {

// Loop-invariant parameters, set by make_descriptor. Every destination pixel maps to
// a source column and row, u and v, before any pixel-double halving,
//
//   u = du_dx*dst_x + du_dy*dst_y + u_at_origin
//   v = dv_dx*dst_x + dv_dy*dst_y + v_at_origin
//
// where rotation decides which of the two varies with dst_x and which with dst_y, so
// the source covers a destination region and a row walk steps by a constant.
struct Descriptor {
    // The source
    const uint8_t *src;
    const uint8_t *palette;   // 256 RGBA words for an indexed source, else null
    int src_row_bytes;        // Source pitch in bytes, row to row
    int src_pixel_bytes;      // Source bytes per pixel
    int src_extent_w;         // Source extent in destination pixels, doubled when
                              // pixel_double
    int src_extent_h;

    // The destination
    int dst_w;
    int dst_h;
    int dst_row_bytes;        // Packed bytes per destination row

    // The region the source covers, half-open on both axes
    int dst_x_start, dst_x_end;
    int dst_y_start, dst_y_end;

    // The affine map above
    int du_dx, du_dy, u_at_origin;
    int dv_dx, dv_dy, v_at_origin;

    // How a row walk moves
    int src_step_x;                 // Source advance in bytes, per pixel along a row
    bool row_walks_along_src_row;   // Whether a destination row walks along a source
                                    // row, which rotation 0 and 180 do. At 90 and
                                    // 270 it walks down a source column instead
    bool pixel_double;              // Whether each source pixel covers a 2x2
                                    // destination block
    bool row_walks_forward;         // Whether a row walk steps forward through the
                                    // source. A rotation or mirror that reverses the
                                    // axis reads it backwards instead

    // A wrapped axis repeats the source instead of running outside of it, so the
    // covered region is the whole frame on whichever destination axis it binds. A
    // mirrored wrap reverses every other repeat, so every seam is a reflection.
    bool wrap_u;
    bool wrap_v;
    bool wrap_mirror_u;
    bool wrap_mirror_v;

    // What an uncovered pixel is filled with
    uint8_t bg_r;
    uint8_t bg_g;
    uint8_t bg_b;
};

// Floored modulo, reducing a coordinate of either sign into [0, period).
inline int floor_mod(int value, int period) {
    int m = value % period;
    return m < 0 ? m + period : m;
}

// Fold a coordinate in [0, 2 * extent) onto [0, extent), the top half backwards
inline int fold(int unfolded, int extent) {
    return unfolded < extent ? unfolded : 2 * extent - 1 - unfolded;
}

// A clockwise rotation of 0, 90, 180 or 270, then a horizontal mirror of the output.
struct Transform {
    int rotation;
    bool mirror;
};


// Fill a descriptor for a whole frame. The source sits at its offset in the plane,
// which is the destination before that plane is rotated clockwise and mirrored.
// Descriptor's coefficients are that inverted, from a panel pixel to a source pixel.
//
// Each axis is either centred or placed by its off_x/off_y top-left in the plane.
// A wrapped axis makes any offset valid, and wrap_mirror_x and wrap_mirror_y imply
// the wrap on their own axis. src_row_bytes is the source pitch, wider than a row on
// a strided view into a larger image, and dst_row_bytes the packed destination row,
// which only the caller's packer knows.
inline Descriptor make_descriptor(const uint8_t *src, int src_w, int src_h,
                                  int dst_w, int dst_h, int dst_row_bytes,
                                  const Transform &transform, bool pixel_double,
                                  bool centred_x, int off_x, bool centred_y, int off_y,
                                  bool wrap_x, bool wrap_y,
                                  bool wrap_mirror_x, bool wrap_mirror_y,
                                  uint32_t bg,
                                  int src_row_bytes, int src_pixel_bytes) {
    int scale = pixel_double ? 2 : 1;
    // Source extent in destination pixels
    int src_extent_w = src_w * scale;
    int src_extent_h = src_h * scale;

    // The plane is the output before rotation. At 90 / 270 its dimensions are swapped
    bool swap_axes = (transform.rotation == 90 || transform.rotation == 270);
    int plane_w = swap_axes ? dst_h : dst_w;
    int plane_h = swap_axes ? dst_w : dst_h;

    // Place the source's top-left in the plane, centred or at the caller's offset
    int place_x = centred_x ? ((plane_w - src_extent_w) >> 1) : off_x;
    int place_y = centred_y ? ((plane_h - src_extent_h) >> 1) : off_y;

    // Bring the placement into range, so the affine coefficients cannot overflow
    wrap_x = wrap_x || wrap_mirror_x;
    wrap_y = wrap_y || wrap_mirror_y;
    constexpr int PLACE_LIMIT = 1 << 28;
    if (wrap_x) {
        // A repeat has a period, so any placement reduces into it
        place_x = floor_mod(place_x, wrap_mirror_x ? 2 * src_extent_w : src_extent_w);
    } else if (place_x > PLACE_LIMIT) {
        // Already too far out to cover anything, so clamp and cover nothing still
        place_x = PLACE_LIMIT;
    } else if (place_x < -PLACE_LIMIT) {
        place_x = -PLACE_LIMIT;
    }
    if (wrap_y) {
        place_y = floor_mod(place_y, wrap_mirror_y ? 2 * src_extent_h : src_extent_h);
    } else if (place_y > PLACE_LIMIT) {
        place_y = PLACE_LIMIT;
    } else if (place_y < -PLACE_LIMIT) {
        place_y = -PLACE_LIMIT;
    }

    // mirror_step and mirror_base turn dst_x into the mirrored column mx
    int mirror_step = transform.mirror ? -1 : 1;
    int mirror_base = transform.mirror ? (dst_w - 1) : 0;

    // Plane coordinates as affine functions of the destination pixel. cx and cy are
    // that pixel with the rotation and mirror undone, and u and v subtract the source
    // offset. Exactly one of u and v varies with dst_x, the other with dst_y.
    int du_dx, du_dy, u_at_origin, dv_dx, dv_dy, v_at_origin;
    switch (transform.rotation) {
        case 90:   // cx = dst_y, cy = (dst_w-1) - mx
            du_dx = 0;             du_dy = 1;
            dv_dx = -mirror_step;  dv_dy = 0;
            u_at_origin = -place_x;
            v_at_origin = (dst_w - 1 - mirror_base) - place_y;
            break;
        case 180:  // cx = (dst_w-1) - mx, cy = (dst_h-1) - dst_y
            du_dx = -mirror_step;  du_dy = 0;
            dv_dx = 0;             dv_dy = -1;
            u_at_origin = (dst_w - 1 - mirror_base) - place_x;
            v_at_origin = (dst_h - 1) - place_y;
            break;
        case 270:  // cx = (dst_h-1) - dst_y, cy = mx
            du_dx = 0;             du_dy = -1;
            dv_dx = mirror_step;   dv_dy = 0;
            u_at_origin = (dst_h - 1) - place_x;
            v_at_origin = mirror_base - place_y;
            break;
        default:   // 0: cx = mx, cy = dst_y
            du_dx = mirror_step;   du_dy = 0;
            dv_dx = 0;             dv_dy = 1;
            u_at_origin = mirror_base - place_x;
            v_at_origin = -place_y;
            break;
    }

    // The switch above can take the origin back outside the period, so reduce again
    if (wrap_x) {
        u_at_origin = floor_mod(u_at_origin,
                                wrap_mirror_x ? 2 * src_extent_w : src_extent_w);
    }
    if (wrap_y) {
        v_at_origin = floor_mod(v_at_origin,
                                wrap_mirror_y ? 2 * src_extent_h : src_extent_h);
    }

    // Where one axis is covered. Its coordinate steps by one per pixel, so the pixels
    // landing inside the source extent form one span, clamped to the destination.
    auto range = [](int coeff, int base, int src_extent, int dst_extent,
                    int &span_start, int &span_end) {
        if (coeff > 0) {
            span_start = -base;
            span_end = src_extent - base;
        } else {
            span_start = base - src_extent + 1;
            span_end = base + 1;
        }
        if (span_start < 0) span_start = 0;
        if (span_end > dst_extent) span_end = dst_extent;
        if (span_end < span_start) span_end = span_start;
    };

    Descriptor desc;
    desc.src = src;
    desc.palette = nullptr;   // An indexed caller points this at its colour table
    desc.dst_w = dst_w;
    desc.dst_h = dst_h;
    desc.du_dx = du_dx; desc.du_dy = du_dy; desc.u_at_origin = u_at_origin;
    desc.dv_dx = dv_dx; desc.dv_dy = dv_dy; desc.v_at_origin = v_at_origin;
    desc.src_row_bytes = src_row_bytes;
    desc.src_pixel_bytes = src_pixel_bytes;
    desc.pixel_double = pixel_double;

    desc.wrap_u = wrap_x;
    desc.wrap_v = wrap_y;
    desc.wrap_mirror_u = wrap_mirror_x;
    desc.wrap_mirror_v = wrap_mirror_y;
    desc.src_extent_w = src_extent_w;
    desc.src_extent_h = src_extent_h;

    // dst_x is bound by whichever coordinate varies with it, and supplies the
    // per-pixel source stride; dst_y is bound by the other coordinate.
    if (du_dx != 0) {
        if (wrap_x) {
            desc.dst_x_start = 0;
            desc.dst_x_end = dst_w;
        } else {
            range(du_dx, u_at_origin, src_extent_w, dst_w,
                  desc.dst_x_start, desc.dst_x_end);
        }
        desc.row_walks_along_src_row = true;
        desc.src_step_x = (du_dx > 0 ? 1 : -1) * src_pixel_bytes;
        desc.row_walks_forward = (du_dx > 0);
    } else {
        if (wrap_y) {
            desc.dst_x_start = 0;
            desc.dst_x_end = dst_w;
        } else {
            range(dv_dx, v_at_origin, src_extent_h, dst_w,
                  desc.dst_x_start, desc.dst_x_end);
        }
        desc.row_walks_along_src_row = false;
        desc.src_step_x = (dv_dx > 0 ? 1 : -1) * desc.src_row_bytes;
        desc.row_walks_forward = (dv_dx > 0);
    }
    if (du_dy != 0) {
        if (wrap_x) {
            desc.dst_y_start = 0;
            desc.dst_y_end = dst_h;
        } else {
            range(du_dy, u_at_origin, src_extent_w, dst_h,
                  desc.dst_y_start, desc.dst_y_end);
        }
    } else {
        if (wrap_y) {
            desc.dst_y_start = 0;
            desc.dst_y_end = dst_h;
        } else {
            range(dv_dy, v_at_origin, src_extent_h, dst_h,
                  desc.dst_y_start, desc.dst_y_end);
        }
    }

    desc.dst_row_bytes = dst_row_bytes;

    // bg arrives packed as 0x00BBGGRR
    desc.bg_r = bg & 0xff;
    desc.bg_g = (bg >> 8) & 0xff;
    desc.bg_b = (bg >> 16) & 0xff;
    return desc;
}

}  // namespace spidisplay
