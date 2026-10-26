# Changelog

1.1.3
-----

**PicoFX library**

* Breaking: `target_ms`, `target_fps`, `measured_ms` and `measured_fps` are now properties
* Breaking: TrafficLightFX drops `fade_rate` and `amber_flashing`, for `curves` and PelicanCrossingFX
* Add ChromaticPlayer, shared by ColourPlayer and StripPlayer, with `colours` to tint a mono effect
* Add `levels` and `curves` to every player, with `ease()` and `fade()` to make a curve
* Add DisabledLED, for an LED that cannot light as another pin uses its PWM channel
* Add `in_use_by` to every LED, and `leds`, `on()` and `off()` to RGBLED
* Add PelicanCrossingFX, SweepFX, FlickerEachFX and RandomEachFX
* Add NAME, CALLED and TAKES to every effect, saying what it is called and what settings it takes
* Add ORANGE, PURPLE and PINK, with their HSV forms
* `start()` rounds its rate to the nearest millisecond, and a paired chain shares it
* Effects keep their speed at every frame rate
* A timer callback arriving after `stop()` no longer updates the LEDs
* The players and colour effects allocate less and draw faster
* A setter given too many values says how many it was given
* package.json lists every module, and the package includes the licence

**Tiny FX**

* Breaking: `i2c` and `wav` raise when the board was created without them, where `wav` was None and `i2c` was missing
* Built on Pimoroni's MicroPython `fx-1.29.0`, with the interpreter's hottest code and the float routines in SRAM
* Add `sensor=`, taking `ANALOG`, `PIR` or `IR` from the new `sensor` module, and `sensor` handing back what it built
* Add `boot_taps()`, counting presses caught by interrupt so a quick tap is not missed
* Add the `timing` module, with `Pacer` holding a loop to a rate and `Roller` saying when something is next due
* The WAV player fades tones and 16-bit WAVs in and out, resumes from `position()`, and turns the amplifier off while silent
* The multi sensor stick's accelerometer and the QwSTPad are frozen into the firmware
* A board that fails partway through being built hands back what it had claimed
* The libraries and examples zips attach to a GitHub release
* The examples move into `examples/python/`
* The examples using the sensor connector take what it holds from `sensor=`
* The sensor and voltage meters and the sensor wave keep their rate with `Pacer`
* Fixed the I2C target example raising as it ends, and answering at an address the multi board example does not look for

1.1.2
-----

**PicoFX library**

* Add `target_ms()`, `target_fps()`, `measured_ms()` and `measured_fps()` to the players, to show whether they keep up
* Add PseudoLED, which stores a brightness without driving a pin, for comms to send. PWMLED builds on it and RGBLED takes it
* Fixed PWMLED raising on `toggle()` before a brightness was set

**Tiny FX**

* Add comms, so one board drives another's outputs over I2C, with examples for two boards and for several
* Add `i2c_freq` to set the I2C bus speed
* Fixed `shutdown()` raising when built with `init_wav=False`

1.1.1
-----

* Include build files for release on PyPi

1.1.0
-----

* fixed error in docs
* Readme: add programming info
* Micropython 1.26 Update
* Add the Pimoroni AyeArr library to TinyFX builds, and  bump MP to v1.27
* Clean up patches no longer needed for newest Micropython
* Bump to v1.28 of Micropython
* Add examples for using Aye Arr with Tiny FX by
