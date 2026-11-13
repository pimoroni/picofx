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
<!-- if sensor -->

### Changing scenes with a remote or motion

With an Aye Arr Remote or a PIR Stick on the sensor connector, a button press or
motion can change the scene. Say which one is fitted in the board entry,
`sensor=ir` for the remote's IR Receiver Stick or `sensor=pir` for a PIR Stick:

```entry
board: sensor=ir
remote: menu_action=first record=restart
```

A `remote:` entry gives buttons something to do, each named as on the remote:
`1_red`, `2_green`, `3_blue`, `4_cyan`, `5_magenta`, `6_yellow`, `7_warm`,
`8_white`, `9_cool`, `0_rainbow`, `anticlock`, `up`, `clockwise`, `left`,
`right`, `down`, `return_undo`, `menu_action` and `record`. Each can go to a
scene, such as `scene Night`, or take a step: `next`, `previous`, `first`,
`restart` to begin the scene showing again, or `nothing`. Entries before the
first heading set what a button does in every scene, and an entry under a
heading changes it while that scene plays.

Without an entry, each number goes to the scene in its place, `0_rainbow` to the
tenth, and `left` and `right` step back and on. `ok_stop` always puts the board
in standby and wakes it, and `play_pause` always holds the effects where they
stand and lets them carry on.

Going to a scene starts its time again, and starts its effects again if its
heading has `restart`. `previous` goes back through the scenes shown, up to the
last ten.

A PIR Stick's entry is `motion:`, with `starts` and `stops`:

```entry
board: sensor=pir
motion: starts=scene Visitor after=2s

[Idle]
__ONE_OUTPUT__: pulse

[Visitor]
__ONE_OUTPUT__: flash
motion: stops=first after=10s
```

`after=` waits before acting, and motion changing back first cancels the wait.
Add `cancel=no` to finish the wait first instead, after which the board does
what the change back asks for.

A heading with no time, such as `[Visitor]`, waits until a button press or
motion changes the scene.
<!-- end -->
