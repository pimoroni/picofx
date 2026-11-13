<!-- block picker_tabs -->

```picker
header: Plasma 2350 Picker
pages: *Effects, Programs
tabs: *DAT strip, CLK strip, ~APA102 strip, LED=Rainbow, Screens=2.8"
```

Under **Effects** you'll find **DAT strip**, **CLK strip** and **APA102 strip**
for the strips, **LED** for the board's own light, and **Screens**. Each tab
shows a small preview of what it's playing, and [[Edit board]] sits at the end
of the row.

<!-- block picker_first_look -->

When your board is new, the picker opens on **DAT strip** with all 66 LEDs as one
stretch, playing nothing yet. The board's own LED, on the **LED** tab, plays
Rainbow.

```picker
badge strip: Strip, 66 LEDs, GRB
strip: *Nothing 66
choose: LEDs 1 to 66 of the strip on DAT
cards Along the lights: Rainbow, Wave, Scanner, Chase, Marquee, *Nothing
```

<!-- block picker_first_cut -->

Choose Rainbow first, then try a cut about halfway along. You'll have two
stretches, both playing Rainbow. Click the right-hand one, press Change look and
choose Scanner, and a light starts sweeping along that half.

```picker
badge strip: Strip, 66 LEDs, GRB
strip: Rainbow 33, *Rainbow 33
choose: LEDs 34 to 66 of the strip on DAT, Rainbow
cards Along the lights: *Rainbow, Wave, Scanner, Chase, Marquee
```

<!-- block picker_board -->

```picker
tabs editing: *DAT strip, CLK strip, ~APA102 strip, LED=Rainbow, Screens=2.8"
stripsetup: 66
```

Choose which strips are fitted, then set how many LEDs each has and its colour
order, which needs changing if red shows as another colour. An APA102 strip uses
both terminals, so it replaces the other two. On **Screens**, set the size of
the screen.

<!-- block picker_screens_picture -->

```picker
screen: 2.8 inch, logo.png
pictures: logo.png=A, sunset.jpg, waves.gif
```

<!-- block picker_programs_picture -->

```picker
pages: Effects, *Programs=My lights
note: my_lights.py
programs On the drive | your own programs: *My lights
```

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
