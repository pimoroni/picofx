# PicoFX - Library Reference <!-- omit in toc -->

This is the library reference for the PicoFX library.

- [LEDs](#leds)
  - [PWMLED](#pwmled)
  - [RGBLED](#rgbled)
  - [PseudoLED](#pseudoled)
  - [DisabledLED](#disabledled)
- [Players](#players)
  - [MonoPlayer](#monoplayer)
  - [ColourPlayer](#colourplayer)
  - [StripPlayer](#stripplayer)
  - [Common](#common)
- [Effects System](#effects-system)


## LEDs

Two classes are offered for controlling LEDs:
* `PWMLED` - This is for controlling a single LED using a PWM output
* `RGBLED` - This is for controlling three LEDs, as red, green, and blue, using PWM outputs

Two more are offered for special cases:
* `PseudoLED` - This stores a brightness without driving a pin, such as for comms to send to another board. `PWMLED` and `DisabledLED` build on it
* `DisabledLED` - This is for an LED that cannot light, as another pin uses its PWM channel

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
RGBLED(r: Pin | PseudoLED, g: Pin | PseudoLED, b: Pin | PseudoLED, invert: bool=True, gamma: float=1)

# Variables
led_r: PWMLED | PseudoLED
led_g: PWMLED | PseudoLED
led_b: PWMLED | PseudoLED
leds: tuple                 # led_r, led_g and led_b, to index or iterate

# Colour Control
set_rgb(r: int | float, g: int | float, b: int | float) -> None
set_hsv(h: float, s: float, v: float) -> None
on() -> None                # White, every channel at full
off() -> None
```

A pin given for a channel is driven as a `PWMLED`, and any `PseudoLED` given is used as it is.


### PseudoLED

```python
# Initialisation
PseudoLED()

# Variables
in_use_by: str | None       # Why the LED cannot light, or None where it can

# Brightness Control
brightness(brightness: float) -> None
on() -> None
off() -> None
toggle() -> None
```

`PWMLED` and `DisabledLED` build on `PseudoLED`, so each carries `in_use_by`. On its own it stores a brightness and drives nothing. The comms classes use it this way to send each brightness a player sets to another board over I2C.


### DisabledLED

```python
# Initialisation
DisabledLED(pin: int, invert: bool=False, reason: str=None)
```

A `DisabledLED` drives its pin to its off level and stays dark. The first attempt to light it prints `reason`, which is also its `in_use_by`, and turning it off is allowed, so code that clears every LED passes over it quietly.


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

The player sends the strip its frame with `update()` each time it draws one, so the strip needs no `start()` of its own.


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
levels: tuple[float]
levels(levels: float | list[float]) -> None
curves: tuple[Curve]
curves(curves: Curve | list[Curve]) -> None

# Timing
target_ms: int          # The period start() was given, in milliseconds
target_fps: float
measured_ms: int        # The time between the last two frames, in milliseconds
measured_fps: float
```

`start()` takes its rate to the nearest millisecond, so `target_fps` says the rate actually held, such as 30.3 for `start(30)`. Comparing the measured figures with the targets shows whether a player is keeping up, as the `multi_fx.py` example prints.

`levels` scales what each channel's effect asks for, so one effect can drive several outputs at different brightnesses. `ColourPlayer` and `StripPlayer` add `colours`, the colour each channel shows a mono effect's brightness in.

`curves` is how long a channel takes to reach what its effect asks for, instead of arriving at once. A curve is made by `fade()` or `ease()`:

```python
fade(rise: float, fall: float=None) -> Curve
ease(rise: float, fall: float=None) -> Curve
```

Both take seconds. A `fade` crosses at a steady rate and arrives in the length it is given; an `ease` settles into place, as a warming filament does. Passing one value uses it for both directions, and a second sets the fall apart from the rise, which is how a real bulb behaves. `None` clears a channel's curve, and neither the effect nor the frame rate is affected: the effect still returns what it always did, and the channel follows it.

A curve moves a mono effect's level, so a colour effect cannot take one. Setting a curve and a colour effect on the same channel raises a `ValueError` for whichever of the two is set second. `levels` works with both kinds.

```python
from picofx import MonoPlayer, ease

player = MonoPlayer(tiny.outputs)
player.effects = [blink] * 6
player.curves = [ease(0.2, 0.5)] * 6   # Slow to light, slower to go out
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

* `Updateable` gives an effect the `tick(delta_ms)` function, which the player calls once a frame with its frame period in milliseconds, letting the effect change over time.
* `Cycling` is an extension of `Updateable` that pre-implements a cycling counter within `tick` giving the `__call__` method access to a `__offset` variable that counts up from 0.0 to 1.0 and repeats.