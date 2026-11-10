<!-- block picker_tabs -->

```picker
header: Mighty FX Picker
pages: *Effects, Programs
tabs: *Outputs=Rainbow, Left strip, Right strip, Screens=2.8" 1.54", Sound
```

Under **Effects** you'll find a tab for each part of the board. **Outputs**,
**Left strip** and **Right strip** are for the lights, followed by **Screens** and
**Sound**. Each tab shows a small preview of what it's playing, and [[Edit board]]
sits at the end of the row.

<!-- block picker_first_look -->

When your board is new, the picker opens on **Outputs** with all seven outputs as
one stretch, playing Rainbow.

```picker
badge: Wiring, every output is one colour light
colour: *Rainbow 7
tools:
settings: Rainbow, on outputs 1 to 7, Brightness 100, Speed 45, Spread 50
cards Along the lights: *Rainbow, Wave, Scanner, Chase, Marquee
```

<!-- block picker_first_cut -->

Try it between lights 4 and 5. You'll have two stretches, both still playing
Rainbow. Click the right-hand one and choose Solid, and lights 5 to 7 turn
yellow.

```picker
colour: Rainbow 4, *Solid 3
tools:
settings: Solid, on outputs 5 to 7, colour yellow, Brightness 100
cards All together: *Solid, Colour cycle, Colour steps, Breathe, Blink
```

<!-- block picker_board -->

```picker
tabs editing: *Outputs=Rainbow, Left strip, Right strip, Screens=2.8" 1.54", Sound
badge: Wiring, every output is one colour light | Drag each light to match its position in your build. Arrows split an output into three mono lights, or rejoin them.
wiring Rainbow: 1, 2, 3, 4, 5, 6, 7
```

On **Outputs**, drag each light to match where it sits in your build, so a look
that travels moves the right way. The arrows split an output into three mono
lights, or join them back into one colour light.

On **Left strip** and **Right strip**, set how many LEDs each strip has and its
colour order, which needs changing if red shows as another colour. The cross
removes a strip you haven't fitted.

```picker
tabs editing: Outputs=Rainbow, *Left strip, Right strip, Screens=2.8" 1.54", Sound
stripsetup: 30
```

On **Screens**, choose a screen on each connector or a Screen Hub across both,
and the size of each screen.

<!-- block picker_screens_picture -->

```picker
screenmode:
screen A: 2.8 inch, skyline.png
screen B: 1.54 inch, pirate_coin.gif
pictures: acrylic_lixie, skyline.png=A, gold_macaw_card.png, medscan.gif, pirate_coin.gif=B
```

<!-- block picker_programs_picture -->

```picker
pages: Effects, *Programs=Flip dot sign
note: flip_dot_sign.py
hero: Flip dot sign | Draw a flip-dot sign that spells its message by flipping one column of dots at a time. | examples/programs/showcase/retro_displays/flip_dot_sign.py, built in
with: screen, 2 screens, hub, remote, servos
programs Retro displays | mechanical, glowing and segment displays: Acrylic lixie, CRT terminal, *Flip dot sign, Lamp matrix, Nixie tube
```

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
| `examples/programs/effects/mono` | one output at a time, and the effects that travel across several |
| `examples/programs/effects/colour` | the same in colour, with traffic lights and crossings |
| `examples/programs/function` | the Boot button, the sensor connector and the supply voltage |
| `examples/programs/infrared/mono` | effects chosen with an infrared remote |
| `examples/programs/infrared/colour` | the same in colour |
| `examples/programs/qwst` | light, tilt and temperature from Qw/ST breakouts |
| `examples/programs/screens/single` | one screen, its backlight, and finding what is attached |
| `examples/programs/screens/playback` | animated GIFs and slideshows |
| `examples/programs/screens/graphics` | drawing from code: text, colour wheels, a starfield |
| `examples/programs/screens/images` | still pictures |
| `examples/programs/screens/layout` | placing a picture on the screen |
| `examples/programs/screens/pair` | two screens working together |
| `examples/programs/screens/hub` | more than two, through a hub |
| `examples/programs/audio` | playing a WAV file |
| `examples/programs/motors` | driving a pair of motors |
| `examples/programs/servos` | servos on the L and R connectors, alone, in a pair and steered by remote |
| `examples/programs/strips` | a rainbow along an LED strip, and filling one an LED at a time |
| `examples/programs/gpio` | using SP/CE pins as plain inputs and outputs, and fading LEDs on them |
| `examples/programs/wireless` | colours fetched over WiFi |
| `examples/programs/comms` | several boards working together |
| `examples/programs/showcase` | larger builds that put several of these together |

Three to start with:

```entry
board: program=examples/programs/effects/colour/sweep_trail.py
board: program=examples/programs/screens/playback/animated_gif.py
board: program=examples/programs/showcase/retro_displays/flip_dot_sign.py
```

Examples under `screens`, `audio`, `motors`, `servos`, `strips`, `gpio`,
`infrared` or `qwst` need that hardware attached. `wireless` needs a WiFi
network, `comms` needs a second board, and some showcase examples need their
own pictures or network.
