# Pimoroni Mighty FX - Library Reference <!-- omit in toc -->

This is the library reference for the [Pimoroni Mighty FX](https://shop.pimoroni.com/products/mightyfx), a light, motion and screen effects controller, powered by the Raspberry Pi RP2350.


## Table of Content <!-- omit in toc -->
- [Getting Started](#getting-started)
- [Reading the User Button](#reading-the-user-button)
- [Setting the RGB LED Outputs](#setting-the-rgb-led-outputs)
  - [Mono LEDs](#mono-leds)
- [The L and R Connectors](#the-l-and-r-connectors)
  - [LED Strips](#led-strips)
  - [Servos](#servos)
- [The SP/CE Connectors](#the-spce-connectors)
- [Using the Sensor Connector](#using-the-sensor-connector)
- [Playing Sound](#playing-sound)
- [Reading Voltage](#reading-voltage)
- [Effects System](#effects-system)
- [`MightyFX` Reference](#mightyfx-reference)
  - [Constants](#constants)
  - [Variables](#variables)
  - [Functions](#functions)


## Getting Started

To start coding your Mighty FX, you will need to add the following lines to the start of your code file.

```python
from mighty_fx import MightyFX
mighty = MightyFX()
```

This will create a `MightyFX` class called `mighty` that will be used in the rest of the examples going forward.

Anything attached to the board beyond its RGB outputs is declared when it is created, such as `MightyFX(strip_l=60)` for an LED strip on **L**. The board sets up only what it is told about, leaving every other pin free.


## Reading the User Button

Mighty FX has one user button, labelled **Boot**. This can be read using the `boot_pressed()` function:

```python
state_boot = mighty.boot_pressed()
```

This reports the button's state at the moment it is asked, so a tap that starts and ends between two reads is missed. `boot_taps()` instead counts presses as they happen, and returns how many there have been since it was last called:

```python
taps = mighty.boot_taps()
```


## Setting the RGB LED Outputs

Mighty FX has seven outputs for non-addressable RGB LEDs, labelled **1** to **7**, each lighting every LED wired to it in the same colour. These can be accessed either through the `outputs` list, or by individual properties, which return `RGBLED` objects:

```python
one = mighty.outputs[0]
also_one = mighty.one
```

These `RGBLED` objects offer two functions to control their associated output, `set_rgb()` which accepts `r`, `g`, and `b` values from `0` to `255`, and `set_hsv()` which accepts `h`, `s`, and `v` values from `0.0` to `1.0`. There are also `on()`, which sets every channel to full, giving white, and `off()`.

```python
# Turn the first output red
mighty.one.set_rgb(255, 0, 0)
time.sleep(1)

# Turn the second output green
mighty.two.set_hsv(0.333, 1, 1)
time.sleep(1)

# Turn them both off again
mighty.one.off()
mighty.two.off()
```

### Mono LEDs

Each RGB output's three channels are also available alone, through the `led_r`, `led_g` and `led_b` variables on each `RGBLED`, giving access to the internal `PWMLED` objects used. A mono LED plugged into an output reaches one of these. For convenience, `monos` lists every output's three channels in turn, 21 in all:

```python
# Light whichever channel a mono LED on output 1 reaches
mighty.monos[0].on()
```


## The L and R Connectors

The **L** and **R** connectors each carry one signal, and each can drive either an LED strip or a servo. Both share a power rail, which the board leaves off until `enable_rail()` is called, so nothing on them is live before then. A white indicator LED lights while the rail is on. `disable_rail()` turns it off again, and `is_rail_enabled()` reports whether it is on.

```python
mighty = MightyFX(strip_l=60)
mighty.enable_rail()
```

### LED Strips

A WS2812 strip is declared with its LED count, or with its count and the order it takes its colours in, for the many strips that do not take them as green, red, blue:

```python
mighty = MightyFX(strip_l=60, strip_r=(30, "rgb"))
```

Each is then available through `strip_l` and `strip_r`. A strip shows what it has been given only when `update()` is called:

```python
mighty.enable_rail()

strip = mighty.strip_l
strip.set_rgb(0, 255, 0, 0)     # The first LED red
strip.set_hsv(1, 0.333, 1, 1)   # The second LED green
strip.update()
```

To play effects along a strip, give it to a `StripPlayer`, as the `strips` examples do.

### Servos

A servo is declared with the calibration that suits it, from the `servo` module:

```python
from servo import ANGULAR, CONTINUOUS

mighty = MightyFX(servo_l=ANGULAR, servo_r=CONTINUOUS)
mighty.enable_rail()

mighty.servo_l.value(45)
```

Each connector shares a PWM channel with one SP/CE connector's backlight, **L** with SP/CE A and **R** with SP/CE B, so a servo cannot be used on a connector whose SP/CE partner drives a screen. The board says so when created, naming the other connector to use.


## The SP/CE Connectors

Mighty FX has two SP/CE connectors, **A** and **B**, each declared for the role it plays from the `SPCE` choices:

| role | what the connector does |
| --- | --- |
| `SPCE.SCREEN` | drives screens over its own SPI bus and backlight |
| `SPCE.MOTOR_DRIVER` | drives a motor driver's two motors and the enable they share |
| `SPCE.GPIO` | hands its five pins out through the port's `io` |
| `SPCE.HUB_SELECTS` | gives its five pins to a Screen Hub on the other connector, as the hub's chip selects |

```python
from mighty_fx import MightyFX, SPCE

mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.MOTOR_DRIVER)
```

Each connector is then available through `spce_a` and `spce_b`, which screens and motor drivers are created against:

```python
from motor_driver import MotorDriver

driver = MotorDriver(mighty.spce_b)
driver.enable()
driver.motor_a.speed(0.5)
```

A motor driver drives PWM on its connector's data lines, which some LED outputs share channels with. Those outputs' affected channels report an error if lit, rather than showing the motor's signal.

With one connector declared `SPCE.SCREEN` and the other `SPCE.HUB_SELECTS`, the board builds a Screen Hub, available through `hub`. Driving screens is covered in the [Screens Library Reference](/docs/screens.md).


## Using the Sensor Connector

Mighty FX has a connector for a single sensor, carrying one signal alongside ground and 3.3V. Two accessories are made for it, the PIR Stick and the IR Receiver, and the signal can also be read as an analog voltage. The board sets each of these up for you when told which one to use:

```python
from sensor import ANALOG, PIR, IR

mighty = MightyFX(sensor=ANALOG)
```

What the board set up is then available through `sensor`:

| role | what `sensor` gives you |
| --- | --- |
| `ANALOG` | an `Analog`, read with `read_voltage()`, which optionally takes a `samples` count |
| `PIR` | a `Pin`, already an input with its pull-up set, read with `value()` |
| `IR` | a `NECRemoteReceiver` from the `aye_arr` library, already started, ready to `bind()` a remote and `decode()` |

Without `sensor=`, the board leaves the connector alone, and reading `sensor` raises an error saying so.


## Playing Sound

Mighty FX has a speaker connector, driven by a `WavPlayer` available through `wav`. It plays WAV files and tones, as described in the `WavPlayer` section of the [Tiny FX Library Reference](/docs/reference.md#wavplayer-reference):

```python
mighty.wav.play_wav("chime.wav")
```

Its buffer holds 200ms of sound, enough to play smoothly beside two screens showing animations. Pass `init_wav=False` to leave the speaker's pins free.


## Reading Voltage

Mighty FX features onboard voltage monitoring, letting you change your effects as the supply changes, which on battery is the cell itself. This can be read by calling `read_voltage()`, which optionally accepts a `samples` parameter to reduce noise by taking the average across multiple readings.

```python
SAMPLES = 50        # The number of measurements to take per reading, to reduce noise

voltage = mighty.read_voltage(SAMPLES)
print("Voltage =", round(voltage, 2))
```


## Effects System

To make it easier to run multiple effects simultaneously, the `PicoFX` library hands LED control over to players, which each get assigned a range of effects objects: a `ColourPlayer` for the RGB outputs, and a `StripPlayer` for each strip. The program lifecycle is the same as on Tiny FX, described in the [Tiny FX Library Reference](/docs/reference.md#program-lifecycle).

```python
from mighty_fx import MightyFX
from picofx import ColourPlayer
from picofx.colour import RainbowWaveFX

mighty = MightyFX()
player = ColourPlayer(mighty.outputs)

wave = RainbowWaveFX(speed=0.3, length=7)
player.effects = [wave(i) for i in range(len(mighty.outputs))]

try:
    player.start()
    while player.is_running() and not mighty.boot_pressed():
        pass
finally:
    player.stop()
    mighty.shutdown()
```

`shutdown()` turns everything off and hands back what the board claimed, so the next program can start cleanly.


## `MightyFX` Reference

### Constants
```python
OUT_PINS = ((3, 0, 1), (4, 5, 2), (9, 6, 7), (10, 11, 8), (15, 12, 13), (38, 39, 14), (42, 40, 41))

I2C_SDA_PIN = 16
I2C_SCL_PIN = 17

USER_SW_PIN = 18

I2S_DATA_PIN = 20
I2S_BCLK_PIN = 21
I2S_LRCLK_PIN = 22
AMP_EN_PIN = 23

SPCE_A_PINS = (32, 33, 34, 35, 36)     # DC, CS, SCK, MOSI, BL
SPCE_B_PINS = (24, 25, 26, 27, 37)     # DC, CS, SCK, MOSI, BL

SERVO_STRIP_EN = 43
SERVO_STRIP_L = 44
SERVO_STRIP_R = 45

SENSOR_PIN = 46
V_SENSE_PIN = 47

V_SENSE_GAIN = 2
RGB_GAMMA = 2.2
```


### Variables
```python
outputs: list[RGBLED]
monos: list[PWMLED]
spce_a: SPCEPort
spce_b: SPCEPort
```


### Functions

```python
# Initialisation
MightyFX(spce_a: int=None,
         spce_b: int=None,
         strip_l: int | tuple=None,
         strip_r: int | tuple=None,
         servo_l: int=None,
         servo_r: int=None,
         sensor: string=None,
         init_i2c: bool=True,
         i2c_freq: int=100000,
         init_wav: bool=True,
         wav_root: string="/")
@classmethod
wake() -> None

# Interaction
boot_pressed() -> bool
boot_taps() -> int

# Power
enable_rail() -> None
disable_rail() -> None
is_rail_enabled() -> bool

# Sensing
read_voltage(samples: int=1) -> float
@property
sensor -> Analog | Pin | NECRemoteReceiver

# Access
@property
one -> RGBLED
...
@property
seven -> RGBLED
@property
strip_l -> WS2812
@property
strip_r -> WS2812
@property
servo_l -> Servo
@property
servo_r -> Servo
@property
hub -> ScreenHub
@property
i2c -> PimoroniI2C
@property
wav -> WavPlayer

# Tidy
clear() -> None
shutdown() -> None
```
