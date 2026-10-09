<!-- block picker_tabs -->

Two tabs sit under the page's header. **The effects** sets the lights and
sound: pick a stretch of outputs, tap a look from the cards to play on it, and
slide its settings until it suits. A run can be cut into stretches that each
play a look of their own. **Edit board** sets the order the lights are wired in,
and moving the RGB output across to the mono side breaks it into three plain
lights. The sounds on this drive are offered on the Sound tab, where files can
be copied onto the drive and deleted from it. Press the plus to split what you
have into scenes that take turns, each with its own looks and sound; what
**Always on** holds plays under every scene.

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
| `out6-1` | all six, the other way round |
| `out2,1,5-6` | mixed, and in the order you write them |
| `rgb` | the RGB output |

The RGB output shows colour. Its red, green and blue can be driven separately as
three plain lights instead, and named alongside the others:

| Written | Means |
| --- | --- |
| `rgb.r` | just the red |
| `rgb.*` | all three of them, red, green then blue |
| `out1-6,rgb.*` | all nine plain lights |

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
| `examples/effects/mono` | one output at a time, and the effects that travel across several |
| `examples/effects/colour` | the RGB output |
| `examples/function` | the button, the sensor connector and the supply voltage |
| `examples/infrared/mono` | effects chosen with an infrared remote |
| `examples/infrared/colour` | the same on the RGB output |
| `examples/qwst` | light, tilt and weather from Qw/ST breakouts |
| `examples/audio` | sound alongside the lights |
| `examples/comms` | several boards working together |
| `examples/showcase` | larger builds that put several of these together |

Three to start with:

```entry
board: program=examples/effects/mono/sweep_trail.py
board: program=examples/effects/colour/rainbow.py
board: program=examples/showcase/ship_thrusters.py
```

Anything under `infrared` or `qwst` needs that hardware attached, and `comms`
wants a second board. The audio examples' sounds are not on the board, to leave
this drive its room.
