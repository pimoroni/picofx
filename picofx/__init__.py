# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import time
from machine import PWM, Pin, Timer

PICOFX_VERSION = "1.1.3"


def rgb_from_hsv(h, s, v):
    if s == 0.0:
        return v, v, v
    else:
        i = int(h * 6.0)
        f = (h * 6.0) - i
        p, q, t = v * (1.0 - s), v * (1.0 - s * f), v * (1.0 - s * (1.0 - f))

        i = i % 6
        if i == 0:
            return v, t, p
        elif i == 1:
            return q, v, p
        elif i == 2:
            return p, v, t
        elif i == 3:
            return p, q, v
        elif i == 4:
            return t, p, v
        elif i == 5:
            return v, p, q


# A pseudo LED class for storing brightness. For use in comms
class PseudoLED:
    # None when the LED is free to light, otherwise the reason it cannot
    in_use_by = None

    def __init__(self):
        self.__brightness = 0

    def brightness(self, brightness):
        self.__brightness = min(1.0, max(0.0, brightness))

    def on(self):
        self.brightness(1)

    def off(self):
        self.brightness(0)

    def toggle(self):
        self.brightness(1 - self.__brightness)


# A basic wrapper for PWM with regular on/off and toggle functions from Pin
# Intended to be used for driving LEDs with brightness control & compatibility with Pin
class PWMLED(PseudoLED):
    FREQUENCY = 1000

    def __init__(self, pin, invert=False, gamma=1):
        super().__init__()
        self.__gamma = gamma
        self.__led = PWM(Pin(pin), freq=self.FREQUENCY, duty_u16=0, invert=invert)

    def brightness(self, brightness):
        super().brightness(brightness)
        self.__led.duty_u16(int(pow(self.__brightness, self.__gamma) * 65535 + 0.5))

    def on(self):
        self.brightness(1)

    def off(self):
        self.brightness(0)

    def toggle(self):
        self.brightness(1 - self.__brightness)


# A stand-in for an LED whose pin or PWM channel another function holds.
# Turning it off works, so board-wide clear() and shutdown() pass through.
# The first attempt to light it prints the reason; it stays dark throughout.
class DisabledLED(PseudoLED):
    def __init__(self, reason):
        super().__init__()
        self.in_use_by = reason
        self.__warned = False

    def brightness(self, brightness):
        if brightness > 0 and not self.__warned:
            print(self.in_use_by)
            self.__warned = True
        super().brightness(brightness)


class RGBLED:
    def __init__(self, r, g, b, invert=True, gamma=1):
        self.led_r = r if isinstance(r, PseudoLED) else PWMLED(r, invert=invert, gamma=gamma)
        self.led_g = g if isinstance(g, PseudoLED) else PWMLED(g, invert=invert, gamma=gamma)
        self.led_b = b if isinstance(b, PseudoLED) else PWMLED(b, invert=invert, gamma=gamma)

        # The same three as a sequence, so they can be indexed and iterated
        self.leds = (self.led_r, self.led_g, self.led_b)

    def __rgb(self, r, g, b):
        self.led_r.brightness(r)
        self.led_g.brightness(g)
        self.led_b.brightness(b)

    def set_rgb(self, r, g, b):
        self.__rgb(r / 255, g / 255, b / 255)

    def set_hsv(self, h, s, v):
        self.__rgb(*rgb_from_hsv(h, s, v))


class Updateable:
    def __init__(self):
        pass

    def tick(self, delta_ms):
        pass

    def reset(self):
        pass


class Cycling(Updateable):
    def __init__(self, speed):
        self.speed = speed
        self.__offset_ms = 0
        self.__offset = 0

    def tick(self, delta_ms):
        self.__offset_ms = (self.__offset_ms + int(delta_ms * self.speed)) % 1000
        self.__offset = self.__offset_ms / 1000

    def reset(self):
        self.__offset_ms = 0
        self.__offset = 0


class CyclingAction(Updateable):
    def __init__(self, speed):
        self.speed = speed
        self.__offset_ms = 0
        self.__offset = 0

    def next(self):
        pass

    def prev(self):
        pass

    def tick(self, delta_ms):
        self.__offset_ms += int(delta_ms * self.speed)
        if self.__offset_ms >= 1000:
            self.__offset_ms -= 1000
            self.next()
        elif self.__offset_ms < 0:
            self.__offset_ms += 1000
            self.prev()

        self.__offset = self.__offset_ms / 1000

    def reset(self):
        self.__offset_ms = 0
        self.__offset = 0


class EffectPlayer:
    DEFAULT_FPS = 100

    def __init__(self, leds, num_leds=None):
        if num_leds is None:
            self.__leds = leds if isinstance(leds, (tuple, list)) else [leds]
            self.__num_leds = len(self.__leds)
        else:
            self.__leds = leds
            self.__num_leds = num_leds

        self.__effects = [None] * self.__num_leds
        self.__data = [()] * self.__num_leds
        self.__updateables = set()

        # A per channel scale on the output of an effect
        self.__levels = [1.0] * self.__num_leds

        self.__period = 1000
        self.__timer = Timer()
        self.__paired = None
        self.__running = False
        self.__last = time.ticks_ms()
        self.__measured = 0

    def start(self, fps=DEFAULT_FPS, force=False):
        if not self.is_running() or force:
            self.stop()

            self.__period = int(1000 / fps)
            if self.__paired is not None:
                self.__paired.__period = self.__period

            self.__last = time.ticks_ms()
            self.__timer.init(mode=Timer.PERIODIC, period=self.__period, callback=self.__update)
            self.__running = True

    def stop(self, reset_fx=False):
        self.__running = False
        self.__timer.deinit()
        if reset_fx:
            for ufx in self.__updateables:
                ufx.reset()

    def is_running(self):
        return self.__running

    def __show(self):
        pass

    def pair(self, player):
        self.__paired = player

    def target_ms(self):
        return self.__period

    def measured_ms(self):
        return self.__measured

    def target_fps(self):
        return 1000 / self.__period

    def measured_fps(self):
        return 1000 / self.__measured if self.__measured > 0 else float("inf")

    def __update(self, timer):
        # Timer callbacks arrive via the scheduler, so one already in-flight
        # at deinit can still run after stop() and must not update the LEDs
        if self.__running:
            self.__tick(timer)

    def __tick(self, timer):
        try:
            for ufx in self.__updateables:
                ufx.tick(self.__period)

            self.__show()

            if self.__paired is not None:
                self.__paired.__tick(timer)
        except BaseException as e:
            self.stop()
            raise e

        now = time.ticks_ms()
        self.__measured = time.ticks_diff(now, self.__last)
        self.__last = now

    @property
    def effects(self):
        return tuple(self.__effects)

    @effects.setter
    def effects(self, effect_list):
        effect_list = self.__to_channel_list(effect_list, "effect_list")

        self.__updateables = set()
        for i, item in enumerate(effect_list):
            self.__effects[i] = None
            self.__data[i] = ()

            # Skip the item if it is none
            if item is None:
                continue

            # Is the item on its own and callable?
            if callable(item):
                # It must therefore be an effect function
                self.__effects[i] = item

                # Is the effect an Updateable class too?
                if isinstance(item, Updateable):
                    self.__updateables.add(item)    # Add it to the updateables set

            # Is the item a tuple?
            elif isinstance(item, tuple):
                first, *rest = item

                # Is the first element an Updateable class?
                if isinstance(first, Updateable):
                    self.__updateables.add(first)   # Add it to the updateables set

                    # Are there are other elements, and is the second element callable?
                    if rest and callable(rest[0]):
                        # Assume the effect function is the second element, and the first is its parent class. All elements that follow are data
                        self.__effects[i] = rest[0]
                        self.__data[i] = tuple(rest[1:])
                    else:
                        # The first element is both the effect function and Updateable class. All elements that follow are data
                        self.__effects[i] = first
                        self.__data[i] = tuple(rest)

                # Is the first element only callable?
                elif callable(first):
                    # It must therefore be an effect function. All elements that follow are data
                    self.__effects[i] = first
                    self.__data[i] = tuple(rest)

        # Clear out excess effects
        for i in range(len(effect_list), self.__num_leds):
            self.__effects[i] = None
            self.__data[i] = ()

    def __to_channel_list(self, values, name):
        # Passes a list of values through or applies one value for every channel
        values = values if isinstance(values, list) else [values] * self.__num_leds

        if len(values) > self.__num_leds:
            raise ValueError(f"`{name}` must have a length less or equal to {self.__num_leds}")

        return values

    @property
    def levels(self):
        return tuple(self.__levels)

    @levels.setter
    def levels(self, levels):
        levels = self.__to_channel_list(levels, "levels")

        for i, level in enumerate(levels):
            self.__levels[i] = min(1.0, max(0.0, level))

        # Reset excess levels
        for i in range(len(levels), self.__num_leds):
            self.__levels[i] = 1.0


class MonoPlayer(EffectPlayer):
    def __init__(self, mono_leds):
        super().__init__(mono_leds)

    def __show(self):
        for i in range(self.__num_leds):
            if self.__effects[i] is not None:
                self.__leds[i].brightness(self.__effects[i](*self.__data[i]) * self.__levels[i])


class ChromaticPlayer(EffectPlayer):
    """
    Shared by the players whose channels can show a colour. Holds the tint a mono
    effect is drawn in, which a mono channel has no use for.
    """
    def __init__(self, leds, num_leds=None):
        super().__init__(leds, num_leds)
        self.__colours = [(255, 255, 255)] * self.__num_leds

    @property
    def colours(self):
        return tuple(self.__colours)

    @colours.setter
    def colours(self, colours):
        colours = self.__to_channel_list(colours, "colours")

        for i, colour in enumerate(colours):
            if not isinstance(colour, (tuple, list)) or len(colour) != 3:
                raise TypeError("each colour must be a tuple of three numbers")

            self.__colours[i] = tuple(min(255, max(0, c)) for c in colour)

        # Reset excess colours
        for i in range(len(colours), self.__num_leds):
            self.__colours[i] = (255, 255, 255)


class ColourPlayer(ChromaticPlayer):
    def __init__(self, rgb_leds):
        super().__init__(rgb_leds)

    def __show(self):
        for i in range(self.__num_leds):
            if self.__effects[i] is not None:
                value = self.__effects[i](*self.__data[i])
                level = self.__levels[i]

                if isinstance(value, tuple):
                    # A colour effect brings its own colour, so only the level applies
                    self.__leds[i].set_rgb(value[0] * level, value[1] * level, value[2] * level)
                else:
                    # A mono effect gives a 0.0 to 1.0 level to scale the channel's colour by
                    value *= level
                    r, g, b = self.__colours[i]
                    self.__leds[i].set_rgb(r * value, g * value, b * value)


class StripPlayer(ChromaticPlayer):
    def __init__(self, led_strip, num_leds=60):
        super().__init__(led_strip, num_leds)

    def __show(self):
        for i in range(self.__num_leds):
            if self.__effects[i] is not None:
                value = self.__effects[i](*self.__data[i])
                level = self.__levels[i]

                if isinstance(value, tuple):
                    r, g, b = (c * level for c in value)
                else:
                    value *= level
                    r, g, b = (c * value for c in self.__colours[i])

                # The strip is driven through a C binding, which wants whole numbers
                self.__leds.set_rgb(i, int(r), int(g), int(b))
