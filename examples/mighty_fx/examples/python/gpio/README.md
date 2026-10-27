# Mighty FX Micropython GPIO Examples <!-- omit in toc -->

These are micropython examples for using Mighty FX's SP/CE ports as general purpose inputs and outputs.

- [Examples](#examples)
  - [SP/CE Buttons](#spce-buttons)
  - [SP/CE GPIO](#spce-gpio)
  - [SP/CE PWM Fade](#spce-pwm-fade)


## Examples

### SP/CE Buttons
[spce_buttons.py](spce_buttons.py)

Read buttons wired to a SP/CE port's five pins, brightening an RGB output while each is held.

### SP/CE GPIO
[spce_gpio.py](spce_gpio.py)

Borrow a SP/CE connector's five pins as general purpose outputs, and chase a high along them.

### SP/CE PWM Fade
[spce_pwm_fade.py](spce_pwm_fade.py)

Fade four LEDs on a SP/CE port's data lines with PWM, and report which output channels that costs.
