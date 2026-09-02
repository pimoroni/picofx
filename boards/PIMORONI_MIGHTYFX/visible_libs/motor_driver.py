# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# The motor driver on one SP/CE connector: the two motors its four data pins drive,
# and the power they share on the connector's fifth. Built against a port declared
# SPCE.MOTOR_DRIVER, as a screen is against a screen port, so any SP/CE host drives
# motors the same way and the board class carries nothing for it.

from machine import Pin


class MotorDriver:
    """
    Two motors and the power they share, built on a port declared SPCE.MOTOR_DRIVER.

    The driver starts unpowered, so a board coming up drives nothing that is already
    wired to it. enable() is what makes the outputs live.
    """

    def __init__(self, port):
        from motor import Motor

        motor_pins, enable_pin = port.motor_pins

        # Named as the driver prints them, and the same pair as a sequence, so a
        # program that drives both walks them and one that drives a single names it
        self.motor_a = Motor(motor_pins[0])
        self.motor_b = Motor(motor_pins[1])
        self.motors = (self.motor_a, self.motor_b)

        self.__enable = Pin(enable_pin, Pin.OUT, value=False)

        # What disable() stopped, so enable() puts back what was running rather than
        # the pair a board came up with
        self.__driving = ()

        # On the port, so a shutdown can stop motors it did not build
        port.driver = self

    def enable(self):
        """Power the driver, and put back whatever disable() stopped."""
        self.__enable.on()
        for motor in self.__driving:
            motor.enable()
        self.__driving = ()

    def disable(self):
        """
        Stop both motors and take the power off the driver.

        The motors stop as well as the power going, because the pins they drive are
        the driver's direction indicators too: cutting the power alone leaves those
        lit, showing a motor being driven that cannot turn.
        """
        self.__driving = tuple(motor for motor in self.motors if motor.is_enabled())
        for motor in self.motors:
            motor.disable()

        self.__enable.off()

    def is_enabled(self):
        """Whether the driver is powered."""
        return self.__enable.value() == 1
