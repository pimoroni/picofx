# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from machine import Pin, PWM, Timer


# A basic wrapper for PWM with regular on/off and toggle functions from Pin
# Intended to be used for driving LEDs with brightness control & compatibility with Pin
class PWMLED:
    def __init__(self, pin, invert=False, gamma=1):
        self._gamma = gamma
        self._led = PWM(Pin(pin), freq=1000, duty_u16=0, invert=invert)

    def brightness(self, brightness):
        brightness = min(1.0, max(0.0, brightness))
        self._brightness = brightness
        self._led.duty_u16(int(pow(brightness, self._gamma) * 65535 + 0.5))

    def on(self):
        self.brightness(1)

    def off(self):
        self.brightness(0)

    def toggle(self):
        self.brightness(1 - self._brightness)


class RGBLED:
    def __init__(self, r, g, b, invert=True, gamma=1):
        self._gamma = gamma
        self.led_r = PWM(Pin(r), freq=1000, duty_u16=0, invert=invert)
        self.led_g = PWM(Pin(g), freq=1000, duty_u16=0, invert=invert)
        self.led_b = PWM(Pin(b), freq=1000, duty_u16=0, invert=invert)

    def _rgb(self, r, g, b):
        self.led_r.duty_u16(int(pow(r, self._gamma) * 65535 + 0.5))
        self.led_g.duty_u16(int(pow(g, self._gamma) * 65535 + 0.5))
        self.led_b.duty_u16(int(pow(b, self._gamma) * 65535 + 0.5))

    def set_rgb(self, r, g, b):
        r = min(255, max(0, r))
        g = min(255, max(0, g))
        b = min(255, max(0, b))
        self._rgb(r / 255, g / 255, b / 255)

    def set_hsv(self, h, s, v):
        if s == 0.0:
            self._rgb(v, v, v)
        else:
            i = int(h * 6.0)
            f = (h * 6.0) - i
            p, q, t = v * (1.0 - s), v * (1.0 - s * f), v * (1.0 - s * (1.0 - f))

            i = i % 6
            if i == 0:
                self._rgb(v, t, p)
            elif i == 1:
                self._rgb(q, v, p)
            elif i == 2:
                self._rgb(p, v, t)
            elif i == 3:
                self._rgb(p, q, v)
            elif i == 4:
                self._rgb(t, p, v)
            elif i == 5:
                self._rgb(v, p, q)


class Updatable:
    def __init__(self, speed):
        self.speed = speed

    def tick(self, delta_ms):
        pass

    def reset(self):
        pass


class Cycling(Updatable):
    def __init__(self, speed):
        super().__init__(speed)
        self.__offset_ms = 0
        self.__offset = 0

    def tick(self, delta_ms):
        self.__offset_ms = (self.__offset_ms + int(delta_ms * self.speed)) % 1000
        self.__offset = self.__offset_ms / 1000

    def reset(self):
        self.__offset_ms = 0
        self.__offset = 0


class EffectPlayer:
    DEFAULT_FPS = 100

    def __init__(self, leds, num_leds=None):
        self.__leds = leds if isinstance(leds, (tuple, list)) else [leds]
        self.__num_leds = len(self.__leds) if num_leds is None else num_leds

        self.__effects = [None] * self.__num_leds
        self.__data = [()] * self.__num_leds
        self.__updatables = set()

        self.__period = 1000
        self.__timer = Timer()
        self.__paired = None
        self.__running = False

    def start(self, fps=DEFAULT_FPS, force=False):
        if not self.is_running() or force:
            self.stop()

            self.__period = int(1000 / fps)
            if self.__paired is not None:
                self.__paired.__period = self.__period

            self.__timer.init(mode=Timer.PERIODIC, period=self.__period, callback=self.__update)
            self.__running = True

    def stop(self, reset_fx=False):
        self.__timer.deinit()
        self.__running = False
        if reset_fx:
            for ufx in self.__updatables:
                ufx.reset()

    def is_running(self):
        return self.__running

    def __show(self):
        pass

    def pair(self, player):
        self.__paired = player

    def __update(self, timer):
        for ufx in self.__updatables:
            ufx.tick(self.__period)

        try:
            self.__show()

            if self.__paired is not None:
                self.__paired.__update(timer)
        except Exception as e:
            self.stop()
            raise e

    @property
    def effects(self):
        return tuple(self.__effects)

    @effects.setter
    def effects(self, effect_list):
        effect_list = effect_list if isinstance(effect_list, list) else [effect_list] * self.__num_leds

        if len(effect_list) > self.__num_leds:
            raise ValueError(f"`effect_list` must have a length less or equal to {self.__num_leds}")

        self.__updatables = set()
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

                # Is the effect an Updatable class too?
                if isinstance(item, Updatable):
                    self.__updatables.add(item)     # Add it to the updatables set

            # Is the item a tuple?
            elif isinstance(item, tuple):
                first, *rest = item

                # Is the first element an Updatable class?
                if isinstance(first, Updatable):
                    self.__updatables.add(first)    # Add it to the updatables set

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
        if len(effect_list) < self.__num_leds:
            for i in range(len(effect_list), self.__num_leds):
                self.__effects[i] = None
                self.__data[i] = ()


class MonoPlayer(EffectPlayer):
    def __init__(self, mono_leds):
        super().__init__(mono_leds)

    def __show(self):
        try:
            for i in range(self.__num_leds):
                if self.__effects[i] is not None:
                    self.__leds[i].brightness(self.__effects[i](*self.__data[i]))
        except Exception:
            raise TypeError("Incorrect effect setup for this MonoPlayer")


class ColourPlayer(EffectPlayer):
    def __init__(self, rgb_leds):
        super().__init__(rgb_leds)

    def __show(self):
        try:
            for i in range(self.__num_leds):
                if self.__effects[i] is not None:
                    self.__leds[i].set_rgb(*self.__effects[i](*self.__data[i]))
        except Exception:
            raise TypeError("Incorrect effect setup for this ColourPlayer")


class StripPlayer(EffectPlayer):
    def __init__(self, rgb_leds, num_leds=60):
        super().__init__(rgb_leds, num_leds)

    def __show(self):
        try:
            for i in range(self.__num_leds):
                if self.__effects[i] is not None:
                    colours = self.__effects[i](*self.__data[i])
                    if not isinstance(colours, tuple):
                        colours = [int(colours * 255)] * 3

                    self.__leds.set_rgb(i, *colours)
        except Exception:
            raise TypeError("Incorrect effect setup for this StripPlayer")
