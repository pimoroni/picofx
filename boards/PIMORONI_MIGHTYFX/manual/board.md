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

Colours by name: red, orange, yellow, green, cyan, blue, purple, magenta, pink,
warm, white, cool, black. Or the hex a colour picker gives you, with its `#`
left off, as `out4` above uses for an orange paler than the named one. A `#`
always starts a comment, so one left on a colour hides the rest of the line.

<!-- block fade_and_ease -->

### Fade and ease

`fade` and `ease` take the seconds a change takes to get there. `fade` crosses
evenly, which is what a stage light does; `ease` goes quickly at first and slows
as it arrives, which is how a bulb warms and is the one that looks natural on a
light switching on and off.

An output follows one way or the other, so a line takes one of them and not
both. Two numbers divided by `|` give the rise and the fall their own lengths,
a light that comes on quickly and fades out slowly being the usual reason:

```entry
out1-7 fade=0.8: blink speed=0.5
out1-3 ease=0.05|1.2: blink speed=1
```

Softening belongs to the output, not to the effect, so it works on any effect.

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
| `examples/effects` | changing from one set of effects to another as time passes |
| `examples/effects/mono` | one output at a time, and the effects that travel across several |
| `examples/effects/colour` | the same in colour, with traffic lights and crossings |
| `examples/function` | the Boot button, the sensor connector and the supply voltage |
| `examples/infrared/mono` | effects chosen with an infrared remote |
| `examples/infrared/colour` | the same in colour |
| `examples/qwst` | light, tilt and weather from Qw/ST breakouts |
| `examples/screens/single` | one screen, its backlight, and finding what is attached |
| `examples/screens/playback` | animated GIFs and slideshows |
| `examples/screens/graphics` | drawing from code: text, colour wheels, a starfield |
| `examples/screens/images` | still pictures |
| `examples/screens/layout` | placing a picture on the screen |
| `examples/screens/pair` | two screens working together |
| `examples/screens/hub` | more than two, through a hub |
| `examples/audio` | playing a wav file |
| `examples/motors` | driving a pair of motors |
| `examples/servos` | sweeping a servo on the L connector |
| `examples/strips` | a rainbow along an LED strip |
| `examples/gpio` | using SP/CE pins as plain inputs and outputs |
| `examples/wireless` | colours fetched over WiFi |
| `examples/showcase` | larger builds that put several of these together |

Three to start with:

```entry
board: program=examples/effects/colour/sweep_trail.py
board: program=examples/screens/playback/animated_gif.py
board: program=examples/showcase/flip_dot_sign.py
```

Anything under `screens`, `audio`, `motors`, `servos`, `strips`, `infrared` or
`qwst` needs that hardware attached, `wireless` needs a WiFi network, and some of
the showcase ones want pictures or a network of their own.
