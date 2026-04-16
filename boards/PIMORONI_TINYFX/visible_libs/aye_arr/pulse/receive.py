# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from collections import deque

import rp2
from machine import Pin

from .common import DebugPin, Pulse
from .pio.rx import FREQUENCY, TIMEOUT_REACHED, count_to_burst_us, count_to_idle_us, pulsereader, pulsereader_debug

# Constants
MAX_BUFFER = const(1024)
DEFAULT_FILTER_THRESHOLD = const(200)


class PulseReceiver:
    def __init__(self, pin_num, pio, sm,
                 debug_pin_base=None, debug_blip_pin=None):
        self.__counts = deque((), MAX_BUFFER)
        self.__sequence = []
        self.__last_pulse = None

        # Set up the pin used to receive pulse signals
        pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)

        # For the RP2350, shift the gpio_base of this PIO if the pin is above 32
        base = 16 if pin_num >= 32 else 0
        rp2.PIO(pio).gpio_base(base)

        # Load either the regular or debug program into the chosen StateMachine
        if debug_pin_base is None:
            self.__sm = rp2.StateMachine(sm + (pio * 4), pulsereader,
                                         freq=FREQUENCY, in_base=pin,
                                         jmp_pin=pin)
        else:
            if debug_pin_base < base or debug_pin_base > base + 30:    # 30 because the debug PIO uses two sideset pins
                raise ValueError(f"'debug_pin_base' is outside the GPIO base of 'pin_num'.\
                                 Choose a 'debug_pin_base' between {base} and {base + 30}") from None
            self.__sm = rp2.StateMachine(sm + (pio * 4), pulsereader_debug,
                                         freq=FREQUENCY, in_base=pin,
                                         sideset_base=Pin(debug_pin_base),
                                         jmp_pin=pin)

        # Set up debug pin for scoping
        self.__debug_blip_pin = DebugPin(debug_blip_pin, Pin.OUT)

    def start(self):
        self.__sm.irq(self.__handler)
        self.__sm.active(1)

    def stop(self):
        self.__sm.active(0)
        self.__sm.irq(None)

    def reset(self):
        self.__counts = deque((), MAX_BUFFER)
        self.__sequence = []

    @micropython.native
    def __handler(self, sm):
        # Copy received counts from the SM to the deque for later processing.
        while sm.rx_fifo() > 0:
            self.__counts.append(sm.get())

    def __analyse(self, pulses):
        # Override this to analyse a received sequence of pulses
        pass

    def decode_no_filter(self):
        """
        Checks for any newly received pulses since the last time `decode` was
        called. Once a sufficient number of pulses has been received, as
        indicated by the PIO program's timeout being reached, the pulses are
        passed to an overridable `__analyse` function to act on any data.

        This should be called frequently from user code to avoid pulses
        queuing up and making remote button presses feel sluggish.

        This function lacks any filtering meaning any "blips" in
        received pulses could cause data to be discarded.
        """

        if not self.__sm.active():
            raise RuntimeError("Cannot decode IR signals. Check that you have called `.start()` on the receiver first.")

        # Go through all counts currently stored
        while len(self.__counts) > 0:
            count_pair = self.__counts.popleft()   # Extract the oldest count pair

            # Did the count timeout get reached?
            if count_pair == TIMEOUT_REACHED:
                # Analyse, and clear the pulse sequence
                self.__analyse(self.__sequence)
                self.__sequence.clear()
                continue        # Skip to the next pulse

            # Otherwise, convert the count pair into a pulse and add it to the sequence
            pulse = Pulse(count_to_burst_us((count_pair >> 16) & 0xffff),
                          count_to_idle_us(count_pair & 0xffff))
            self.__sequence.append(pulse)

    def decode(self, filter_threshold=DEFAULT_FILTER_THRESHOLD):   # with filter
        """
        Checks for any newly received pulses since the last time `decode` was
        called. Once a sufficient number of pulses has been received, as
        indicated by the PIO program's timeout being reached, the pulses are
        passed to an overridable `__analyse` function to act on any data.

        This should be called frequently from user code to avoid pulses
        queuing up and making remote button presses feel sluggish.

        This function includes a low-pass filter to removes any "blips" in
        received pulses to recover data that may otherwise be discarded.
        """

        if not self.__sm.active():
            raise RuntimeError("Cannot decode IR signals. Check that you have called `.start()` on the receiver first.")

        # Go through all counts currently stored
        while len(self.__counts) > 0:
            count_pair = self.__counts.popleft()   # Extract the oldest count pair

            # Did the count timeout get reached?
            if count_pair == TIMEOUT_REACHED:
                # If there is one, add the last pulse to the pulse sequence to finish it off
                if self.__last_pulse is not None:
                    self.__sequence.append(self.__last_pulse)
                    self.__last_pulse = None

                # Analyse, and clear the pulse sequence
                self.__analyse(self.__sequence)
                self.__sequence.clear()
                continue        # Skip to the next pulse

            # Otherwise, convert the count pair into a pulse
            current_pulse = Pulse(count_to_burst_us((count_pair >> 16) & 0xffff),
                                  count_to_idle_us(count_pair & 0xffff))

            # Is this the first pulse we've received in this sequence?
            if self.__last_pulse is None:
                self.__last_pulse = current_pulse   # Save it for later
                continue        # Skip to the next pulse

            last_burst, last_idle = self.__last_pulse   # For convenience

            # Was the idle of the last pulse below the filter threshold?
            if last_idle < filter_threshold:
                self.__debug_blip_pin.on()      # Show that a blip was detected

                # Filter out the blip by merging the last pulse into the burst of the current pulse, updating the last pulse
                self.__last_pulse = Pulse(
                    current_pulse.burst + last_burst + last_idle,
                    current_pulse.idle      # Idle is unchanged
                )

                self.__debug_blip_pin.off()     # Show that a blip was handled
                continue        # Skip to the next pulse

            # Was the burst of the current pulse below the filter threshold?
            if current_pulse.burst < filter_threshold:
                self.__debug_blip_pin.on()      # Show that a blip was detected

                # Filter out the blip by merging the current pulse into the idle of the last pulse, updating the last pulse
                self.__last_pulse = Pulse(
                    last_burst,     # Burst is unchanged
                    last_idle + current_pulse.burst + current_pulse.idle
                )

                self.__debug_blip_pin.off()     # Show that a blip was handled
                continue        # Skip to the next pulse

            # The last pulse is now valid, so add it to the pulse sequence, and update the last pulse
            self.__sequence.append(self.__last_pulse)
            self.__last_pulse = current_pulse
