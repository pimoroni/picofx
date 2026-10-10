# Pimoroni Tiny FX - Library Reference <!-- omit in toc -->

This is the library reference for the [Pimoroni Tiny FX](https://shop.pimoroni.com/products/tinyfx), a LED effects controller, powered by the Raspberry Pi RP2040.


## Table of Content <!-- omit in toc -->
- [Getting Started](#getting-started)
- [Reading the User Button](#reading-the-user-button)
- [Setting the Mono LED Outputs](#setting-the-mono-led-outputs)
- [Setting the RGB LED Output](#setting-the-rgb-led-output)
- [Using the Sensor Connector](#using-the-sensor-connector)
- [Reading Voltage](#reading-voltage)
- [Effects System](#effects-system)
  - [Program Lifecycle](#program-lifecycle)
- [`TinyFX` Reference](#tinyfx-reference)
  - [Constants](#constants)
  - [Variables](#variables)
  - [Functions](#functions)
- [`WavPlayer` Reference](#wavplayer-reference)
  - [Constants](#constants-1)
  - [Functions](#functions-1)


## Getting Started

To start coding your Tiny FX, you will need to add the following lines to the start of your code file.

```python
from tiny_fx import TinyFX
tiny = TinyFX()
```

This will create a `TinyFX` class called `tiny` that will be used in the rest of the examples going forward.


## Reading the User Button

Tiny FX has one user button, labelled **Boot**. This can be read using the `boot_pressed()` function:

```python
state_boot = tiny.boot_pressed()
```

This reports the button's state at the moment it is asked, so a tap that starts and ends between two reads is missed. `boot_taps()` instead counts presses as they happen, and returns how many there have been since it was last called:

```python
taps = tiny.boot_taps()
```


## Setting the Mono LED Outputs

Tiny FX has six outputs for mono LEDs, labelled **1**, **2**, **3**, **4**, **5**, and **6**, each lighting every LED wired to it together. These can be accessed either through the `outputs` list, or by individual properties, which return `PWMLED` objects:

```python
one = tiny.outputs[0]
also_one = tiny.one
```

These `PWMLED` objects offer several functions to control their associated outputs. They can be turned `on()`, turned `off()`, inverted via `toggle()` and have their brightness directly set via `brightness()`, which accepts a value from `0.0` to `1.0`.

```python
# Turn the first output on
tiny.one.on()
time.sleep(1)

# Turn the first output off
tiny.one.off()
time.sleep(1)

# Invert the first output (from off to on)
tiny.one.toggle()
time.sleep(1)

# Set the output to half brightness
tiny.one.brightness(0.5)
time.sleep(1)
```

## Setting the RGB LED Output

Tiny FX has a single output for non-addressable RGB LEDs, labelled **RGB**, lighting every LED wired to it in the same colour. This can be accessed through the `rgb` variable, which returns a `RGBLED` object:

```python
rgb = tiny.rgb
```

This `RGBLED` object offers two functions to control its associated output, `set_rgb()` which accepts `r`, `g`, and `b` values from `0` to `255`, and `set_hsv()` which accepts `h`, `s`, and `v` values from `0.0` to `1.0`.

```python
# Turn the rgb output to red
rgb.set_rgb(255, 0, 0)
# rgb.set_hsv(0, 1, 1)
time.sleep(1)

# Turn the rgb output to green
rgb.set_rgb(0, 255, 0)
# rgb.set_hsv(0.333, 1, 1)
time.sleep(1)

# Turn the rgb output to blue
rgb.set_rgb(0, 0, 255)
# rgb.set_hsv(0.666, 1, 1)
time.sleep(1)

# Turn the rgb output to white
rgb.set_rgb(255, 255, 255)
# rgb.set_hsv(0, 0, 1)
time.sleep(1)
```

There are also `on()` and `off()`. `on()` sets every channel to full, giving white, and `off()` is the same as `set_rgb(0, 0, 0)`.

```python
# Turn the rgb output on, then off again
rgb.on()
time.sleep(1)
rgb.off()
```

It is also possible to control the individual outputs of the RGB connection by accessing the `led_r`, `led_g`, `led_b` variables on the `RGBLED`, giving access to the internal `PWMLED` objects used.

```python
# Turn the rgb output to red
rgb.led_r.on()
rgb.led_g.off()
rgb.led_b.off()
time.sleep(1)

# Turn the rgb output to green
rgb.led_r.off()
rgb.led_g.on()
rgb.led_b.off()
time.sleep(1)

# Turn the rgb output to blue
rgb.led_r.off()
rgb.led_g.off()
rgb.led_b.on()
time.sleep(1)

# Turn the rgb output to white
rgb.led_r.on()
rgb.led_g.on()
rgb.led_b.on()
time.sleep(1)
```

This can be useful for if you wish to connect up additional mono LEDs (the RGB connector can actually accept a Mono connector without any rewiring), though note that the gamma value for the RGB output is slightly different to that of the mono outputs.


## Using the Sensor Connector

Tiny FX has a connector for a single sensor, carrying one signal alongside ground and 3.3V. Two accessories are made for it, the PIR Stick and the IR Receiver, and the signal can also be read as an analog voltage. The board sets each of these up for you when told which one to use:

```python
from sensor import ANALOG, PIR, IR

tiny = TinyFX(sensor=ANALOG)
```

What the board set up is then available through `sensor`:

| role | what `sensor` gives you |
| --- | --- |
| `ANALOG` | an `Analog`, read with `read_voltage()`, which optionally takes a `samples` count |
| `PIR` | a `Pin`, already an input with its pull-up set, read with `value()` |
| `IR` | a `NECRemoteReceiver` from the `aye_arr` library, already started, ready to `bind()` a remote and `decode()` |

Letting the board set up `IR` is especially worthwhile, as the receiver needs a PIO state machine and the board knows which ones are free.

```python
from aye_arr.nec.remotes import PimoroniRemote

tiny = TinyFX(sensor=IR)

receiver = tiny.sensor
receiver.bind(PimoroniRemote())
```

Without `sensor=`, the board leaves the connector alone, and reading `sensor` raises an error saying so. To use the connector some other way, its pin number is available as `SENSOR_PIN`.


## Reading Voltage

Tiny FX features onboard voltage monitoring, letting you change your effects as your battery voltage changes, perhaps to indicate when new batteries are needed. This can be read by calling `read_voltage()`, which optionally accepts a `samples` parameter to reduce noise by taking the average across multiple readings.

```python
SAMPLES = 50        # The number of measurements to take per reading, to reduce noise

voltage = tiny.read_voltage(SAMPLES)
print("Voltage =", round(voltage, 2))
```

## Effects System

To make it easier to run multiple effects simultaneously, the `PicoFX` library was created. This library hands LED control over to two classes, a `MonoPlayer` and a `ColourPlayer`, which each get assigned a range of effects objects. For more information about this, refer to the [PicoFX Library Reference](https://github.com/pimoroni/picofx/blob/main/picofx/README.md).


### Program Lifecycle

When writing a program for Tiny FX using PicoFX, there are a number of steps that should be included to make best use of the board's capabilities.


```python
# Perform system level imports here
# e.g. import math

from tiny_fx import TinyFX
from picofx import MonoPlayer       # This import is only needed if using the mono outputs
from picofx import ColourPlayer     # This import is only needed if using the colour output

# Import any effects you are using
# e.g. from picofx.mono import BinaryCounterFX
# e.g. from picofx.colour import RainbowFX

"""
This is a boilerplate example for Tiny FX. Use it as a base for your own programs.

Press "Boot" to exit the program.
"""

# Constants
# e.g. SLEEP_TIME = 0.1

# Variables
tiny = TinyFX()     # Create a new TinyFX object. These optional keyword parameters are supported:
                    # `init_i2c`, `init_wav`, and `wav_root`
player = MonoPlayer(tiny.outputs)       # Create a new effect player to control TinyFX's mono outputs
rgb_player = ColourPlayer(tiny.rgb)     # Create a new effect player to control TinyFX's rgb output

# Create your effects objects here
# e.g. binary = BinaryCounterFX(interval=0.1)

# Set up the mono effects to play
# e.g. player.effects = [
#          binary(0),
#          binary(1),
#          binary(2),
#          binary(3),
#          binary(4),
#          binary(5)
#      ]

# Set up the colour effect to play
# e.g. rgb_player.effects = RainbowFX(speed=0.2, sat=1.0, val=1.0)

# Have the RGB player run in sync with the Mono player
player.pair(rgb_player)


# Place other variables here
# e.g. button_state = False


# Put any functions needed for your program here
# e.g. def my_function():
#          pass


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()   # Start the effects running

    # Perform any other setup

    # Loop until the effect stops or the "Boot" button is pressed
    while player.is_running() and not tiny.boot_pressed():
        #######################
        # Put your program here
        #######################
        pass

# Stop any running effects and turn off all the outputs
finally:
    player.stop()
    tiny.shutdown()
```


## `TinyFX` Reference

### Constants
```python
OUT_PINS = (3, 2, 4, 5, 8, 9)
RGB_PINS = (13, 14, 15)

I2C_SDA_PIN = 16
I2C_SCL_PIN = 17

I2S_DATA_PIN = 18
I2S_BCLK_PIN = 19
I2S_LRCLK_PIN = 20
AMP_EN_PIN = 21

USER_SW_PIN = 22
SENSOR_PIN = 26
V_SENSE_PIN = 28

V_SENSE_GAIN = 2
V_SENSE_DIODE_CORRECTION = 0.3

OUTPUT_GAMMA = 2.8
RGB_GAMMA = 2.2
```


### Variables
```python
outputs: list[PWMLED]
rgb: RGBLED

# If init_i2c was True
i2c: PimoroniI2C

# If init_wav was True
wav: WavPlayer
```


### Functions

```python
# Initialisation
TinyFX(init_i2c: bool=True,
       i2c_freq: int=100000,
       init_wav: bool=True,
       wav_root: string="/",
       sensor: string=None)

# Interaction
boot_pressed() -> bool
boot_taps() -> int

# Sensing
read_voltage(samples: int=1) -> float
@property
sensor -> Analog | Pin | NECRemoteReceiver

# Access
@property
one -> PWMLED
@property
two -> PWMLED
@property
three -> PWMLED
@property
four -> PWMLED
@property
five -> PWMLED
@property
six -> PWMLED

# Tidy
clear() -> None
shutdown() -> None
```


## `WavPlayer` Reference

### Constants

```python
# Internal states
PLAY = 0
PAUSE = 1
FLUSH = 2
STOP = 3
NONE = 4

MODE_WAV = 0
MODE_TONE = 1

TONE_SINE = 0
TONE_SQUARE = 1
TONE_TRIANGLE = 2

# Default buffer length
SILENCE_BUFFER_LENGTH = 1024
WAV_BUFFER_LENGTH = 1024
INTERNAL_BUFFER_LENGTH = WAV_BUFFER_LENGTH * 2

TONE_SAMPLE_RATE = 44_100
TONE_BITS_PER_SAMPLE = 16
TONE_FULL_WAVES = 2

# How long a tone or 16-bit WAV takes to fade in or out, where starting or stopping
# mid-waveform would click
FADE_MS = 40

# How long a write to the FX drive waits while a sound fades out
WRITE_HOLD_MS = 500
```


### Functions

```python
# Initialisation
WavPlayer(id: int,
          sck_pin: int,
          ws_pin: int,
          sd_pin: int,
          amp_enable: int=None,
          ibuf_len: int=INTERNAL_BUFFER_LENGTH,
          root: string="/",
          ibuf_ms: int=None)
deinit() -> None

# Directories
set_root(root: string) -> None

# Player Control
play_wav(wav_file: string | file, loop: bool=False, position: int=0) -> None
play_tone(frequency: float, amplitude: float, shape: int=TONE_SINE) -> None
pause() -> None
resume() -> None
stop() -> None
is_playing() -> bool
is_paused() -> bool
position() -> int | None
```

`ibuf_ms` grows the player's buffer to hold at least that many milliseconds of whatever plays, for a program whose refills can be held up, such as one drawing to screens.

A tone or 16-bit WAV fades in as it starts, and `pause()` and `stop()` fade it out over `FADE_MS` before taking effect, so `is_paused()` turns true once the fade has played out.

`position()` says how far into the current WAV playback has reached, in bytes, or `None` where no WAV is under way. Passing it back to `play_wav()` as `position` picks up from there.
