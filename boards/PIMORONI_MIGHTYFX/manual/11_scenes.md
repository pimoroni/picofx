## Scenes

A file can hold several sets of effects and show them one after another. A
heading in square brackets begins one, and says how long it shows for:

```entry
[Evening: 30s]
out1-7: rainbow_wave speed=0.3

[Night: 10s]
out1-7 colour=warm: pulse
```

The name is everything before the `:` and may be anything you like, spaces
included. The time is in seconds, `30s`, or in minutes, `10m`. Scenes take turns
in the order they are written, then start again.

Entries before the first heading are always on, whatever is showing, so anything
that should never change goes there:

```entry
out1: static brightness=0.2
```

While a scene shows, an output it does not name goes dark if any other scene
uses it, and is left alone if none of them do. A scene may name an output that
is always on, and takes it over for as long as it shows.

A screen behaves the same way: its picture stays put but the light goes out
while another scene has the board, and comes back when its own returns.

Add `restart` to a heading and its effects begin again every time it comes
round, instead of carrying on from where they were left:

```entry
[Beacon: 5s restart]
out1-3: flash_sequence flashes=3
```

The board entry belongs outside every scene. A single scene with no time simply
shows for ever, and ejecting this drive always starts again at the first scene.
