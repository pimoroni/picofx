## Scenes

A file can hold several sets of effects and show them one after another. A
heading in square brackets begins one, and says how long it shows for:

```entry
[Evening: 30s]
out1-6: pulse_wave speed=0.3
rgb: rainbow speed=0.2

[Night: 10s]
out1-6: flicker_each
rgb colour=warm: pulse
```

The time is in seconds, `30s`, or in minutes, `10m`. Scenes take turns in the
order they are written, then start again. Entries before the first heading are
always on, whatever is showing. Add `restart` to a heading and its effects begin
again every time it comes round.
