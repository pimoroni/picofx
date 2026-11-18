## The board

One entry sets up the board itself, and names no __OUTPUT__:

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
<!-- if sensor -->
`sensor` says what's on the sensor connector, `ir` or `pir`, as
[Changing scenes with a remote or motion](#changing-scenes-with-a-remote-or-motion)
explains.
<!-- end -->
<!-- if screens -->
<!-- board screen_settings -->
<!-- end -->
<!-- if strips -->
<!-- board strip_settings -->
<!-- end -->

Saving `effects.txt` is all it takes: the board detects the save, briefly takes
the drive back, and plays the new effects, just as a single press of **Boot**
would. Only saving `effects.txt` triggers this, so copying __COPIED_FILES__ onto
the drive does not reload the effects. With `reload=manual`, a save waits for an
eject or a press of **Boot** instead.

### Running your own program

A program can be on this drive or on the board's own filesystem, and its name
can include folders. The board looks here first, then on the
<!-- if examples -->
board, so `program=__EXAMPLE_PROGRAM__` runs one of the
examples the board comes with.
<!-- end -->
<!-- if not examples -->
board.
<!-- end -->
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
`reload=manual`, press **__RESET_BUTTON__** to apply the change. A program can read files
from this drive while it is shown, so its pictures and sounds can sit beside it
here.

When the program ends, the board plays the effects in the rest of the file.

<!-- if screens -->
__SCREEN_SETTINGS_UNSEEN__. It sets up its own screens, so
pass it the size in `args` if it needs it.
<!-- end -->

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
import sys

args = sys.argv[1:]
FOLDER = args[0] if args else "posters"
```

### Your program in the picker

The picker's **Programs** tab lists every Python file directly on this
drive and in its `programs` folder,
<!-- if examples -->
beside the examples in its `examples/programs` folder,
<!-- end -->
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
= 90 or 270`. The first is the default. The picture always shows the program at
its defaults.
<!-- if examples -->

To change an example, choose it and press the copy button in the corner of its
card. The picker copies it
and its pictures into `programs`, under a new name if that one is taken, and
chooses the copy. Open the copy from the drive in Thonny or another editor, then
press **Save to board** to run it.
<!-- end -->

To delete one of your own programs from the drive, press the cross in the
corner of its card. One in `programs` takes its pictures with it.

A board with a wireless module keeps `secrets.py` directly on the drive for
your WiFi network's name and password and your [time zone](#time-zones), and
restores an empty one if it is deleted. Programs that go online, importing
`network` or `requests`, are listed only when the drive has that file.
<!-- if examples -->
An example is listed only in the section it names.
`examples/programs/sections.txt` sets the order of the sections, one per line:
its name, then a `|` and a description.
<!-- end -->
<!-- if screens -->
A file whose opening string has a `Drawing:` line is [a
drawing](#drawing-from-code), so it is not listed.
<!-- end -->

### Time zones

Programs that show the time of day take your time zone from `TIME_ZONE` in
`secrets.py`, such as `TIME_ZONE = "uk"`. Left empty, they show UTC. Where a
zone has summer time, the clock changes on the right dates by itself.

| Name | Places | Time | Summer time |
| --- | --- | --- | --- |
| `american_samoa` | American Samoa | UTC-11 | no |
| `hawaii` | Hawaii | UTC-10 | no |
| `alaska` | Alaska | UTC-9 | yes |
| `pacific` | US & Canada Pacific | UTC-8 | yes |
| `arizona` | Arizona | UTC-7 | no |
| `mountain` | US & Canada Mountain | UTC-7 | yes |
| `mexico` | Mexico City | UTC-6 | no |
| `central` | US & Canada Central | UTC-6 | yes |
| `colombia` | Colombia, Peru & Panama | UTC-5 | no |
| `cuba` | Cuba | UTC-5 | yes |
| `eastern` | US & Canada Eastern | UTC-5 | yes |
| `venezuela` | Venezuela, Bolivia & Puerto Rico | UTC-4 | no |
| `atlantic` | Atlantic Canada | UTC-4 | yes |
| `newfoundland` | Newfoundland | UTC-3:30 | yes |
| `brazil` | Brazil & Argentina | UTC-3 | no |
| `cape_verde` | Cape Verde | UTC-1 | no |
| `azores` | Azores | UTC-1 | yes |
| `utc` | UTC | UTC | no |
| `uk` | UK, Ireland & Portugal | UTC | yes |
| `west_africa` | West Africa | UTC+1 | no |
| `central_europe` | Central Europe | UTC+1 | yes |
| `eastern_europe` | Eastern Europe | UTC+2 | yes |
| `egypt` | Egypt | UTC+2 | yes |
| `south_africa` | South Africa | UTC+2 | no |
| `moscow` | Moscow, Turkey & Saudi Arabia | UTC+3 | no |
| `iran` | Iran | UTC+3:30 | no |
| `gulf` | UAE & Oman | UTC+4 | no |
| `pakistan` | Pakistan | UTC+5 | no |
| `india` | India & Sri Lanka | UTC+5:30 | no |
| `nepal` | Nepal | UTC+5:45 | no |
| `bangladesh` | Bangladesh | UTC+6 | no |
| `indochina` | Thailand, Vietnam & Jakarta | UTC+7 | no |
| `china` | China, Singapore & Perth | UTC+8 | no |
| `japan` | Japan & Korea | UTC+9 | no |
| `darwin` | Darwin | UTC+9:30 | no |
| `adelaide` | Adelaide | UTC+9:30 | yes |
| `brisbane` | Brisbane | UTC+10 | no |
| `sydney` | Sydney, Melbourne & Hobart | UTC+10 | yes |
| `solomon` | Solomon Islands & New Caledonia | UTC+11 | no |
| `fiji` | Fiji | UTC+12 | no |
| `nz` | New Zealand | UTC+12 | yes |
| `samoa_tonga` | Samoa & Tonga | UTC+13 | no |
| `line_islands` | Kiribati Line Islands | UTC+14 | no |

A place not listed can use a zone with the same time, but its clock may be an
hour out for part of the year.

<!-- if examples -->
### What is already on the board

These come with the board, so `program=` can run any of them with nothing to
download:

<!-- board examples_on_board -->

The full list, with a description of each, is in the
[examples README on GitHub](__EXAMPLES_URL__).
<!-- end -->
