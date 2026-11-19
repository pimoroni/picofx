# Changelog

1.2.0
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

**autofx module**

* Add autofx, which reads an effects file and plays it on a board's outputs, strips, screens and speaker, reporting each line it cannot use in errors.txt with what to write instead
* An effects file sets each output's effect and settings, with levels, colours, fades and eases, plays scenes in turn, and shows pictures, animations and drawings on Mighty FX's screens
* A sound takes a `volume`, and a scene can set its screens or sound to `none`
* A scene can name the scene that follows it with `then`, and the IR remote and PIR Stick can start a scene through `remote:` and `motion:` entries

**FX drive**

* Add the FX drive, a USB drive holding effects.txt that the board plays at power on and again a few seconds after each save
* Add FX drive builds of Tiny FX, Tiny FX W, Mighty FX and Plasma 2350
* Each drive build comes with a -full uf2 that writes the whole board, FX drive included, and a -with-libs uf2 that updates the firmware and libraries and keeps the drive
* A drive build writes its own main.py, which lights the outputs dim with `wake()` while autofx loads, and a wireless board's drive holds the WiFi credentials file
* Add the timezones library, giving the UTC offset for the `TIME_ZONE` set in the WiFi credentials file, summer time included
* Pressing BOOT twice hides the drive, and twice again brings it back
* The WAV player fades out while a computer writes to the FX drive, and returns once it finishes
* The outputs show a bar while autofx loads the effects file
* The FX drive carries the picker, a web page opened from the drive in Chrome or Edge, which chooses and previews effects and saves them to the board
* It also carries a text editor that offers each effect and setting as you type, and a manual of every effect and setting, both opened in a browser
* The FX drive keeps pictures, drawings and sounds in their own folders and the user's programs in `programs`, making each where it is missing
* The picker's Programs tab copies an example into `programs` to be changed, and duplicates or deletes the user's own programs
* A drawing can offer styles, chosen with `style=` in the effects file or in the picker, which shows a thumbnail of each
* Two screens can show one picture or drawing together, written as `screenA,B` in the effects file or chosen with the picker's Paired toggle
* The picker has a Sensor tab for the IR remote and PIR Stick, a volume for each sound, and scene cards that choose how each scene ends
* The picker says when newer firmware is released for the board, and offers the one file the board needs, with what's new and how to install it
* The picker's Discover buttons download more example programs, pictures, drawings and sounds from GitHub, and Check for updates fetches newer versions, keeping a changed copy in `programs`
* Discover offers Mighty FX and Tiny FX 72 looping example sounds from fx-sounds, from sirens, alarms and train horns to engines, sci-fi effects and ambience, and the Sound tab links to its gallery for more
* Deleting an example program in the picker also deletes the folder of modules it brings, such as the hub clock's faces
* Each FX drive build carries the example programs worth running as demos, with Mighty FX's pictures and drawings, and Discover offers the rest
* The picker, editor and manual link to help and to a problem report that fills in the board and firmware version
* tools/build_editor.py and tools/build_manual.py build each board's picker and manual from shared parts, and CI checks every board's are rebuilt
* tools/build_examples_index.py writes each board's examples index for Discover, and CI checks it is current

**Tiny FX**

* Breaking: `i2c` and `wav` raise when the board was created without them, where `wav` was None and `i2c` was missing
* Built on Pimoroni's MicroPython `fx-1.29.0`, with the interpreter's hottest code and the float routines in SRAM
* Add `sensor=`, taking `ANALOG`, `PIR` or `IR` from the new `sensor` module, and `sensor` handing back what it built
* Add `boot_taps()`, counting presses caught by interrupt so a quick tap is not missed
* Add the `timing` module, with `Pacer` holding a loop to a rate and `Roller` saying when something is next due
* Add `volume` to the WAV player, for tones and 16-bit WAVs
* The WAV player fades tones and 16-bit WAVs in and out, resumes from `position()`, and turns the amplifier off while silent
* The multi sensor stick's accelerometer and the QwSTPad are frozen into the firmware
* A board that fails partway through being built hands back what it had claimed
* The uf2s and the libraries and examples zips attach to a GitHub release, named for its tag as release files have been
* Fixed WAV files with tags before their audio not playing
* The examples move into `examples/programs/`
* The examples using the sensor connector take what it holds from `sensor=`
* The sensor and voltage meters and the sensor wave keep their rate with `Pacer`
* The examples gain PelicanCrossingFX, SweepFX with and without a trail, a WAV player, counting taps, and light, temperature and spirit level readings from Qw/ST sensors
* Fixed the I2C target example raising as it ends, and answering at an address the multi board example does not look for

**Mighty FX**

* Add Mighty FX, an RP2350 board with seven RGB outputs, two SP/CE connectors, L and R connectors, a sensor connector and audio, built on Pimoroni's MicroPython `fx-1.29.0` with its heap in PSRAM
* Each SP/CE connector is declared for its role, `SPCE.SCREEN`, `SPCE.GPIO`, `SPCE.GPIO_PWM`, `SPCE.HUB_SELECTS` or `SPCE.MOTOR_DRIVER`, and a screen connector beside a `HUB_SELECTS` one builds a Screen Hub
* Screens are driven by the spidisplay module, with picovector for drawing and fonts held in a ROMFS
* The L and R connectors take an LED strip or a servo each, on a shared rail that stays off until `enable_rail()`
* Servos and motor drivers run on PIO clusters, so they take no PWM channel from the outputs or the screens
* An output whose PWM channel a `SPCE.GPIO_PWM` connector takes becomes a `DisabledLED`, which says why when asked to light
* Mighty FX answers on I2C as an FX target, and `MightyFXControl` drives one from another board
* Networking, Bluetooth and `lte` for a Clipper are frozen into the firmware, and `spce` with its `MotorDriver` is copied to `/lib`
* `STRIPS` and `SCREENS` name the board's strip connectors and screen ports
* Add the Mighty FX examples for its onboard functions, effects and audio
* Add the Mighty FX examples for the IR remote, Qw/ST sensors, WiFi and comms
* Add the Mighty FX examples for motor drivers, servos, LED strips and GPIO
* Add the Mighty FX examples for screens and the Screen Hub, with the pictures they show, most taking a 1.54" screen as well as a 2.8" and a rotation in args
* Add the Mighty FX showcases, bringing the examples together as projects
* Example drawings of the showcase signs and scenes come with a picture of each and play from a `drawing` entry or the picker's Screens tab
* Add the hub clock showcase, a digit on each of a Screen Hub's screens in eight styles, showing the time in `TIME_ZONE` when it can reach the internet over WiFi

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
