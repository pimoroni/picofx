<!-- block picker_tabs -->

The picker has two tabs, **The effects** and **A program**. **The effects**
controls the lights, screens and sound: select a stretch of outputs or LEDs,
choose a look from the cards, and adjust its settings. A run can be split into
stretches, each playing its own look. **Edit board**, at the end of the lights'
tabs, sets up your hardware: the order the lights are wired in, the number of
LEDs on each strip, each screen's size, and a Screen Hub. The Screens and Sound
tabs list the pictures, drawings and sounds on this drive, and can copy files
onto the drive or delete them. Press **+** to split your setup into scenes that
play in turn, each with its own looks, pictures and sound. Anything on the
**Always on** tab plays under every scene.

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
| `out7-1` | all seven, in reverse order |
| `out2,1,5-7` | a mix, played in the order written |

Each output is a colour light. Its red, green and blue channels can also be
driven separately, as three mono lights:

| Written | Means |
| --- | --- |
| `out3.r` | the red channel only |
| `out3.*` | all three channels, in the order red, green, blue |
| `out1-7.*` | all 21, from 1's red to 7's blue |
| `out7-1.*` | all 21 in reverse order, from 7's blue to 1's red |

<!-- block setting_examples -->

```entry
out1-7 level=50%: pulse
out1-3 colour=warm: flicker
out4 colour=ff8040: static
out1 level=0.5, 2 level=0.8, 3-7: pulse_wave
out1-7 ease=0.4: blink speed=0.5
```

<!-- block strips_intro -->

A WS2812 LED strip plugs into the connector marked **L** or **R**, and its LEDs
take the same effects, colours and levels as the outputs. First tell the board
how many LEDs the strip has, as it cannot detect this:

<!-- block strips_notes -->

`stripR` does the same for the other connector. Both connectors share one power
supply, so a strip on either lights the small LED between them, and the unused
connector is powered too.

<!-- block screen_notes -->

A screen updates less often than the lights, and effects on the outputs take
time from it. If a file asks for more frames than the screen can draw, it drops
frames to keep its timing.

<!-- block scene_example -->

```entry
[Evening: 30s]
out1-7: rainbow_wave speed=0.3

[Night: 10s]
out1-7 colour=warm: pulse
```

<!-- block screen_settings -->

| `screenA` | the size of the screen on SP/CE A, or `hub` for a Screen Hub | no screen |
| `screenB` | the size of the screen on SP/CE B | no screen |
| `hubA` to `hubF` | the size of the screen at each Screen Hub position | no screen there |

<!-- block strip_settings -->

| `stripL` | the number of LEDs on the strip plugged into **L**, then after a `\|` its colour order | no strip |
| `stripR` | the same for **R** | no strip |

<!-- block examples_on_board -->

| Folder | What is in it |
| --- | --- |
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
| `examples/python/servos` | servos on the L and R connectors, alone, in a pair and steered by remote |
| `examples/python/strips` | a rainbow along an LED strip, and filling one an LED at a time |
| `examples/python/gpio` | using SP/CE pins as plain inputs and outputs, and fading LEDs on them |
| `examples/python/wireless` | colours fetched over WiFi |
| `examples/python/comms` | several boards working together |
| `examples/python/showcase` | larger builds that put several of these together |

Three to start with:

```entry
board: program=examples/python/effects/colour/sweep_trail.py
board: program=examples/python/screens/playback/animated_gif.py
board: program=examples/python/showcase/flip_dot_sign.py
```

Examples under `screens`, `audio`, `motors`, `servos`, `strips`, `gpio`,
`infrared` or `qwst` need that hardware attached. `wireless` needs a WiFi
network, `comms` needs a second board, and some showcase examples need their
own pictures or network.
