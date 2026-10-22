# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from machine import Pin

# The roles the sensor connector can take, passed to a board as sensor=. The connector
# carries one signal, so a board takes one of these at a time.
ANALOG = "analog"   # An analog sensor, read as a voltage through pimoroni's Analog
PIR = "pir"         # A motion sensor, read as a level through a pulled-up input
IR = "ir"           # The infrared receiver, decoded by aye_arr on a state machine the board picks

ROLES = (ANALOG, PIR, IR)


def build_sensor(role, pin, pio, sm):
    """
    Build what the connector was declared as on its pin, or None for no role. A receiver
    is started here, holding its state machine until the board shuts down.
    """
    # No role claims nothing, leaving the pin free for anything wired to the connector
    if role is None:
        return None

    if role == ANALOG:
        from pimoroni import Analog
        return Analog(Pin(pin))

    if role == PIR:
        return Pin(pin, Pin.IN, Pin.PULL_UP)

    if role == IR:
        from aye_arr.nec import NECRemoteReceiver
        built = NECRemoteReceiver(pin, pio, sm)
        built.start()
        return built

    raise ValueError(f"'{role}' is not a sensor role. Pass sensor=ANALOG, sensor=PIR or sensor=IR, imported from sensor")
