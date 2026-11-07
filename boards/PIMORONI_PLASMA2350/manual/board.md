<!-- block picker_tabs -->

The picker has two tabs, **The effects** and **A program**. **The effects**
controls the strips, the board's LED and the screen: select a stretch of LEDs,
choose a look from the cards, and adjust its settings. A strip can be split into
stretches, each playing its own look. **Edit board**, at the end of the lights'
tabs, sets up your hardware: which strips are fitted, the number of LEDs on
each, and the screen's size. The Screens tab lists the pictures and drawings on
this drive, and can copy files onto the drive or delete them. Press **+** to
split your setup into scenes that play one after another, each with its own looks and
pictures. Anything on the **Always on** tab plays under every scene.

<!-- block entry_examples -->

```entry
stripDat: rainbow_wave speed=0.3 length=30
rgb level=50%: pulse speed=0.6
```

<!-- block naming_outputs -->

The RGB LED on the board is `rgb`, and takes any effect. The LEDs of a strip are
named under [LED strips](#led-strips).

```entry
rgb: rainbow speed=0.3
```

<!-- block setting_examples -->

```entry
stripDat level=50%: pulse
stripDat1-30 colour=warm: flicker
rgb colour=ff8040: static
stripDat ease=0.4: blink speed=0.5
```

<!-- block strips_intro -->

The two screw terminals are marked **DAT** and **CLK**. A WS2812 strip needs
only a data line, so one can go on each terminal: `stripDat` and `stripClk`. An
APA102 strip needs both data and clock, so it is the only strip on the board,
`stripApa`. A strip's LEDs take the same effects, colours and levels as the
board's LED. First tell the board how many LEDs each strip has, as it cannot
detect this:

<!-- block strips_notes -->

`stripClk` and `stripApa` are set the same way. An APA102 strip also has an overall
brightness, about half by default, set after its length on the board line, such as
`stripApa=144|75%`. The effects' own levels apply on top of it.

`stripApa` and the WS2812 strips cannot play at once, since they use the same
terminals. A file naming both plays the WS2812 strips and reports the
conflict in `errors.txt`.

<!-- block screen_notes -->

The Plasma 2350 W has no SP/CE connector, so it takes no screen, and the picker
offers none.

A 2.8 inch panel is mounted upright, 240 wide by 320 tall, so a landscape
picture is cropped at the sides unless the line rotates it with
`rotation=90`.

<!-- block scene_example -->

```entry
[Daytime: 30s]
stripDat: rainbow_wave speed=0.3

[Night: 2m]
stripDat colour=ff5a00: flicker_each
```

<!-- block screen_settings -->

| `screen` | the size of the screen on the SP/CE connector | no screen |

<!-- block strip_settings -->

| `stripDat` | the number of LEDs on a WS2812 strip on **DAT**, then after a `\|` its colour order | no strip |
| `stripClk` | the same for **CLK** | no strip |
| `stripApa` | the number of LEDs on an APA102 strip across both terminals, then after a `\|` its brightness | no strip |
