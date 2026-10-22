# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import time
from collections import namedtuple

from machine import PWM, Pin, Timer

PICOFX_VERSION = "1.1.3"

# An eased curve halves its distance this many times over its length, which looks
# arrived on a lit output, so it finishes with a fade of the same length
SETTLE = 6


# How a channel moves to what its effect asks for. rise and fall are the seconds each
# way, and straight is whether it crosses at a steady rate or eases in
Curve = namedtuple("Curve", ("rise", "fall", "straight"))


def ease(rise, fall=None):
    """A curve that settles into place, as a warming filament does."""
    return Curve(rise, rise if fall is None else fall, False)


def fade(rise, fall=None):
    """A curve that crosses at a steady rate, arriving in the length it is given."""
    return Curve(rise, rise if fall is None else fall, True)


def rgb_from_hsv(h, s, v):
    if s == 0.0:
        return v, v, v

    sixth = h * 6.0
    i = int(sixth)
    f = sixth - i

    # Each sixth shows the darkest mix and one of the two that travel, never both,
    # so only the shared one is calculated ahead of the branch
    p = v * (1.0 - s)

    i = i % 6
    if i == 0:
        return v, v * (1.0 - s * (1.0 - f)), p
    if i == 1:
        return v * (1.0 - s * f), v, p
    if i == 2:
        return p, v, v * (1.0 - s * (1.0 - f))
    if i == 3:
        return p, v * (1.0 - s * f), v
    if i == 4:
        return v * (1.0 - s * (1.0 - f)), p, v
    return v, p, v * (1.0 - s * f)


class PseudoLED:
    """
    An LED stand-in that stores a brightness without driving a pin. Comms sends
    its brightness it to another board, and PWMLED and DisabledLED build on it.
    """

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


class PWMLED(PseudoLED):
    """
    A basic wrapper for PWM with regular on/off and toggle functions from Pin.
    Intended to be used for driving LEDs with brightness control & compatibility with Pin.
    """

    FREQUENCY = 1000

    def __init__(self, pin, invert=False, gamma=1):
        super().__init__()
        self.__gamma = gamma
        self.__led = PWM(Pin(pin), freq=self.FREQUENCY, duty_u16=0, invert=invert)

    def brightness(self, brightness):
        # Clamped here, not through PseudoLED.brightness, the call costing more than the clamp
        self.__brightness = min(1.0, max(0.0, brightness))
        self.__led.duty_u16(int(pow(self.__brightness, self.__gamma) * 65535 + 0.5))


class DisabledLED(PseudoLED):
    """
    An LED that cannot light, as another pin uses its PWM channel. It drives its pin to the off
    level and prints why on the first attempt to light it, while turning it off passes quietly.
    """

    def __init__(self, pin, invert=False, reason=None):
        super().__init__()
        self.in_use_by = reason if reason is not None else f"GPIO {pin} cannot light, as another pin uses its PWM channel."
        self.__warned = False

        # Drive the pin to its off level, since being left as PWM will make it show the
        # signal of the other GPIO on its channel, or will glow faintly if left floating
        Pin(pin, Pin.OUT, value=invert)

    def brightness(self, brightness):
        if brightness > 0 and not self.__warned:
            print(self.in_use_by)
            self.__warned = True
        super().brightness(brightness)


class RGBLED:
    """Three LEDs driven together as red, green and blue, each from a pin or any PseudoLED."""

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

    # White, the colour every channel at full makes
    def on(self):
        self.__rgb(1, 1, 1)

    def off(self):
        self.__rgb(0, 0, 0)


class Updateable:
    """The base of an effect that changes over time, its player calling tick() once a frame with the frame period in milliseconds."""

    def __init__(self):
        pass

    def tick(self, delta_ms):
        pass

    def reset(self):
        pass


class Cycling(Updateable):
    """An Updateable whose __offset counts from 0.0 to 1.0 and repeats, at speed cycles a second."""

    def __init__(self, speed):
        self.speed = speed
        self.__offset_us = 0    # Microseconds, since a slow speed moves less than a millisecond a tick
        self.__offset = 0

    def tick(self, delta_ms):
        self.__offset_us = (self.__offset_us + int(delta_ms * 1000 * self.speed)) % 1_000_000
        self.__offset = self.__offset_us / 1_000_000

    def reset(self):
        self.__offset_us = 0
        self.__offset = 0


class CyclingAction(Updateable):
    """An Updateable that calls next() each time it completes a cycle forwards and prev() backwards, at speed cycles a second."""

    def __init__(self, speed):
        self.speed = speed
        self.__offset_us = 0
        self.__offset = 0

    def next(self):
        pass

    def prev(self):
        pass

    def tick(self, delta_ms):
        self.__offset_us += int(delta_ms * 1000 * self.speed)
        if self.__offset_us >= 1_000_000:
            self.__offset_us -= 1_000_000
            self.next()
        elif self.__offset_us < 0:
            self.__offset_us += 1_000_000
            self.prev()

        self.__offset = self.__offset_us / 1_000_000

    def reset(self):
        self.__offset_us = 0
        self.__offset = 0


class EffectPlayer:
    """The base of the players, calling each channel's effect once a frame on a timer and showing what it returns."""

    DEFAULT_FPS = 100

    def __init__(self, leds, num_leds=None):
        # Check if an LED count was given. Only an object holding many LEDs needs to provide this, such as a strip
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

        # Whether each channel's effect brings its own colour, so cannot take a curve
        self.__chromatic = [False] * self.__num_leds

        # How each channel follows its effect, None following it at once
        self.__curves = [None] * self.__num_leds

        # What each curved channel is showing, for its curve to move on from
        self.__showing = [0.0] * self.__num_leds

        self.__period_ms = 1000
        self.__timer = Timer()
        self.__paired = None
        self.__running = False
        self.__last = time.ticks_ms()
        self.__measured_ms = 0

    def start(self, fps=DEFAULT_FPS, force=False):
        if not self.is_running() or force:
            self.stop()

            # Rounded to the nearest millisecond, and floored at one so a rate past 1000fps still ticks
            self.__period_ms = max(1, int(1000 / fps + 0.5))

            # Each paired player ticks the next, so the whole chain runs on this
            # timer and every one of them measures time by this period
            partner = self.__paired
            while partner is not None:
                partner.__period_ms = self.__period_ms
                partner = partner.__paired

            self.__last = time.ticks_ms()
            self.__timer.init(mode=Timer.PERIODIC, period=self.__period_ms, callback=self.__update)
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

    # Pair another player to update straight after this one, using this player's or its parent's timer
    def pair(self, player):
        self.__paired = player

    @property
    def target_ms(self):
        return self.__period_ms

    @property
    def measured_ms(self):
        return self.__measured_ms

    @property
    def target_fps(self):
        return 1000 / self.__period_ms

    @property
    def measured_fps(self):
        return 1000 / self.__measured_ms if self.__measured_ms > 0 else float("inf")

    def __update(self, timer):
        # Timer callbacks arrive via the scheduler, so one already in-flight
        # at deinit can still run after stop() and must not update the LEDs
        if self.__running:
            self.__tick(timer)

    def __tick(self, timer):
        try:
            for ufx in self.__updateables:
                ufx.tick(self.__period_ms)

            self.__show()

            if self.__paired is not None:
                self.__paired.__tick(timer)
        except BaseException as e:
            self.stop()
            raise e

        now = time.ticks_ms()
        self.__measured_ms = time.ticks_diff(now, self.__last)
        self.__last = now

    @property
    def effects(self):
        return tuple(self.__effects)

    @effects.setter
    def effects(self, effect_list):
        effect_list = self.__to_channel_list(effect_list, "effects")

        self.__updateables = set()
        for i, item in enumerate(effect_list):
            self.__effects[i] = None
            self.__data[i] = ()
            self.__chromatic[i] = False

            # Skip the item if it is none
            if item is None:
                continue

            # Does the effect bring its own colour? A curve cannot follow one, so this and the
            # curves setter each refuse the pairing, whichever is set second, and the tick never checks
            owner = item[0] if isinstance(item, tuple) and item else item
            if getattr(owner, "CHROMATIC", False):
                self.__chromatic[i] = True
                if self.__curves[i] is not None:
                    raise ValueError(f"channel {i} has a curve, and this effect brings its own colour, which a curve cannot follow: clear the curve, or give the channel a mono effect")

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

                    # Are there other elements, and is the second element callable?
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
            self.__chromatic[i] = False

    def __to_channel_list(self, values, name):
        # A list holds a value per channel. Anything else is one value for every channel, a tuple included
        values = values if isinstance(values, list) else [values] * self.__num_leds

        if len(values) > self.__num_leds:
            raise ValueError(f"{name} has {len(values)} entries for {self.__num_leds} channels. Give at most {self.__num_leds}, or one value for every channel")

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

    @property
    def curves(self):
        return tuple(self.__curves)

    @curves.setter
    def curves(self, curves):
        """How a channel reaches what its effect asks for, or None to reach it at once.

        Made by ease() or fade(), taking one length for both ways or a rise and a fall.
        A mono effect's level is what a curve moves, so a colour effect cannot take one.
        """
        curves = self.__to_channel_list(curves, "curves")

        for i, curve in enumerate(curves):
            if curve is None:
                self.__curves[i] = None
                continue

            if self.__chromatic[i]:
                raise ValueError(f"channel {i}'s effect brings its own colour, which a curve cannot follow: curve a mono effect, or set levels, which reaches both")

            if not isinstance(curve, Curve):
                raise ValueError("a curve is made by ease() or fade(), or None for a "
                                 "channel that follows its effect at once")
            if curve.rise < 0 or curve.fall < 0:
                raise ValueError("a curve is how long a channel takes to follow its "
                                 "effect, so it cannot be negative")
            self.__curves[i] = None if curve.rise == 0 and curve.fall == 0 else curve

        # Reset excess curves
        for i in range(len(curves), self.__num_leds):
            self.__curves[i] = None

    # What a curved channel shows this frame, moved toward what its effect asks for. A
    # caller skips this where no curve is set, the call costing more than the check
    def __followed(self, index, value):
        # Its fields are read by index, which costs less than by name
        curve = self.__curves[index]
        showing = self.__showing[index]
        rising = value > showing
        seconds = curve[0] if rising else curve[1]
        if seconds > 0:
            # Both scale by the period, so a curve takes its length at any frame rate
            if curve[2]:
                step = self.__period_ms / (seconds * 1000)
                value = min(value, showing + step) if rising else max(value, showing - step)
            else:
                value = value + (showing - value) * 2 ** (-(self.__period_ms * SETTLE) / (seconds * 1000))

        self.__showing[index] = value
        return value


class MonoPlayer(EffectPlayer):
    """A player for single colour LEDs, showing each channel's effect as a brightness."""

    def __init__(self, mono_leds):
        super().__init__(mono_leds)

    def __show(self):
        # Fetched once a frame, where each output would otherwise look them up again
        effects = self.__effects
        data = self.__data
        levels = self.__levels
        curves = self.__curves
        leds = self.__leds
        for i in range(self.__num_leds):
            if effects[i] is not None:
                # Unpacking an empty tuple allocates, so a channel with no data is called bare
                item = data[i]
                value = (effects[i](*item) if item else effects[i]()) * levels[i]
                if curves[i] is not None:
                    value = self.__followed(i, value)
                leds[i].brightness(value)


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
                raise TypeError(f"colour {i} is {colour!r}. Give each colour as a tuple of three numbers from 0 to 255")

            self.__colours[i] = tuple(min(255, max(0, c)) for c in colour)

        # Reset excess colours
        for i in range(len(colours), self.__num_leds):
            self.__colours[i] = (255, 255, 255)


class ColourPlayer(ChromaticPlayer):
    """A player for RGB LEDs, showing a colour effect as it is and a mono effect in its channel's colour."""

    def __init__(self, rgb_leds):
        super().__init__(rgb_leds)

    def __show(self):
        # The lists are read from self each time, since fetching them once a frame as the other
        # players do takes this frame past the slots a board keeps on the C stack
        is_instance = isinstance
        tuple_type = tuple
        for i in range(self.__num_leds):
            if self.__effects[i] is not None:
                item = self.__data[i]
                value = self.__effects[i](*item) if item else self.__effects[i]()
                level = self.__levels[i]

                if is_instance(value, tuple_type):
                    # A colour effect brings its own colour, so only the level applies
                    self.__leds[i].set_rgb(value[0] * level, value[1] * level, value[2] * level)
                else:
                    # A mono effect gives a 0.0 to 1.0 level to scale the channel's colour by
                    value *= level
                    if self.__curves[i] is not None:
                        value = self.__followed(i, value)
                    r, g, b = self.__colours[i]
                    self.__leds[i].set_rgb(r * value, g * value, b * value)


class StripPlayer(ChromaticPlayer):
    """A player for a WS2812 or APA102 strip, one channel per LED, sending the strip its frame each time it draws one."""

    def __init__(self, led_strip, num_leds=60):
        super().__init__(led_strip, num_leds)

    def __show(self):
        # Fetched once a frame, where each LED would otherwise look them up again
        effects = self.__effects
        data = self.__data
        levels = self.__levels
        curves = self.__curves
        colours = self.__colours
        strip = self.__leds
        is_instance = isinstance
        tuple_type = tuple
        to_int = int
        for i in range(self.__num_leds):
            if effects[i] is not None:
                item = data[i]
                value = effects[i](*item) if item else effects[i]()
                level = levels[i]

                # Indexed one at a time, a genexp here allocating once an LED a frame
                if is_instance(value, tuple_type):
                    r = value[0] * level
                    g = value[1] * level
                    b = value[2] * level
                else:
                    value *= level
                    if curves[i] is not None:
                        value = self.__followed(i, value)
                    colour = colours[i]
                    r = colour[0] * value
                    g = colour[1] * value
                    b = colour[2] * value

                # The strip is driven through a C binding, which wants whole numbers
                strip.set_rgb(i, to_int(r), to_int(g), to_int(b))

        # A strip shows nothing until its frame is sent, once a frame
        strip.update()
