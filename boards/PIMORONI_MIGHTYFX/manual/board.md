<!-- block picker_tabs -->

Two tabs sit under the page's header. **The effects** sets the lights, screens
and sound: pick a stretch of outputs or LEDs, tap a look from the cards to play
on it, and slide its settings until it suits. A run can be cut into stretches
that each play a look of their own. **Edit board** sets up what is built: the
order the lights are wired in, how many LEDs a strip has, which size each screen
is, and a Screen Hub. The pictures, drawings and sounds on this drive are offered
on the Screens and Sound tabs, where files can be copied onto the drive and
deleted from it. Press the plus to split what you have into scenes that take
turns, each with its own looks, pictures and sound; what **Always on** holds plays
under every scene.

<!-- block entry_examples -->

```entry
out1-7: rainbow_wave speed=0.3
out3 level=50%: pulse speed=0.6
```

<!-- block naming_outputs -->

### Naming outputs

| Written | Means |
| --- | --- |
| `out1` | one output |
| `out1,3,5` | three of them |
| `out1-7` | all seven |
| `out7-1` | all seven, the other way round |
| `out2,1,5-7` | mixed, and in the order you write them |

An output shows colour. Its red, green and blue can be driven separately as
three plain lights instead:

| Written | Means |
| --- | --- |
| `out3.r` | just the red |
| `out3.*` | all three of them, red, green then blue |
| `out1-7.*` | all 21, from 1's red to 7's blue |
| `out7-1.*` | all 21 the other way round, from 7's blue to 1's red |

<!-- block setting_examples -->

```entry
out1-7 level=50%: pulse
out1-3 colour=warm: flicker
out4 colour=ff8040: static
out1 level=0.5, 2 level=0.8, 3-7: pulse_wave
out1-7 ease=0.4: blink speed=0.5
```

<!-- block strips_intro -->

A strip of WS2812 LEDs plugs into the connector marked **L** or **R**, and its
LEDs take the same effects, colours and levels the outputs do. Tell the board
how long it is first, since that is the one thing it cannot work out for itself:

<!-- block strips_notes -->

`stripR` is the same for the other connector. Both share one power supply, so a
strip on either lights the small LED between them, and anything plugged into the
one you are not using is powered too.

<!-- block screen_notes -->

A screen draws about twenty frames a second at best, and effects on the outputs
take time from it, so a file asking for more keeps its timing by dropping
frames. Ask for twenty or fewer and it plays every one.

<!-- block scene_example -->

```entry
[Evening: 30s]
out1-7: rainbow_wave speed=0.3

[Night: 10s]
out1-7 colour=warm: pulse
```

<!-- block screen_settings -->

| `screenA` | what size of screen is on SP/CE A, or `hub` for a Screen Hub | no screen |
| `screenB` | the same for SP/CE B | no screen |
| `hubA` to `hubF` | what size of screen is at each of a Screen Hub's positions | no screen there |

<!-- block strip_settings -->

| `stripL` | how many LEDs are on a strip plugged into **L**, and after a `\|` the order it takes its colours in | no strip |
| `stripR` | the same for **R** | no strip |

<!-- block examples_on_board -->

| Folder | What is in it |
| --- | --- |
| `examples/python/effects` | changing from one set of effects to another as time passes |
| `examples/python/effects/mono` | one output at a time, and the effects that travel across several |
| `examples/python/effects/colour` | the same in colour, with traffic lights and crossings |
| `examples/python/function` | the Boot button, the sensor connector and the supply voltage |
| `examples/python/infrared/mono` | effects chosen with an infrared remote |
| `examples/python/infrared/colour` | the same in colour |
| `examples/python/qwst` | light, tilt and weather from Qw/ST breakouts |
| `examples/python/screens/single` | one screen, its backlight, and finding what is attached |
| `examples/python/screens/playback` | animated GIFs and slideshows |
| `examples/python/screens/graphics` | drawing from code: text, colour wheels, a starfield |
| `examples/python/screens/images` | still pictures |
| `examples/python/screens/layout` | placing a picture on the screen |
| `examples/python/screens/pair` | two screens working together |
| `examples/python/screens/hub` | more than two, through a hub |
| `examples/python/audio` | playing a wav file |
| `examples/python/motors` | driving a pair of motors |
| `examples/python/servos` | sweeping a servo on the L connector |
| `examples/python/strips` | a rainbow along an LED strip |
| `examples/python/gpio` | using SP/CE pins as plain inputs and outputs |
| `examples/python/wireless` | colours fetched over WiFi |
| `examples/python/showcase` | larger builds that put several of these together |

Three to start with:

```entry
board: program=examples/python/effects/colour/sweep_trail.py
board: program=examples/python/screens/playback/animated_gif.py
board: program=examples/python/showcase/flip_dot_sign.py
```

Anything under `screens`, `audio`, `motors`, `servos`, `strips`, `infrared` or
`qwst` needs that hardware attached, `wireless` needs a WiFi network, and some of
the showcase ones want pictures or a network of their own.
