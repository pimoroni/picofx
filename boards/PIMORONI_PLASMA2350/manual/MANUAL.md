# Plasma 2350

Two LED terminals, a screen connector, and a text file that drives them. Edit
`effects.txt` on this drive, eject it, and the board applies the change straight
away. No code needed, though there is room for it when you want it.

## Getting started

Edit `effects.txt` to change what the lights do, then eject this drive and the
board applies the change straight away.

In a hurry? Save the file and press **Boot** once. The drive disappears and
comes straight back with the new effects running, so you can keep editing.
Ejecting is the surer way, since a computer does not always write the file out
until then. Press **Boot** twice to hide the drive, and twice again to bring it
back.

Deleting `effects.txt` restores the default; emptying it leaves the board dark.

**Would you rather not write the file at all? `PICKER.html` on this drive writes
it for you.** Open it in Chrome or Edge, point it at this drive, and choose what
each strip plays. `EDITOR.html` beside it is a place to write the file with the
names offered as you type.

## Writing an entry

Each line names what to light, a colon, and the effect to play on it:

```entry
stripDat: rainbow_wave speed=0.3 length=30
```

Settings follow the effect as `name=value`. A line starting `#` is a note and is
ignored. The board reads the whole file each time the drive goes away, so a
mistake on one line is reported in `errors.txt` and the rest still plays.

## LED strips

The two screw terminals are marked **DAT** and **CLK**. A WS2812 strip needs
only a data line, so one can go on each terminal: `stripDat` and `stripClk`. An
APA102 strip needs both, data and clock, so it is the one strip on the board,
`stripApa`.

A strip's length is declared on the board line:

```entry
board: stripDat=60 stripClk=30
board: stripApa=144
```

A strip's LEDs are named like outputs, so `stripDat1-10` is the first ten and
the bare name is the whole run:

```entry
stripDat1-30: pulse_wave speed=0.5
stripDat31-60 colour=ff5a00: flicker_each
```

Most WS2812 strips take their colours as green, red, then blue, and the board
sends them that way. If yours shows another colour where you asked for red, it
takes them in another order: write the letters `r`, `g` and `b` after its
length in the order it wants them, such as `stripDat=60|rgb`.

An APA102 strip has a brightness of its own for the whole strip, at 50% unless
the board line says otherwise, such as `stripApa=144|75%`. The effects' own
levels apply on top of it.

`stripApa` and the WS2812 strips cannot play at once, since they use the same
terminals. A file naming both plays the WS2812 strips and says so in
`errors.txt`.

## The board's LED

The RGB LED on the board is `rgb`, and takes any colour effect:

```entry
rgb: rainbow speed=0.3
```

It also reports: it flashes when a reload fails, and holds a dim white while a
computer is copying to the drive.

## The screen

A screen on the SP/CE connector is `screen`, and needs its size on the board
line, since a panel cannot say what size it is:

```entry
board: screen=2.8
screen: image file="picture.png"
```

The Plasma 2350 W has no SP/CE connector, so it takes no screen, and the picker
offers none.

Pictures and animations go on this drive beside `effects.txt`. `gif` plays an
animation, `image` shows a still, and `sequence` plays a folder of them in turn.

The panel is mounted upright, 240 wide by 320 tall, so a landscape picture is
cropped at its sides unless the line turns it: `screen rotation=90: image
file="picture.png"`.

**A limit for now.** The board's memory is small, and what the last file showed
can keep its room until a restart. Saving a change from one full-size picture
to another is refused with a note in `errors.txt`; turn the board off and on
with the new file saved and it plays. Animations under about 60KB of frames,
small pictures, and drawings with `pixel_double=true` change over without a
restart. The lights are never affected.

## Scenes

A heading starts a scene, and scenes take turns for the time each names.
Everything above the first heading stays on throughout:

```entry
rgb: static colour=white brightness=0.2

[Daytime: 30s]
stripDat: rainbow_wave speed=0.3

[Night: 2m]
stripDat colour=ff5a00: flicker_each
```

## The board

The board line holds what is the same in every scene: each strip's length, and
its colour order or brightness, the screen's size, and how the drive behaves.
`reload=auto` applies a saved file without an eject, and `drive=manual` keeps
the drive hidden until **Boot** is pressed twice. `program=` runs a Python file from this drive in place of the
effects.

## When something is wrong

The board's LED says so, and the more flashes the worse it is: white once means
the computer was still writing, so press again in a moment; blue twice means a
line could not be read, and `errors.txt` says which; red three times means
there was no room to write `errors.txt`, so free some space on the drive.
