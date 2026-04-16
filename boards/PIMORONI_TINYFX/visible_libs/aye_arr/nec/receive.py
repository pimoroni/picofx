# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import time

from machine import Pin

import aye_arr.logging as logging

from ..pulse.common import DebugPin
from ..pulse.receive import DEFAULT_FILTER_THRESHOLD, PulseReceiver
from .common import NEC_DATA_BURST_US, NEC_DATA_ONE_US, NEC_DATA_ZERO_US, NEC_REPEAT, NEC_REPEAT_TIMEOUT_MS, NEC_START_BURST_US, NEC_START_DATA_US, NEC_START_REPEAT_US, pulse_us_valid
from .remotes import KNOWN_REMOTES


# Function for performing callbacks with parameters and optional arguments
def perform_callback(callback, *args):
    # Extract the callback function and any parameters for it
    if isinstance(callback, (tuple, list)):
        func, *params = callback
    else:
        func, params = callback, []

    try:
        # Attempt to call the function with additional args
        return func(*params, *args)
    except TypeError as e:
        # Ignore the TypeError if it was caused by the additional args
        if not str(e).startswith("function takes "):
            raise

    # Fall back to calling the function without additional args
    return func(*params)


class NECReceiver(PulseReceiver):
    def __init__(self, pin_num, pio, sm,
                 debug_pin_base=None, debug_blip_pin=None, debug_error_pin=None,
                 logging_level=logging.LOG_WARN):
        self.__last_code = NEC_REPEAT
        self.__received_ms = time.ticks_ms()
        self.__last_code_ms = self.__received_ms

        self.__press_callback = None
        self.__repeat_callback = None
        self.__release_callback = None

        logging.level = logging_level
        super().__init__(pin_num, pio, sm, debug_pin_base, debug_blip_pin)

        # Set up debug pin for scoping
        self.__debug_error_pin = DebugPin(debug_error_pin, Pin.OUT)

    def bind(self, on_press, on_repeat=True, on_release=None):
        self.__press_callback = on_press
        self.__repeat_callback = on_press if on_repeat is True else on_repeat
        self.__release_callback = on_release

    def start(self):
        super().start()
        logging.warn("--- IR receiver started ---")

    def stop(self):
        super().stop()
        logging.warn("--- IR receiver stopped ---")

    def reset(self):
        self.__last_code = NEC_REPEAT
        self.__received_ms = time.ticks_ms()
        self.__last_code_ms = self.__received_ms
        super().reset()

    def __extract_code(self, pulses):
        while len(pulses) > 0:
            pulse = pulses[0]

            # Is the first pulse a repeat and are there no other pulses?
            if pulse_us_valid(pulse.burst, NEC_START_BURST_US) and \
               pulse_us_valid(pulse.idle, NEC_START_REPEAT_US) and \
               len(pulses) == 1:
                return NEC_REPEAT

            # Is the first pulse an invalid start?
            if not pulse_us_valid(pulse.burst, NEC_START_BURST_US) and \
               not pulse_us_valid(pulse.idle, NEC_START_DATA_US):
                self.__debug_error_pin.on()
                logging.debug(f"Invalid Start [{pulse.burst}, {pulse.idle}], Exp: {NEC_START_BURST_US} then {NEC_START_DATA_US} or {NEC_START_REPEAT_US}")
                del pulses[0]
                self.__debug_error_pin.off()
                continue        # Skip to the next pulse

            # Are there fewer pulses than a full code requires?
            if len(pulses) < 33:
                return None     # No code was extracted

            # Go through the rest of the pulses and extract the code
            code = 0
            for i in range(1, 33):
                pulse = pulses[i]

                # Does the full pulse length (of the burst and idle combined) match a `Zero`?
                if pulse_us_valid(pulse.burst + pulse.idle,
                                  NEC_DATA_BURST_US + NEC_DATA_ZERO_US):
                    continue    # Skip to the next data pulse

                # Does the full pulse length (of the burst and idle combined) match a `One`?
                if pulse_us_valid(pulse.burst + pulse.idle,
                                  NEC_DATA_BURST_US + NEC_DATA_ONE_US):
                    code |= (1 << (i - 1))      # Add a 1 at the relevant bit position
                    continue    # Skip to the next data pulse

                self.__debug_error_pin.on()
                logging.debug(f"Invalid Data [{pulse.burst}, {pulse.idle}], Exp {NEC_DATA_BURST_US} then {NEC_DATA_ONE_US} or {NEC_DATA_ZERO_US}")
                self.__debug_error_pin.off()
                return None     # No code was extracted

            return code     # A complete code was extracted

        return None     # No code was extracted

    def decode_no_filter(self):
        self.__check_repeat_timeout()
        super().decode_no_filter()

    def decode(self, filter_threshold=DEFAULT_FILTER_THRESHOLD):   # with filter
        self.__check_repeat_timeout()
        super().decode(filter_threshold)

    def __check_repeat_timeout(self):
        # Expire our last code if it was received too long ago and isn't a repeat
        current_ms = time.ticks_ms()
        if time.ticks_diff(current_ms, self.__received_ms) > NEC_REPEAT_TIMEOUT_MS and \
           self.__last_code != NEC_REPEAT:
            logging.info(f"Last code 0x{self.__last_code:08x} expired")

            # Perform the general release action for the last code, if any
            self.__on_release(self.__last_code, current_ms, self.__last_code_ms)

            self.__last_code = NEC_REPEAT

    def __analyse(self, pulses):
        # Attempt to extract a code from the received pulses
        code = self.__extract_code(pulses)

        # Was a code was extracted?
        if code is not None:
            # Record the time of this new code
            self.__received_ms = time.ticks_ms()

            # Was the code a repeat?
            if code == NEC_REPEAT:
                if self.__last_code != NEC_REPEAT:
                    logging.info(f"Repeat received, loading code 0x{self.__last_code:08x}")

                # Perform the general repeat action for the last code, if any
                self.__on_repeat(self.__last_code, self.__received_ms, self.__last_code_ms)
                return

            self.__on_release(self.__last_code, self.__received_ms, self.__last_code_ms)

            logging.info(f"Code received, 0x{code:08x}")

            # Perform the general press action for the new code, if any
            self.__on_press(code, self.__received_ms, self.__last_code_ms)

            # Update the last variables
            self.__last_code = code
            self.__last_code_ms = self.__received_ms

    def __on_release(self, code, ms, last_press_ms):
        if self.__release_callback is not None:
            perform_callback((self.__release_callback, code), ms, last_press_ms)

    def __on_repeat(self, code, ms, last_press_ms):
        if self.__repeat_callback is not None:
            perform_callback((self.__repeat_callback, code), ms, last_press_ms)

    def __on_press(self, code, ms, last_press_ms):
        if self.__press_callback is not None:
            perform_callback((self.__press_callback, code), ms, last_press_ms)


class NECRemoteReceiver(NECReceiver):
    SHORT_RELEASE_MS = 250

    def __init__(self, pin_num, pio, sm, extended_addresses=False,
                 debug_pin_base=None, debug_blip_pin=None, debug_error_pin=None,
                 logging_level=logging.LOG_WARN):
        self.__remotes = {}
        self.__extended = extended_addresses
        self.__repeat_callbacks = []
        self.__release_callbacks = []
        self.__short_callbacks = []
        super().__init__(pin_num, pio, sm, debug_pin_base, debug_blip_pin, debug_error_pin, logging_level)

    def bind(self, remote_descriptor, force=False):
        addr = remote_descriptor.ADDRESS
        if addr in self.__remotes:
            if not force:
                raise ValueError(f"A remote with the address '0x{addr:0x}' is already bound. Use a different address, or append with 'force=True'")
            self.__remotes[addr].append(remote_descriptor)
        else:
            self.__remotes[addr] = [remote_descriptor]

    def __on_release(self, _, ms, last_press_ms):
        if len(self.__short_callbacks) > 0:
            # Perform the short release actions of the last command, if any
            for callback in self.__short_callbacks:
                perform_callback(callback, ms, last_press_ms)
        else:
            # Perform the release actions of the last command, if any
            for callback in self.__release_callbacks:
                perform_callback(callback, ms, last_press_ms)

        # Clear out the callback lists
        self.__repeat_callbacks.clear()
        self.__release_callbacks.clear()
        self.__short_callbacks.clear()

    def __on_repeat(self, _, ms, last_press_ms):
        if len(self.__short_callbacks) == 0 or \
           time.ticks_diff(ms, last_press_ms) > self.SHORT_RELEASE_MS:
            # A repeat was encountered so clear out any short release callbacks
            self.__short_callbacks.clear()

            # Perform the repeat actions of the last command, if any
            for callback in self.__repeat_callbacks:
                perform_callback(callback, ms, last_press_ms)

    def __on_press(self, code, ms, last_press_ms):
        # Extract the address from the code, optionally supporting extended addresses
        addr = code & 0xff          # 8 bit address
        if addr != ((code >> 8) ^ 0xff) & 0xff:
            if not self.__extended:
                logging.warn(f"Address check failed: 0x{addr:02x} != 0x{((code >> 8) ^ 0xff) & 0xff:02x}")
                return
            addr |= code & 0xff00

        # Extract the command from the code
        cmd = (code >> 16) & 0xff
        if cmd != (code >> 24) ^ 0xff:
            logging.warn(f"Command check failed: 0x{cmd:02x} != 0x{(code >> 24) ^ 0xff:02x}, Addr: {addr:02x}")
            return

        # Does the address match one of the bound remotes?
        if addr in self.__remotes:
            # Go through all the bound remotes with the address
            known = False
            for remote in self.__remotes[addr]:
                # Perform the general callback for any command received
                if remote.on_any is not None:
                    known = True if perform_callback((remote.on_any, cmd), ms, last_press_ms) else known

                # Perform the callback only for known commands that are received
                if remote.on_known is not None:
                    for key, val in remote.BUTTON_CODES.items():
                        if val == cmd:
                            known = True if perform_callback((remote.on_known, key), ms, last_press_ms) else known
                            break

                try:
                    # Attempt to get the button associated with the command
                    # Raises a KeyError if it fails
                    button = remote.button(cmd)

                    # At least one bound remote has this button
                    known = True

                    if logging.level >= logging.LOG_WARN:
                        for key, val in remote.BUTTON_CODES.items():
                            if val == cmd:
                                print(f"'{key}' (0x{cmd:02x}) received from bound remote `{remote.NAME}` (0x{addr:02x})")

                    # Perform the press action of the bound button, if present
                    if button.on_press is not None:
                        perform_callback(button.on_press, ms, last_press_ms)

                    # Queue up the repeat action of the bound button, if present
                    if button.on_repeat is not None:
                        self.__repeat_callbacks.append(button.on_repeat)

                    # Queue up the release action of the bound button, if present
                    if button.on_release is not None:
                        self.__release_callbacks.append(button.on_release)

                    # Queue up the short release action of the bound button, if present
                    if button.on_short is not None:
                        self.__short_callbacks.append(button.on_short)

                except KeyError:
                    pass

            # None of the bound remotes had a button binding for the command
            if not known and logging.level >= logging.LOG_WARN:
                for remote in self.__remotes[addr]:
                    print(f"Unknown command (0x{cmd:02x}) received from bound remote `{remote.NAME}` (0x{addr:02x}). ", end="")

                    # Suggest which remote command it may be
                    keys = [key for key, val in remote.BUTTON_CODES.items() if val == cmd]
                    if len(keys) == 1:
                        print(f"Likely '{keys[0]}'")
                    else:
                        print("No known command")

        # The address does not match one of the bound remotes
        elif logging.level >= logging.LOG_WARN:
            print(f"Unknown code (Addr 0x{addr:02x}, Cmd 0x{cmd:02x}) received. ", end="")

            # Suggest which remote command it may be
            known = False
            for remote in KNOWN_REMOTES:
                if remote.ADDRESS == addr:
                    print(", or " if known else "Likely from ", end="")

                    known = True
                    keys = [key for key, val in remote.BUTTON_CODES.items() if val == cmd]
                    if len(keys) == 1:
                        print(f"'{remote.NAME}.{keys[0]}'", end="")
                    else:
                        print(f"'{remote.NAME}' remote", end="")

            print("" if known else "No known remote")
