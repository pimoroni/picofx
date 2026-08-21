# PicoFX - Library Reference <!-- omit in toc -->

This is the library reference for the PicoFX library.

- [LEDs](#leds)
  - [PWMLED](#pwmled)
  - [RGBLED](#rgbled)
- [Players](#players)
  - [MonoPlayer](#monoplayer)
  - [ColourPlayer](#colourplayer)
  - [StripPlayer](#stripplayer)
  - [Common](#common)
- [Effects System](#effects-system)
  - [Offering an effect to an effects file](#offering-an-effect-to-an-effects-file)


## LEDs

Two classes are offered for controlling LEDs:
* `PWMLED` - This is for controlling a single LED using a PWM output
* `RGBLED` - This is for controlling a three LEDs, as red, green, and blue, using PWM outputs

### PWMLED

```python
# Initialisation
PWMLED(pin: int, invert: bool=False, gamma: float=1)

# Brightness Control
brightness(brightness: float) -> None
on() -> None
off() -> None
toggle() -> None
```

### RGBLED

```python
# Initialisation
RGBLED(r: Pin | PWMLED, g: Pin | PWMLED, b: Pin | PWMLED, invert: bool=True, gamma: float=1)

# Variables
led_r: PWMLED
led_g: PWMLED
led_b: PWMLED

# Colour Control
set_rgb(r: int | float, g: int | float, b: int | float) -> None
set_hsv(h: float, s: float, v: float) -> None
```


## Players

Players are classes that deal with taking brightnesses and colours from effects and applying them to a set of LEDs.
There is a common `EffectPlayer` class, and three subclasses to support specific LED types:
* `MonoPlayer` - controls a set of `PWMLED` objects
* `ColourPlayer` - controls a set of `RGBLED` objects
* `StripPlayer` - controls a strip of `WS2812` or `APA102` LEDs. These classes come from the Pimoroni [Plasma library](https://github.com/pimoroni/pimoroni-pico/tree/main/micropython/modules/plasma).


### MonoPlayer

```python
# Initialisation
MonoPlayer(mono_leds: PWMLED | list[PWMLED])
```


### ColourPlayer

```python
# Initialisation
ColourPlayer(rgb_leds: RGBLED | list[RGBLED])
```


### StripPlayer

```python
# Initialisation
StripPlayer(rgb_leds : WS2812 | APA102, num_leds: int=60)
```


### Common
```python
# Constants
DEFAULT_FPS = 100

# Player Control
start(fps: int=DEFAULT_FPS, force: bool=False) -> None
stop(reset_fx: bool=False) -> None
is_running() -> bool

# Synchronisation
pair(player: EffectPlayer) -> None

# Properties
effects: tuple[Any]
effects(effect_list: Any | list[Any]) -> None
```

## Effects System

The effect system is quite flexible, accepting any `callable` object, be it a function or a class. Using classes is preferred, by implementing their `__call__` method as this lets their state be changed over time. For example:

```python
class StaticFX:
    def __init__(self, brightness=1.0):
        self.brightness = brightness

    def __call__(self):
        return self.brightness
```

For creating dynamic effects, classes can inherit from two types, `Updateable` and `Cycling`:

* `Updateable` gives an effect the `ticks_ms(delta_ms)` function, letting the effect change over time.
* `Cycling` is an extension of `Updateable` that pre-implements a cycling counter within `ticks_ms` giving the `__call__` method access to a `__offset` variable that counts up from 0.0 to 1.0 and repeats.


### Offering an effect to an effects file

On MightyFX, an effect can also be written by name in `effects.txt`. An effect offers itself by declaring three class attributes:

* `NAME` is the word an entry writes. An effect without one is not offered.
* `CALLED` is how a channel gets its callable: `None` where one object serves every channel, `"position"` where it is called with the channel's place in the group, and a tuple of method names where it names one per channel, as `traffic_light` names `red`, `amber` and `green`.
* `TAKES` is the settings an entry may write.

```python
from picofx import Cycling


class BreatheFX(Cycling):
    NAME = "breathe"
    CALLED = None
    TAKES = ("speed", "brightness")

    def __init__(self, speed=1, brightness=1.0):
        super().__init__(speed)
        self.brightness = brightness

    def __call__(self):
        # __offset counts 0.0 to 1.0 and repeats, so this rises and falls once a cycle
        return abs(self.__offset * 2 - 1) * self.brightness
```

The effects the board already knows are the ones in `MONO_EFFECTS` and `COLOUR_EFFECTS`, which is a list an effect of your own can be added to. Do it in `main.py`, before `autofx` is imported, since that is when the names are gathered:

```python
from picofx.mono import MONO_EFFECTS
from breathe import BreatheFX

MONO_EFFECTS.append(BreatheFX)

import autofx
```

`out1-4: breathe speed=0.5 brightness=80%` then plays it, and a value the effect cannot use is reported in `errors.txt` the way any other is.

Settings are named rather than invented: `TAKES` may only hold names the effects file already reads, `speed`, `duty`, `interval`, `brightness`, `hue` and the rest listed in the manual. A name it has no reading for is reported and the effect runs on its own value for it.