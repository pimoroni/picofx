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