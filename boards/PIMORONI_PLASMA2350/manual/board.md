<!-- block picker_tabs -->

Two tabs sit under the page's header. **The effects** sets the strips, the
board's LED and the screen: pick a stretch of LEDs, tap a look from the cards to
play on it, and slide its settings until it suits. A strip can be cut into
stretches that each play a look of their own. **Edit board** sets up what is
built: which strips are fitted, how many LEDs each has, and which size the
screen is. The pictures and drawings on this drive are offered on the Screens
tab, where files can be copied onto the drive and deleted from it. Press the plus
to split what you have into scenes that take turns, each with its own looks and
pictures; what **Always on** holds plays under every scene.

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
APA102 strip needs both, data and clock, so it is the one strip on the board,
`stripApa`. A strip's LEDs take the same effects, colours and levels the board's
LED does. Tell the board how long a strip is first, since that is the one thing
it cannot work out for itself:

<!-- block strips_notes -->

`stripClk` and `stripApa` are named the same way. An APA102 strip has a
brightness of its own for the whole strip, at 50% unless the board line says
otherwise, such as `stripApa=144|75%`. The effects' own levels apply on top of
it.

`stripApa` and the WS2812 strips cannot play at once, since they use the same
terminals. A file naming both plays the WS2812 strips and says so in
`errors.txt`.

<!-- block screen_notes -->

The Plasma 2350 W has no SP/CE connector, so it takes no screen, and the picker
offers none.

The panel is mounted upright, 240 wide by 320 tall, so a landscape picture is
cropped at its sides unless the line turns it, with `rotation=90`.

**A limit for now.** The board's memory is small, and what the last file showed
can keep its room until a restart. Saving a change from one full-size picture
to another is refused with a note in `errors.txt`; turn the board off and on
with the new file saved and it plays. Animations under about 60KB of frames,
small pictures, and drawings with `pixel_double=true` change over without a
restart. The lights are never affected.

<!-- block scene_example -->

```entry
[Daytime: 30s]
stripDat: rainbow_wave speed=0.3

[Night: 2m]
stripDat colour=ff5a00: flicker_each
```

<!-- block screen_settings -->

| `screen` | what size of screen is on the SP/CE connector | no screen |

<!-- block strip_settings -->

| `stripDat` | how many LEDs are on a WS2812 strip on **DAT**, and after a `\|` the order it takes its colours in | no strip |
| `stripClk` | the same for **CLK** | no strip |
| `stripApa` | how many LEDs are on an APA102 strip across both terminals, and after a `\|` its brightness | no strip |
