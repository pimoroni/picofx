# Changelog

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
