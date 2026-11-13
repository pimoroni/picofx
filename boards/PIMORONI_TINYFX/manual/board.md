<!-- block picker_tabs -->

```picker
header: Tiny FX Picker
pages: *Effects, Programs
tabs: *Outputs=mono Wave, Sound
```

Under **Effects** you'll find **Outputs** for the lights and **Sound** for the
speaker. Each tab shows a small preview of what it's playing, and [[Edit board]]
sits at the end of the row.

<!-- block picker_first_look -->

When your board is new, the picker opens on **Outputs**. The six mono outputs are
one stretch playing Wave, and the RGB output has a stretch of its own playing
Rainbow.

```picker
badge: Wiring, the RGB output is one colour light
mono: *Wave 6
colour RGB: Rainbow 1
settings: Wave, on outputs 1 to 6, Brightness 100, Speed 45, Spread 50
```

<!-- block picker_first_cut -->

Try it between mono lights 3 and 4. You'll have two stretches, both still playing
Wave. Click the right-hand one, press Change look and choose Sparkle, and lights
4 to 6 start to twinkle.

```picker
mono: Wave 3, *Wave 3
colour RGB: Rainbow 1
choose: outputs 4 to 6, Wave
cards mono Individual: Sparkle, Counter, Traffic light, Pelican crossing
```

<!-- block picker_board -->

```picker
tabs editing: *Outputs=mono Wave, Sound
badge: Wiring, the RGB output is one colour light | Drag each light to match its position in your build.
wiring mono Wave: 1, 2, 3, 4, 5, 6 | RGB
```

Drag each light to match where it sits in your build, so a look that travels
moves the right way. The arrow on the RGB output moves it across to the mono side
as three mono lights, or brings them back as one colour light.

<!-- block picker_programs_picture -->

```picker
pages: Effects, *Programs=Ship thrusters
note: ship_thrusters.py
with: remote, Qw/ST, speaker
programs Model lighting | thrusters, beacons and lit postcards: Rescue vehicle, *Ship thrusters, Space tales
```

<!-- block entry_examples -->

```entry
out1-6: pulse_wave speed=0.3
rgb: rainbow speed=0.5
out3 level=50%: pulse speed=0.6
```

<!-- block naming_outputs -->

### Naming outputs

| Written | Means |
| --- | --- |
| `out1` | one output |
| `out1,3,5` | three of them |
| `out1-6` | all six |
| `out6-1` | all six, in reverse order |
| `out2,1,5-6` | a mix, played in the order written |
| `rgb` | the RGB output |

The RGB output is a colour light. Its red, green and blue channels can also be
driven separately, as three mono lights named alongside the others:

| Written | Means |
| --- | --- |
| `rgb.r` | the red channel only |
| `rgb.*` | all three channels, in the order red, green, blue |
| `out1-6,rgb.*` | all nine mono lights |

<!-- block setting_examples -->

```entry
out1-6 level=50%: pulse
rgb colour=warm: flicker
out1-6 ease=0.4: blink speed=0.5
```

<!-- block scene_example -->

```entry
[Evening: 30s]
out1-6: pulse_wave speed=0.3
rgb: rainbow speed=0.2

[Night: 10s]
out1-6: flicker_each
rgb colour=warm: pulse
```

<!-- block examples_on_board -->

| Folder | What is in it |
| --- | --- |
| `examples/programs/effects/mono` | one output at a time, and the effects that travel across several |
| `examples/programs/effects/colour` | the RGB output |
| `examples/programs/function` | the button, the sensor connector and the supply voltage |
| `examples/programs/infrared/mono` | effects chosen with an infrared remote |
| `examples/programs/infrared/colour` | the same on the RGB output |
| `examples/programs/qwst` | light, tilt and temperature from Qw/ST breakouts |
| `examples/programs/audio` | sound alongside the lights |
| `examples/programs/comms` | several boards working together |
| `examples/programs/wireless` | colours fetched over WiFi, on the Tiny FX W |
| `examples/programs/showcase` | larger builds that put several of these together |

Three to start with:

```entry
board: program=examples/programs/effects/mono/sweep_trail.py
board: program=examples/programs/effects/colour/rainbow.py
board: program=examples/programs/showcase/ship_thrusters.py
```

Examples under `infrared` or `qwst` need that hardware attached, `wireless` needs a WiFi network,
and `comms` needs a second board. The audio examples' sounds are not included, to save space on
this drive.
