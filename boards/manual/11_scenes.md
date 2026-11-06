## Scenes

A file can hold several sets of effects, called scenes, and play them one
after another. A heading in square brackets starts each scene and sets how
long it plays:

<!-- board scene_example -->

The name is everything before the `:` and can be anything, including spaces. The
time is in seconds, `30s`, or minutes, `10m`. Scenes play in the order written,
then repeat.

Entries before the first heading are always on, whichever scene is playing, so
put anything that should never change there:

```entry
__ONE_OUTPUT__: static brightness=0.2
```

While a scene plays, an __OUTPUT__ it does not name goes dark if another scene
uses it, and is left alone otherwise. A scene can name an always-on __OUTPUT__ and
takes it over while the scene plays.

<!-- if screens -->
Screens behave the same way: the picture stays, but the backlight turns off
while another scene plays, and comes back when its own scene returns.
<!-- end -->

Add `restart` to a heading to restart that scene's effects each time it
plays, instead of resuming where they left off:

```entry
[Beacon: 5s restart]
__THREE_OUTPUTS__: flash_sequence flashes=3
```

The board entry goes before any scene heading. A single scene with no time plays
forever, and every reload, whether from a save, an eject or a press of **Boot**,
starts again from the first scene.
