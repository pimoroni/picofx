# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from machine import Pin, PWM, Timer


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


# A basic wrapper for PWM with regular on/off and toggle functions from Pin
# Intended to be used for driving LEDs with brightness control & compatibility with Pin
class PWMLED:
    def __init__(self, pin, invert=False, gamma=1):
        self.__gamma = gamma
        self.__led = PWM(Pin(pin), freq=1000, duty_u16=0, invert=invert)

    def brightness(self, brightness):
        self.__brightness = min(1.0, max(0.0, brightness))
        self.__led.duty_u16(int(pow(self.__brightness, self.__gamma) * 65535 + 0.5))

    def on(self):
        self.brightness(1)

    def off(self):
        self.brightness(0)

    def toggle(self):
        self.brightness(1 - self.__brightness)


class RGBLED:
    def __init__(self, r, g, b, invert=True, gamma=1):
        self.led_r = r if isinstance(r, PWMLED) else PWMLED(r, invert=invert, gamma=gamma)
        self.led_g = g if isinstance(g, PWMLED) else PWMLED(g, invert=invert, gamma=gamma)
        self.led_b = b if isinstance(b, PWMLED) else PWMLED(b, invert=invert, gamma=gamma)

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


class EffectPlayer:
    DEFAULT_FPS = 100

    def __init__(self, leds, num_leds=None):
        self.__leds = leds if isinstance(leds, (tuple, list)) else [leds]
        self.__num_leds = len(self.__leds) if num_leds is None else num_leds

        self.__effects = [None] * self.__num_leds
        self.__data = [()] * self.__num_leds
        self.__updateables = set()

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
            for ufx in self.__updateables:
                ufx.reset()

    def is_running(self):
        return self.__running

    def __show(self):
        pass

    def pair(self, player):
        self.__paired = player

    def __update(self, timer):
        try:
            for ufx in self.__updateables:
                ufx.tick(self.__period)

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
        if len(effect_list) < self.__num_leds:
            for i in range(len(effect_list), self.__num_leds):
                self.__effects[i] = None
                self.__data[i] = ()


class MonoPlayer(EffectPlayer):
    def __init__(self, mono_leds):
        super().__init__(mono_leds)

    def __show(self):
        for i in range(self.__num_leds):
            if self.__effects[i] is not None:
                self.__leds[i].brightness(self.__effects[i](*self.__data[i]))


class ColourPlayer(EffectPlayer):
    def __init__(self, rgb_leds):
        super().__init__(rgb_leds)

    def __show(self):
        for i in range(self.__num_leds):
            if self.__effects[i] is not None:
                colours = self.__effects[i](*self.__data[i])
                if not isinstance(colours, tuple):
                    colours = [int(colours * 255)] * 3

                self.__leds[i].set_rgb(*colours)


class StripPlayer(EffectPlayer):
    def __init__(self, rgb_leds, num_leds=60):
        super().__init__(rgb_leds, num_leds)

    def __show(self):
        for i in range(self.__num_leds):
            if self.__effects[i] is not None:
                colours = self.__effects[i](*self.__data[i])
                if not isinstance(colours, tuple):
                    colours = [int(colours * 255)] * 3

                self.__leds.set_rgb(i, *colours)
