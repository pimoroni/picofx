<!-- Generated from boards/manual/ and this board's own parts by tools/build_manual.py. Edit those and rebuild; edits here are lost. -->

# Tiny FX

Six mono outputs, one RGB output, a speaker, and a page on this drive that sets them all up for you. Open the
picker, choose your looks and save, and you'll see them play a few seconds
later. No code is needed, though you can write your own programs whenever you
want to.

## Getting started

The quickest way to start is the picker. Open it in Chrome or Edge, with
[[Picker]] at the top of this page or `PICKER.html` on this drive, then press
[[Open FX drive]] and choose this drive. Choose a look from the cards and press
[[Save to board]]. A few seconds later the drive disappears briefly, then comes
back with your changes playing. [The picker](#the-picker) shows you everything
else it can do.

While the board starts up or loads your changes, a dim bar of light fills and
empties along the outputs until the effects begin.

If a save does not seem to work, press **Boot** once or eject this drive, as a
computer does not always finish writing to a drive straight away.

You can hide the drive when you don't need it. Double-press **Boot** to hide it,
and double-press again to bring it back.
Each double press runs a dim light along the outputs, towards the
USB connector when the drive is shown and away from it when it is hidden.

While the computer copies files to this drive, the effects pause and a
dim light travels along the outputs. The effects resume shortly
after the copy finishes.

**The board also comes with ready-made programs, from single effects to whole
builds, and the picker can run any of them. See [what is already on the
board](#what-is-already-on-the-board).**

## The picker

The picker is where you choose what your board plays, from the looks on its
lights to a whole program. You'll be greeted with whatever the board is playing
right now, so you can carry on from there. Nothing reaches the board until you
press [[Save to board]], so feel free to try things out.

### The page: Getting around

Along the top are [[Open FX drive]], [[Save to board]] and [[Check board]]. Below
them are two large tabs. **Effects** is where you'll spend most of your time, and
**Programs** runs a program instead.

```picker
header: Tiny FX Picker
pages: *Effects, Programs
tabs: *Outputs=mono Wave, Sound
```

Under **Effects** you'll find **Outputs** for the lights and **Sound** for the
speaker. Each tab shows a small preview of what it's playing, and [[Edit board]]
sits at the end of the row.

### Lights: Choosing a look

On **Outputs** you'll see your lights, and below them a bar showing what each
stretch of them plays.

When your board is new, the picker opens on **Outputs**. The six mono outputs are
one stretch playing Wave, and the RGB output has a stretch of its own playing
Rainbow.

```picker
badge: Wiring, the RGB output is one colour light
mono: *Wave 6
colour RGB: Rainbow 1
tools:
settings: Wave, on outputs 1 to 6, Brightness 100, Speed 45, Spread 50
cards mono Along the lights: *Wave, Scanner, Chase, Marquee
```

Click the bar, or any light, to select that stretch. Then click a card in the
gallery to play that look there.

The cards are grouped by how they play. **Along the lights** travel from one end
to the other, **Ready-made** looks combine several others, **All together** shows
the same on every light, and **Individual** gives each light its own part. Cards
with a small palette let you choose the colour, and [[Nothing]] turns the stretch
off.

The selected stretch's settings sit just above the gallery. Every look has a
brightness, and most also have a speed and a setting of their own. A look that
takes a colour shows a row of colours to choose from, with [[custom]] for any
other. [[Reverse]] changes which end a travelling look starts from. If you want
an exact figure, the arrow at the right of the sliders opens a drawer to type it
in.

### Lights: Cutting into stretches

To play more than one look, cut the bar into stretches. Hover over the bar where
you want a cut, between two lights, and click.

Try it between mono lights 3 and 4. You'll have two stretches, both still playing
Wave. Click the right-hand one and choose Sparkle, and lights 4 to 6 start to
twinkle.

```picker
mono: Wave 3, *Sparkle 3
colour RGB: Rainbow 1
tools:
settings: Sparkle, on outputs 4 to 6, Brightness 100
cards mono Individual: *Sparkle, Counter, Traffic light, Pelican crossing
```

Drag a cut to move it, or click the cross on it to remove it.

The tools under the bar do the same in one go. [[Split into]] cuts the selected
stretch into a number of equal [[stretches]], or into stretches of so many
[[lights each]]. [[Join all]] puts the bar back to one stretch. [[Repeat]] takes
the number of stretches you set, starting with the selected one, and repeats
them to the end. The arrows above the bar undo and redo.

### Board: Setting up your hardware

Press [[Edit board]] to tell the picker about your hardware. Everything else
fades while you're there, and [[Done]] takes you back.

Look out for the chip icon on [[Edit board]]. The picker marks every board
setting with it, such as the order your lights are wired in. These settings
describe your hardware, so they're shared by every scene.

```picker
tabs editing: *Outputs=mono Wave, Sound
badge: Wiring, the RGB output is one colour light | Drag each light to match its position in your build.
wiring mono Wave: 1, 2, 3, 4, 5, 6 | RGB
```

Drag each light to match where it sits in your build, so a look that travels
moves the right way. The arrow on the RGB output moves it across to the mono side
as three mono lights, or brings them back as one colour light.

### Sound: Choosing a sound

Once the drive is open, the **Sound** tab lists the WAV files on it. Choose one
to play alongside the lights, or [[Silence]] for none. [[on repeat]] plays it
over and over instead of once, and the volume slider sets how loud the board
plays it. To add your own, drop a WAV file onto the tab and the picker copies it
onto the drive.

```picker
sounds: *rain.wav, doorbell.wav, Silence
```

### Scenes: Playing one after another

Press [[+ split into scenes]] to have the board play one setup after another.
What you've set up so far becomes Scene 1, and a tray of cards appears above
the tabs, one for each scene. A card shows the scene's name, an icon for each
part of the board it sets, and how it ends, such as "10s" or "45s, then Day".
Click a card to work on that scene, and drag it by the grip beside its name to
change the order. [[+ another scene]] adds one, and when the cards fill their
last row it becomes a thin bar under them.

```picker
pages: *Effects, Programs
scenes: Always on, *Scene 1 10s
```

Each scene takes the colour of its place, matching the number buttons on the
Aye Arr Remote, so the first scene is red like button 1 and the tenth takes the
rainbow of button 0. A scene you move takes the colour of its new place.

Everything below the tray sits in a frame of the chosen scene's colour, with the
scene's settings on a tab at its top left: its name, whether it "shows for" a
number of seconds or "waits", and the scene after it. That's the next scene
unless you choose another, or "itself" to repeat it. Tick "restart each time" to
have a scene start its effects from the beginning each time it plays, instead of
carrying on where they left off. A scene that goes back to itself always
restarts, so its tick stays on. With only one scene, "shows for" repeats it
after that many seconds, and "waits" keeps it showing.

Beside the tab, the page says where the scene comes, such as "Scene 2 of 4, then
Day", and [[Remove scene]] takes it away.

Each scene needs a name of its own. While its name is empty, "Always on" or
another scene's, the name is outlined and the words beside the tab say why.
Leave it that way and the scene goes back to its last name that worked.

### Scenes: Playing over Always on

The first card, **Always on**, runs down the left of the tray. Anything on it
plays under every scene. A scene that plays on the same part of the board takes
over from it while that scene shows.

With a scene chosen, the page shows what the board plays where the scene sets
nothing. Those lights play Always on's look, on tiles striped inside a dashed
outline. A light that only another scene uses is dark, as the board turns it
off, and the bar names the scene that lights it. In a scene, [[Nothing]] means
the scene sets nothing of its own there, so Always on can still play.

On **Sound**, Always on's sound wears the same stripes in a scene with none of
its own, and its [[on repeat]] and volume are greyed. Choose [[Silence]] to
quieten it while the scene shows.

### Sensor: Changing scenes with a remote or motion

Press [[Edit board]] and choose what's on the sensor connector, an Aye Arr
Remote through an IR Receiver Stick, or a PIR Stick. That's the only board
setting for it. The **Sensor** tab then shows the remote with a row for each
button, or the Stick with a row for when motion starts and one for when it
stops.

On **Always on**, choose what each does in every scene. To begin with, each
number goes to the scene in its place, 0 to the tenth, and Left and Right step
back and on through the scenes. With a scene chosen, the rows Always on sets are
striped, and choosing one changes it while that scene shows. A number only goes
to the scene in its place or does nothing, so to give a scene another number,
drag its card to that place. While a remote is fitted, each card shows its
number in the corner, unless Always on sets that number to do nothing.

OK / Stop and Play / Pause do the same in every scene, so they're gold with a
padlock. OK / Stop puts the board in standby and wakes it, so there's always a
way to stop it, and Play / Pause holds the effects where they stand.

Going to a scene starts its time again, and starts its effects again if its
"restart each time" is ticked. To begin a scene again whatever its tick says,
choose "from the start" on its own row, or "Restart the scene showing" on
Always on.

A PIR Stick's rows can wait before they act. Set the seconds after "after", then
choose what happens if the motion changes back first. "cancel this" drops the
wait, and "finish this first" acts when the wait is over, then does what the
change back asks for.

With a sensor fitted, a scene can wait instead of showing for a time. Choose
"waits" in place of "shows for" on its card, and the scene stays until a button
or motion changes it. A new scene waits to begin with. Without a sensor nothing
can move a waiting scene on, and the picker warns you.

### Programs: Running a program

**Programs** lists the board's programs, what a remote, a sensor or a speaker brings, and any of
your own programs on this drive, to run instead of the effects.
Choose one and save, and the board restarts to run it. The **With** buttons above
the list name the hardware the programs use, so turn off anything you don't have
and you'll only see programs that work without it. [[Choose none]] goes back to
the effects. [Your program in the picker](#your-program-in-the-picker) explains
how your own programs appear there.

```picker
pages: Effects, *Programs=Ship thrusters
note: ship_thrusters.py
with: remote, Qw/ST, speaker
programs Model lighting | thrusters, beacons and lit postcards: Rescue vehicle, *Ship thrusters, Space tales
```

### Saving: Sending to the board

[[Save to board]] writes your changes, and the board loads them a few seconds
later. The picker tells you when the board is playing your save, and whether it
found any problems. [[Check board]] asks the board again at any time.

The arrow beside [[Save to board]] opens the save settings. Untick "Play saves
without an eject" and the board waits for an eject or a single press of
**Boot**. Tick "Keep the drive hidden at start" and the drive stays hidden until
**Boot** is double-pressed.

```picker
header: Tiny FX Picker | Playing on the board. No problems reported.
savemenu:
```

On a Mac, each save shows "Disk Not Ejected Properly" once and closes any Finder
window on this drive. Don't worry, the drive comes back a few seconds later and
the page carries on.

The page can only reach the drive in Chrome, Edge or another Chromium-based
browser. Safari and Firefox cannot write to a drive from a web page, so the
picker says so there. [The editor](#the-editor) can still save from them, as a
download.

<!-- contents fold -->

## The editor

The picker saves everything into one text file on this drive, `effects.txt`, and
shows the file it will write at the foot of the page. The file can also be edited
by hand in any text editor, and [writing an entry](#writing-an-entry) and the
sections after it describe its format. The picker keeps lines it cannot edit
unchanged, and asks before replacing a file it has not read.

Deleting `effects.txt` restores the default file. Emptying it turns everything
off.

`EDITOR.html` on this drive is a text editor for `effects.txt` that understands
its format. Each word is coloured by its role, and as you type it suggests what
fits: the outputs at the start of a line, the effects after the colon,
then that effect's settings and their values. A hint below the text describes
the value expected. Tab or Enter accepts a suggestion, Escape dismisses it, and
Ctrl+Space shows suggestions again.

It underlines names it does not recognise, such as a misspelt effect or a setting
the effect does not take. Values are not checked, as the board reads them itself.
**Save to board** writes the file and **Check board** reads `errors.txt`, as in
the picker.

It suggests only what this board's firmware provides, so new firmware features
appear without the page changing. It saves in one click from a Chromium browser,
as the picker does, and from Safari or Firefox as a download you then copy onto
this drive. It needs `catalogue.js`, which sits beside it on this drive.

## Writing an entry

```shape
<outputs> <their settings>: <effect> <its settings>
```

```entry
out1-6: pulse_wave speed=0.3
rgb: rainbow speed=0.5
out3 level=50%: pulse speed=0.6
```

Each entry has one colon. Before it go the outputs and their brightness or
colour. After it go the effect and its settings.

Settings you leave out use their defaults. A `#` starts a comment. An entry can
span several lines as long as the colon is on the first, and indentation does not
matter.

## Outputs

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

Order matters for effects that travel: they move through the outputs in the
order you write them, so list them in the order they appear in your build,
which need not be number order.

### Setting an output

These go before the colon, separate from the effect:

| Setting | What it does | If omitted |
| --- | --- | --- |
| `level` | brightness, 0 to 1, such as 0.5 or 50% | 1 |
| `colour` | a colour name or six-digit hex code, for the RGB output when its effect brings no colour | white |
| `fade` | seconds to fade between changes, at a steady rate | changes instantly |
| `ease` | seconds to ease between changes, slowing at the end like a bulb | changes instantly |

```entry
out1-6 level=50%: pulse
rgb colour=warm: flicker
out1-6 ease=0.4: blink speed=0.5
```

Colour names: red, orange, yellow, green, cyan, blue, purple, magenta, pink,
warm, white, cool, black. Or a hex code from a colour picker, without its `#`,
such as ff8040 for a paler orange. A `#` always starts a comment, so leaving it
on a colour hides the rest of the line.

### Fade and ease

`fade` and `ease` set how many seconds a change takes. `fade` changes at a
steady rate, like a stage light. `ease` changes quickly at first and slows
towards the end, like a warming bulb, and looks more natural on a light
switching on and off.

An output uses one or the other, so a line takes `fade` or `ease`, not
both. Two numbers separated by `|` set the rise and fall separately, for
example a light that comes on quickly and fades out slowly:

```entry
out1-6 fade=0.8: blink speed=0.5
out1-3 ease=0.05|1.2: blink speed=1
```

`fade` and `ease` belong to the output, not the effect, so they work with any
effect, except effects that set their own colours.

## Effects

Every setting is optional. Left out, it uses the default shown below.

### Brightness effects

These work for any output, or for one of the RGB output's red, green and blue.

| Effect | Settings |
| --- | --- |
| `none` | |
| `static` | `brightness=1` |
| `blink` | `speed=1` `phase=0` `duty=0.5` |
| `blink_wave` | `speed=1` `length=1` `phase=0` `duty=0.5` |
| `flash` | `speed=1` `flashes=2` `window=0.5` `phase=0` `duty=0.5` |
| `flash_sequence` | `speed=1` `length=1` `flashes=1` `window=1` `phase=0` `duty=0.5` |
| `flicker` | `brightness=1` `dimness=0.5` `bright_min=0.05` `bright_max=0.1` `dim_min=0.02` `dim_max=0.04` |
| `flicker_each` | as `flicker` |
| `pulse` | `speed=1` `phase=0` |
| `pulse_wave` | `speed=1` `length=1` `phase=0` |
| `sweep` | `speed=1` `length=1` `extent=1` `hold=0` |
| `random` | `interval=0.05` `brightness_min=0` `brightness_max=1` |
| `random_each` | as `random` |
| `binary_counter` | `interval=0.1` `count=0` `step=1` |
| `traffic_light` | `red_interval=10` `red_amber_interval=5` `green_interval=10` `amber_interval=5` |
| `pelican_crossing` | `red_interval=8` `flashing_interval=6` `green_interval=20` `amber_interval=3` |

### Colour effects

These bring their own colour, so they work only for the RGB output.

| Effect | Settings |
| --- | --- |
| `rgb` | `red=255` `green=255` `blue=255` |
| `hsv` | `hue=0` `sat=1` `val=1` |
| `rainbow` | `speed=1` `sat=1` `val=1` |
| `rainbow_wave` | `speed=1` `length=1` `sat=1` `val=1` |
| `hue_step` | `interval=1` `hue=0` `sat=1` `val=1` `steps=6` |
| `rgb_blink` | `colour=red` `speed=1` `phase=0` `duty=0.5` |

### Effects that travel

Effects ending in `_wave`, `_sequence` and `_counter`, and `sweep`, travel
across the outputs you name. The others do the same thing on each one.

Effects ending in `_each` treat each output separately: `flicker_each` dips
each one at its own moments, like flames, and `random_each` gives each its own
brightness. `flicker` and `random` affect them all together, like a single light:

```entry
out1-6: flicker_each dimness=0.6
```

`traffic_light` and `pelican_crossing` use their outputs in the order given
below. With fewer, they light only the first ones. Naming more is an error,
reported in `errors.txt`.

### Traffic lights and crossings

`traffic_light` needs three outputs, lit red, amber and green in that order.
It switches instantly, so add `ease` to look like a real signal's lamps:

```entry
out1-3 ease=0.3: traffic_light
```

`pelican_crossing` needs five outputs: the same three, then the pedestrian's
stop and walk figures. Instead of red and amber, it flashes amber and the walk
figure together, as a real pelican crossing does before it changes back. It
cycles on its own timer, as there is no button to press:

```entry
out1-5 ease=0.3: pelican_crossing green_interval=20 red_interval=8
```

With three outputs, `pelican_crossing` plays its traffic lights only:

```entry
out1-3: pelican_crossing
```

### Sweep

`sweep` is a light that travels across the outputs and turns back at each end,
like a scanner. `extent` sets how far its glow reaches either side, in outputs,
and `speed` counts one crossing as one cycle, as the other travelling effects count
one pass. `hold` pauses at each end, in seconds, giving the trail time to fade
before the light returns:

```entry
out1-6 ease=0.4: sweep speed=1 extent=1 hold=1
```

Give `extent` a whole number of outputs, such as 1 or 2. A value in between
makes the light dim between outputs and brighten on each, so it appears to
step. 1 is the smallest that travels smoothly.

### Blinking through colours

`rgb_blink` blinks one colour, or several in sequence separated by `|`. A comma
instead would give each output its own colour. Without a colour it blinks red:

```entry
rgb: rgb_blink colour=red|warm|ff8040 speed=0.5
```

### What the settings mean

`speed` is cycles per second: 1 is once a second, 0.5 once every two seconds,
2 twice a second. A negative speed runs the cycle backwards.

The settings measured in seconds are `interval`, `hold`, flicker's `bright_min`,
`bright_max`, `dim_min` and `dim_max`, and the four intervals `traffic_light`
and `pelican_crossing` each take. `length`, `flashes`, `steps`, `count` and
`step` are whole numbers, and a negative `step` counts down.

`red`, `green` and `blue` run from 0 to 255. The rest run from 0 to 1, written as
0.5 or 50%. These include `window`, the share of each cycle the flashes happen in.
`hue` also takes degrees, such as 180deg, as a colour picker shows them.

**If you write Python**, you can add your own effect to this list and use it like
any other. The library reference on
[GitHub](https://github.com/pimoroni/picofx/blob/main/picofx/README.md) explains
how, under Effects System.

## Sound

The board plays a WAV file through its speaker, alongside
everything else:

```entry
audio: wav file=chimes.wav
audio: wav file=ambience.wav loop=yes
```

| Plays | Settings |
| --- | --- |
| `wav` | `file` `loop=no` `volume=1` |

The file plays once each time the effects start, or repeatedly with `loop`.
`volume` sets how loud it plays, from 0 to 1 or as a percentage, such as
`volume=50%`.

The board looks for the file in this drive's `sounds` folder, where the picker
adds sounds, then directly on the drive, then on the board itself. It
opens the file before this drive is shown, so the sound keeps playing when the
drive appears on a computer. While the computer copies files to this drive, the
sound pauses with the effects, and replacing a file while it plays silences it
until the next reload.

Use an uncompressed 16-bit or 32-bit WAV file, mono or stereo. MP3 is not
supported, and nor are 8-bit or 24-bit WAV files. This drive
holds 2.5MB, or 2MB on the Tiny FX W, so a lower sample rate fits more. A minute of 16-bit mono
takes about 2.6MB at 22kHz and under 1MB at 8kHz.

The board plays one sound at a time, so each scene takes one `audio` entry, and
one more can go before the first heading. An `audio` entry in a scene plays
while that scene plays, and one before the first heading plays in any scene
without its own sound. A sound paused by a scene change resumes where it left
off when its scene returns, and one that had finished starts again from the
beginning. A scene with `restart` starts its sound from the beginning every
time, along with everything else in it.

## Scenes

A file can hold several sets of effects, called scenes, and play them one
after another. A heading in square brackets starts each scene and sets how
long it plays:

```entry
[Evening: 30s]
out1-6: pulse_wave speed=0.3
rgb: rainbow speed=0.2

[Night: 10s]
out1-6: flicker_each
rgb colour=warm: pulse
```

The name is everything before the `:` and can be anything, including spaces. The
time is in seconds, `30s`, or minutes, `10m`. Scenes play in the order written,
then repeat.

Each scene needs a name of its own. A heading with no name, or with a name
another scene already has, even in different capitals, is reported in
`errors.txt`. The picker also keeps the name "Always on" for the entries before
the first heading.

Entries before the first heading are always on, whichever scene is playing, so
put anything that should never change there:

```entry
out1: static brightness=0.2
```

While a scene plays, an output it does not name plays its always-on entry.
Where there is none, it goes dark if another scene uses it, and is left alone
otherwise. A scene can name an always-on output and takes it over while the
scene plays, and `none` turns it off for that scene:

```entry
[Night: 10m]
out1: none
```


A scene with no `audio` entry lets the always-on sound play on, as
[Sound](#sound) explains. `audio: none` silences it while the scene shows.

Add `restart` to a heading to restart that scene's effects each time it
plays, instead of resuming where they left off:

```entry
[Beacon: 5s restart]
out1-3: flash_sequence flashes=3
```

A scene hands over to the next one in order. The picker can choose another,
which it writes after `then` at the end of the heading. `then` ends the
heading's settings, so everything after it is the next scene's name, spaces and
all, and `restart` goes before it:

```entry
[Night: 45s restart then Day]
```

A scene can also go back to itself, to begin its effects again each time its
time is up. That needs `restart`, as does a file's only scene when it has a
time, since otherwise nothing changes when the time is up, and `errors.txt`
says so:

```entry
[Storm: 30s restart then Storm]
```

The board entry goes before any scene heading. A scene with no time, such as
`[Welcome]`, waits, and the board stays on it. Put one last to play the scenes
before it once and then hold, such as an opening effect after the board starts.
A scene that no other scene goes on to never shows, and `errors.txt` says so.
Every reload, whether from a save, an eject or a press of **Boot**, starts again
from the first scene.

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
out1: pulse

[Visitor]
out1: flash
motion: stops=first after=10s
```

`after=` waits before acting, and motion changing back first cancels the wait.
Add `cancel=no` to finish the wait first instead, after which the board does
what the change back asks for.

A heading with no time, such as `[Visitor]`, waits until a button press or
motion changes the scene.

## The board

One entry sets up the board itself, and names no output:

```entry
board: drive=manual program=fireplace.py
```

| Setting | What it does | If omitted |
| --- | --- | --- |
| `drive` | `manual` keeps the drive hidden until **Boot** is double-pressed | shown at boot |
| `reload` | `manual` plays a save only after an eject or a press of **Boot** | plays a few seconds after saving |
| `program` | a Python file to run instead of the effects | the effects play |
| `args` | arguments for that program, separated by `\|` | none |

The picker's save settings write the first two. "Keep the drive hidden at start"
is `drive=manual`, and unticking "Play saves without an eject" is `reload=manual`.
`sensor` says what's on the sensor connector, `ir` or `pir`, as
[Changing scenes with a remote or motion](#changing-scenes-with-a-remote-or-motion)
explains.

Saving `effects.txt` is all it takes: the board detects the save, briefly takes
the drive back, and plays the new effects, just as a single press of **Boot**
would. Only saving `effects.txt` triggers this, so copying sounds onto
the drive never interrupts anything. With `reload=manual`, a save waits for an
eject or a press of **Boot** instead.

### Running your own program

A program can be on this drive or on the board's own filesystem, and its name
can include folders. The board looks here first, then on the
board, so `program=examples/programs/effects/mono/sweep_trail.py` runs one of the
examples the board comes with.
If both have a file with that name, the one on this drive
runs.

If the program is missing or stops with an error, the effects play instead
and `errors.txt` explains why, so a mistyped name never leaves the board
doing nothing.

Saving a file that names a program while the effects are playing restarts the
board, which then runs the program as it would at power-on.

The effects stop while a program runs, and **Boot** and ejecting do nothing. The
drive is always shown, even with `drive=manual`, so you can still edit
`effects.txt`. Saving it restarts the board with the new file. With
`reload=manual`, press **Reset** to apply the change. A program can read files
from this drive while it is shown, so its pictures and sounds can sit beside it
here.

When the program ends, the board plays the effects in the rest of the file.

`args` passes values to a program, so one program can behave differently
without being edited. Separate several with `|`, and put anything containing a
space or a colon in quotes:

```entry
board: program=slideshow.py args=posters|3
board: program=clock.py args="07:30"
```

**If you are writing the program**, read them from `sys.argv` as in any Python
program, starting at `sys.argv[1]`. Thonny passes none when you run the file
from there, so give each one a default and the file works either way:

```python
args = sys.argv[1:]
FOLDER = args[0] if args else "posters"
```

### Your program in the picker

The picker's **Programs** tab lists every Python file directly on this
drive and in its `programs` folder,
beside the examples in its `examples/programs` folder,
and describes each one from its opening string, the text in triple quotes that
opens the file. The first sentence says what the program does, and these lines
control how the picker shows it:

```python
'''
Program: Big clock
Shows the time.
Args: Colour, Seconds = 10
Picture: clock.png
Section: Signs and displays
'''
```

| Line | What the picker does with it |
| --- | --- |
| `Program: Big clock` | names the program, in place of its file name |
| `Args: Colour, Seconds = 10` | gives each argument a box of its own, and writes `args=` from them |
| `Picture: clock.png` | shows that picture for the program, kept beside it |
| `Section: Signs and displays` | lists the program in that section, not under **On the drive** |
| `Thumbnail: servo` | draws a servo for a program with no picture, `servo pair` two of them, or `motor`, or `outputs` and a pattern such as `outputs rainbow` |

Each is optional. Without `Picture`, the picker shows `clock.png` for `clock.py`
if it exists, and `clock-2.png` as a second screen's picture. Without `Args`, a
program that reads `sys.argv` gets empty boxes for adding arguments.

A value after `=` in `Args` is the program's default, so the box starts with it,
and `args=` is left out while every argument keeps its default. An argument
named `Screen size` offers the sizes the firmware knows, and one named
`Rotation` offers 0, 90, 180 and 270, or the values it lists, such as `Rotation
= 90 or 270`, the first being the default. The picture always shows the program
at its defaults.

To change an example, choose it and press **Customise**. The picker copies it
and its pictures into `programs`, under a new name if that one is taken, and
chooses the copy. Open the copy from the drive in Thonny or another editor, then
press **Save to board** to run it.

To delete one of your own programs from the drive, press the cross in the
corner of its card. One in `programs` takes its pictures with it.

A board with a wireless module keeps `secrets.py` directly on the drive for
your WiFi network's name and password, and restores an empty one if it is
deleted. Programs that go online, importing `network` or `requests`, are listed
only when the drive has that file.
An example is listed only in the section it names.
`examples/programs/sections.txt` sets the order of the sections, one per line:
its name, then a `|` and a description.

### What is already on the board

These come with the board, so `program=` can run any of them with nothing to
download:

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

The full list, with a description of each, is in the
[examples README on GitHub](https://github.com/pimoroni/picofx/tree/main/examples/tiny_fx).

<!-- contents Help -->

## When something is wrong

The lights flash to show a problem, and more flashes means a more serious
one. The RGB output shows the colour:

| Flashes | What happened |
| --- | --- |
| white, once | the computer was still writing, so the press was ignored. Try again in a moment |
| blue, twice | a line in `effects.txt` could not be read. `errors.txt` names the line |
| blue, twice | a sound could not be played. `errors.txt` names the line. A sound's error appears there once the board has the drive back |
| red, three times | there was no room to write `errors.txt`. This drive is full or damaged, so free some space or repair it from a computer |

A setting with an invalid value is ignored and noted in `errors.txt`,
and the effect uses its default instead.

A drive that cannot be repaired can be returned to how it shipped by
installing the board's `-full` firmware from the
[picofx releases](https://github.com/pimoroni/picofx/releases/latest).
This erases everything on the drive, so copy off anything you want to
keep first.

## More from Pimoroni

### Boards and accessories

- [Mighty FX](https://shop.pimoroni.com/products/mightyfx)
- [Tiny FX](https://shop.pimoroni.com/products/tinyfx)
- [Tiny FX W](https://shop.pimoroni.com/products/tiny-fx-w)
- [Plasma 2350](https://shop.pimoroni.com/products/plasma-2350)
- [Plasma 2350 W](https://shop.pimoroni.com/products/plasma-2350-w)
- [Everything in the range](https://shop.pimoroni.com/collections/tiny-fx)

### Going further

- [picofx on GitHub](https://github.com/pimoroni/picofx), the library these effects come from
