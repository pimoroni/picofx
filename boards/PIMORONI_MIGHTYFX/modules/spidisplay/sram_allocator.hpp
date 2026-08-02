// SPDX-License-Identifier: MIT
//
// Claim allocator over the free SRAM region between the GC heap symbols.
// Header-only so the host test harness compiles the same code the firmware runs.
//
// Displays claim their band and cache workspace from the TOP of the region, so
// the module's buffer(nbytes, offset) views keep their stateless bottom-up
// addresses and only the ceiling moves. The claim table is fixed because the
// allocator itself must not allocate; a full table fails a claim cleanly and
// the caller raises.

#pragma once

#include <cstddef>
#include <cstdint>

namespace spidisplay {

class SRAMAllocator {
public:
    static constexpr int MAX_CLAIMS = 16;

    void init(uint8_t *region_start, uint8_t *region_end) {
        start = region_start;
        end = region_end;
    }

    // 4-aligned block of at least `bytes`, placed first-fit from the top.
    // nullptr when nothing fits or the table is full.
    uint8_t *claim(size_t bytes) {
        if (start == nullptr || bytes == 0) {
            return nullptr;
        }
        Claim *slot = nullptr;
        for (Claim &candidate : claims) {
            if (candidate.base == nullptr) {
                slot = &candidate;
                break;
            }
        }
        if (slot == nullptr) {
            return nullptr;
        }

        bytes = (bytes + 3) & ~(size_t)3;
        if (bytes > (size_t)(end - start)) {
            return nullptr;
        }
        uint8_t *base = align_down(end - bytes);
        // Step down past every live claim the candidate overlaps. Claims are
        // few (MAX_CLAIMS) so the rescan-on-move loop is trivially cheap.
        bool moved = true;
        while (moved) {
            if (base < start) {
                return nullptr;
            }
            moved = false;
            for (const Claim &other : claims) {
                if (other.base != nullptr
                        && base < other.base + other.bytes
                        && other.base < base + bytes) {
                    base = align_down(other.base - bytes);
                    moved = true;
                }
            }
        }

        slot->base = base;
        slot->bytes = bytes;
        return base;
    }

    // Unknown or null bases are ignored, so a double release is a no-op.
    void release(const uint8_t *base) {
        if (base == nullptr) {
            return;
        }
        for (Claim &candidate : claims) {
            if (candidate.base == base) {
                candidate.base = nullptr;
                candidate.bytes = 0;
                return;
            }
        }
    }

    // Contiguous bytes from the bottom of the region to the lowest live claim:
    // what a stateless bottom-anchored buffer() view can actually have.
    size_t available() const {
        if (start == nullptr) {
            return 0;
        }
        const uint8_t *ceiling = end;
        for (const Claim &candidate : claims) {
            if (candidate.base != nullptr && candidate.base < ceiling) {
                ceiling = candidate.base;
            }
        }
        return (size_t)(ceiling - start);
    }

private:
    struct Claim {
        uint8_t *base = nullptr;
        size_t bytes = 0;
    };

    static uint8_t *align_down(uint8_t *p) {
        return (uint8_t *)((uintptr_t)p & ~(uintptr_t)3);
    }

    Claim claims[MAX_CLAIMS] = {};
    uint8_t *start = nullptr;
    uint8_t *end = nullptr;
};

}  // namespace spidisplay
