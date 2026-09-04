// SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
//
// SPDX-License-Identifier: MIT
//
// A scheduler for updating several displays at the same time, so a pair costs little
// more than one display's frame instead of twice as much.
//
// A display waits for its tear-effect (TE) signal edge, then streams its frame over
// the wire while converting the pixels still to come. Run one display after another
// and those waits and conversions are serial. Interleaved, one display's wait is
// another's conversion time, and every wire streams at once.
//
// The displays must be of one type, on different buses, and already prepared. How far
// one converts ahead of its own stream is bounded by its ring, stage_capacity_rows()
// deep, so staging depth is a display setting and not an interleaver one.

#pragma once

#include <cstdint>

namespace spidisplay {

// Start every display's TE wait at once so they overlap, then loop until each has
// finished its frame. hysteresis_rows is the free ring rows another display must show
// before the slice leaves the one it is on, or half its ring when negative.
template <typename Display>
void interleave(Display *const *displays, int count, bool v_sync,
                uint32_t te_timeout_us, int slice_rows, int hysteresis_rows) {
    // Names the zero step() is given to service a wire and convert nothing. It has to
    // stay zero, so the sweep that cannot wait never spends its time converting.
    constexpr int NO_CONVERT_ROWS = 0;

    for (int slot = 0; slot < count; ++slot) {
        displays[slot]->arm(v_sync, te_timeout_us);
    }

    // Run until every frame is done. start_slot rotates which display is looked at
    // first, and sticky_slot remembers which one holds the convert slice.
    int start_slot = 0;
    int sticky_slot = -1;
    for (;;) {
        bool progressed = false;
        bool all_done = true;

        // Serve what cannot wait, TE edges and freed channels, before any conversion
        for (int offset = 0; offset < count; ++offset) {
            Display *display = displays[(offset + start_slot) % count];
            if (display->done()) {
                continue;
            }
            all_done = false;
            if (display->poll_te()) {
                // Its TE edge has arrived, so the wire can start
                display->start_stream();
                progressed = true;
            } else {
                progressed |= display->step(NO_CONVERT_ROWS);
            }
        }
        if (all_done) {
            break;    // Every display has finished its frame
        }
        // Rotate the start so ties do not always favour the same display.
        start_slot = (start_slot + 1) % count;

        // Release the slice once the display holding it has converted its frame
        if (sticky_slot >= 0 && displays[sticky_slot]->convert_done()) {
            sticky_slot = -1;
        }

        // Choose which display converts. The pick sticks with one display while its
        // ring has room, so its source reads stay in the shared XIP cache, which
        // alternating between two PSRAM rotation-90 displays would evict.
        int chosen_slot = -1;
        int fewest_staged = 0;
        for (int offset = 0; offset < count; ++offset) {
            int slot = (offset + start_slot) % count;
            Display *display = displays[slot];
            if (!display->wants_convert()) {
                continue;
            }
            // The first of two thresholds. A display with only a slice plus two bands
            // left to stream takes the slice back, before its ring empties.
            int staged = display->staged_rows();
            if (staged <= slice_rows + 2 * display->band_rows()
                    && (chosen_slot < 0 || staged < fewest_staged)) {
                chosen_slot = slot;
                fewest_staged = staged;
            }
        }
        // No ring is close to empty, so whoever holds the slice keeps it
        if (chosen_slot < 0 && sticky_slot >= 0
                && displays[sticky_slot]->wants_convert()) {
            chosen_slot = sticky_slot;
        }
        if (chosen_slot < 0) {
            // Nothing holds the slice either, so it goes to the emptiest ring
            int most_free_rows = 0;
            for (int offset = 0; offset < count; ++offset) {
                int slot = (offset + start_slot) % count;
                Display *display = displays[slot];
                if (!display->wants_convert()) {
                    continue;
                }
                // The second threshold, which a candidate clears before a full ring
                // hands the slice on, so one freed slot cannot bounce it straight
                // back. Negative selects half the ring.
                int clearance_rows = hysteresis_rows < 0
                                     ? display->stage_capacity_rows() / 2
                                     : hysteresis_rows;
                int free_rows = display->stage_free_rows();
                if ((sticky_slot < 0 || free_rows >= clearance_rows)
                        && (chosen_slot < 0 || free_rows > most_free_rows)) {
                    chosen_slot = slot;
                    most_free_rows = free_rows;
                }
            }
        }
        if (chosen_slot >= 0) {
            // The chosen display keeps the slice until it converts or loses it
            sticky_slot = chosen_slot;
            progressed |= displays[chosen_slot]->step(slice_rows);
        }

        if (!progressed) {
            // Nothing advanced this turn, and on a real display this hook is empty
            displays[0]->idle_wait();
        }
    }
}

}  // namespace spidisplay
