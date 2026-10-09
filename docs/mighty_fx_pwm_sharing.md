# Mighty FX - PWM Channel Sharing <!-- omit in toc -->

The RP2350 at the heart of Mighty FX has 24 PWM channels shared across its 48 GPIOs: pins 16
apart below GPIO 32 drive the same channel, as do pins 8 apart from GPIO 32 upward. When two pins
select PWM on a shared channel they emit the same signal, with no error raised by the hardware.

Mighty FX's pin allocation avoids this for normal use, but some functions share channels by
necessity. This page lists the pairings and what the library does about them.

## Table of Content <!-- omit in toc -->
- [Which Pins Share](#which-pins-share)
- [Motor Driving and the LED Outputs](#motor-driving-and-the-led-outputs)
- [Checking Before Lighting](#checking-before-lighting)
- [Using the Remaining Channels of a Partial Output](#using-the-remaining-channels-of-a-partial-output)
- [Screen Backlights and the Servo Connectors](#screen-backlights-and-the-servo-connectors)
- [Driving Pins Yourself](#driving-pins-yourself)
- [Tiny FX](#tiny-fx)


## Which Pins Share

The pairings that involve two Mighty FX functions:

| Function | GPIO | Shares with | GPIO |
|---|---|---|---|
| SP/CE B DC / Motor | 24 | Output 4 blue | 8 |
| SP/CE B CS / Motor | 25 | Output 3 red | 9 |
| SP/CE B SCK / Motor | 26 | Output 4 red | 10 |
| SP/CE B MOSI / Motor | 27 | Output 4 green | 11 |
| SP/CE A DC / Motor | 32 | Output 7 green | 40 |
| SP/CE A CS / Motor | 33 | Output 7 blue | 41 |
| SP/CE A SCK / Motor | 34 | Output 7 red | 42 |
| SP/CE A MOSI / Motor | 35 | Servo/Strip enable | 43 |
| SP/CE A backlight | 36 | Servo/Strip L | 44 |
| SP/CE B backlight | 37 | Servo/Strip R | 45 |
| Output 6 red | 38 | Sensor | 46 |

Every other Mighty FX pin pairs with a function that never selects PWM (I2C, I2S, the user
switch, the amp enable) or with an ADC input, so no other combination can conflict.


## Motor Driving and the LED Outputs

A screen on a SP/CE port uses SPI and does not touch the LED outputs. Driving motors does: the
port's four signal lines become PWM, taking the channels shared with output 7 (port A) or with
output 4 and output 3's red channel (port B).

The library handles this when the board is created. Any LED channel whose PWM channel a motor
role holds is replaced with a stand-in that stays dark. The first attempt to light it prints a
message naming the conflict, once, and effects continue running with that channel dark:

```
Output 7's red LED cannot light. GPIO 42 shares a PWM channel with GPIO 34, which SP/CE A is using to drive motors.
```

Turning a disabled channel off is silent, so `clear()` and `shutdown()` behave normally.


## Checking Before Lighting

Every LED channel carries an `in_use_by` attribute. It is `None` when the channel is free to
light, otherwise it holds the message above:

```python
mighty = MightyFX(spce_a=SPCE.GPIO_PWM)

if mighty.seven.led_r.in_use_by is None:
    mighty.seven.set_rgb(255, 0, 0)
```


## Using the Remaining Channels of a Partial Output

With port B declared for PWM, output 3 loses only its red channel. Green and blue stay live and can
be driven individually, which also covers using an RGB-to-Mono adapter to treat the 21 channels
as separate LEDs:

```python
mighty = MightyFX(spce_b=SPCE.GPIO_PWM)

mighty.three.led_g.brightness(0.5)   # works
mighty.three.led_b.brightness(0.5)   # works
mighty.three.led_r.brightness(0.5)   # prints the conflict, stays dark
```


## Screen Backlights and the Servo Connectors

The SP/CE backlight pins share channels with the Servo/Strip connectors: GPIO 36 with the L
connector, GPIO 37 with the R connector. LED strips are unaffected, since WS2812 strips are
driven over PIO by the `plasma` library.

A servo declared on the same side as a screen is refused, naming both pins, so the two cannot be
set up together by accident:

```python
mighty = MightyFX(spce_a=SPCE.SCREEN, servo_l=True)   # refused
mighty = MightyFX(spce_a=SPCE.SCREEN, servo_r=True)   # fine, SP/CE B drives no screen
```

One signal on both pins is what the refusal prevents: backlight brightness changes would corrupt
the servo pulses and servo pulses would flicker the backlight. A PIO-backed servo API that avoids
the sharing altogether is planned. Building your own `machine.PWM` on GPIO 44 or 45 goes around
the refusal, so do not do it while a screen on the matching port has claimed its backlight.

An LED strip is unaffected either way, and `strip_l` beside a screen on SP/CE A is a normal thing
to declare.


## Driving Pins Yourself

The pairing is a property of the chip, not of the library, so your own `machine.PWM` objects are
subject to the same table. Which of the two declarations you use is what decides whether the board
protects you.

`SPCE.GPIO` hands over the pins and claims nothing, so putting PWM on them takes the shared
channels with no stand-in to warn you, and every output stays live. Check the table first.

`SPCE.GPIO_PWM` hands over the same pins and tells the board the four data lines will be PWM
driven, so the shared channels are claimed at construction and the LEDs on them become stand-ins
that report instead of lighting. That is what a motor driver wants, and anything else putting PWM
on the connector.


## Tiny FX

Tiny FX's RP2040 shares channels between pins 16 apart, but its allocation pairs every output
with a pin that never selects PWM, so no shipped function conflicts with another. The table above
is Mighty FX only.
