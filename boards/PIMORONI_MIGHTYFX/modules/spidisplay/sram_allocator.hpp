// SPDX-License-Identifier: MIT
//
// Claim allocator over the free SRAM region between the GC heap symbols.
// Header-only so the host test harness compiles the same code the firmware runs.
//
// Claims come from both ends. Displays take their band and cache workspace from
// the TOP, canvases from the BOTTOM, and the two grow toward each other, so the
// space between them is always one contiguous span and neither end fragments the
// other. A canvas keeps the low addresses because a re-run of a script then gets
// the same ones back.
//
// The claim table is fixed because the allocator itself must not allocate; a full
// table fails a claim cleanly and the caller raises. Sixteen covers the displays
// and canvases a board can drive at once.

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
        Claim *slot = free_slot();
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
        slot->low = false;
        return base;
    }

    // The same from the bottom, for canvases. Placed first-fit upward, so the
    // lowest free address wins and a script's canvases land where they did last run.
    uint8_t *claim_low(size_t bytes) {
        if (start == nullptr || bytes == 0) {
            return nullptr;
        }
        Claim *slot = free_slot();
        if (slot == nullptr) {
            return nullptr;
        }

        bytes = (bytes + 3) & ~(size_t)3;
        if (bytes > (size_t)(end - start)) {
            return nullptr;
        }
        uint8_t *base = align_up(start);
        // Step up past every live claim the candidate overlaps, the mirror of the
        // downward walk above.
        bool moved = true;
        while (moved) {
            if (base + bytes > end) {
                return nullptr;
            }
            moved = false;
            for (const Claim &other : claims) {
                if (other.base != nullptr
                        && base < other.base + other.bytes
                        && other.base < base + bytes) {
                    base = align_up(other.base + other.bytes);
                    moved = true;
                }
            }
        }

        slot->base = base;
        slot->bytes = bytes;
        slot->low = true;
        return base;
    }

    // Drop every low claim at once. Canvases have no owner to finalise them, so
    // they come back when the screens that drew to them do.
    void release_low() {
        for (Claim &candidate : claims) {
            if (candidate.base != nullptr && candidate.low) {
                candidate.base = nullptr;
                candidate.bytes = 0;
                candidate.low = false;
            }
        }
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

    // The contiguous span between the two sets of claims: what a further claim from
    // either end can have.
    size_t available() const {
        if (start == nullptr) {
            return 0;
        }
        const uint8_t *floor = start;
        const uint8_t *ceiling = end;
        for (const Claim &candidate : claims) {
            if (candidate.base == nullptr) {
                continue;
            }
            if (candidate.low) {
                if (candidate.base + candidate.bytes > floor) {
                    floor = candidate.base + candidate.bytes;
                }
            } else if (candidate.base < ceiling) {
                ceiling = candidate.base;
            }
        }
        return ceiling > floor ? (size_t)(ceiling - floor) : 0;
    }

    // Bytes from the region base to the lowest workspace claim, which is what an
    // explicitly placed view is measured against: naming an offset says where to
    // start, so it reaches over the low claims deliberately.
    size_t headroom() const {
        if (start == nullptr) {
            return 0;
        }
        const uint8_t *ceiling = end;
        for (const Claim &candidate : claims) {
            if (candidate.base != nullptr && !candidate.low
                    && candidate.base < ceiling) {
                ceiling = candidate.base;
            }
        }
        return (size_t)(ceiling - start);
    }

    // Distance from the region base to the first byte a claim_low() would take, so
    // a caller can turn a claimed base into an offset.
    size_t low_offset(const uint8_t *base) const {
        return (size_t)(base - start);
    }

private:
    struct Claim {
        uint8_t *base = nullptr;
        size_t bytes = 0;
        bool low = false;
    };

    Claim *free_slot() {
        for (Claim &candidate : claims) {
            if (candidate.base == nullptr) {
                return &candidate;
            }
        }
        return nullptr;
    }

    static uint8_t *align_down(uint8_t *p) {
        return (uint8_t *)((uintptr_t)p & ~(uintptr_t)3);
    }

    static uint8_t *align_up(uint8_t *p) {
        return (uint8_t *)(((uintptr_t)p + 3) & ~(uintptr_t)3);
    }

    Claim claims[MAX_CLAIMS] = {};
    uint8_t *start = nullptr;
    uint8_t *end = nullptr;
};

}  // namespace spidisplay
