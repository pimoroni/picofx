## The picker

The picker is where you choose what your board plays, from the looks on its
lights to a whole program. You'll be greeted with whatever the board is playing
right now, so you can carry on from there. Nothing reaches the board until you
press [[Save to board]], so feel free to try things out.

### The page: Getting around

Along the top are [[Open FX drive]], [[Save to board]] and [[Check board]]. Below
them are two large tabs. **Effects** is where you'll spend most of your time, and
**Programs** runs a program instead.

<!-- board picker_tabs -->

### Lights: Choosing a look

__LIGHTS_TABS__ you'll see a bar of your lights, cut into stretches, each one
named for the look it plays.

<!-- board picker_first_look -->

Click a stretch to select it. A stretch that plays a look shows its settings.
Every look has a brightness, and most also have a speed and a setting of their
own. A look that takes a colour shows a row of colours to choose from, with
[[custom]] for any other. [[Reverse]] changes which end a travelling look starts
from. If you want an exact figure, the arrow at the right of the sliders opens a
drawer to type it in.

Press [[Change look]] to choose another look, or [[Keep]] to leave it as it is. A
stretch playing nothing shows the gallery straight away. Click a card to play
that look there.

The cards are grouped by how they play. **Along the lights** travel from one end
to the other, **Ready-made** looks combine several others, **All together** shows
the same on every light, and **Individual** gives each light its own part. Cards
with a small palette let you choose the colour, and [[Nothing]] turns the stretch
off.

### Lights: Cutting into stretches

To play more than one look, cut the bar into stretches. Hover over the bar where
you want a cut, between two lights, and click.

<!-- board picker_first_cut -->

Drag a cut to move it, or click the cross on it to remove it. The arrows above
the bar undo and redo.
<!-- if strips -->
On a long strip, the magnifier buttons zoom in so each LED is easier to reach.
<!-- end -->

### Board: Setting up your hardware

Press [[Edit board]] to tell the picker about your hardware. Everything else
fades while you're there, and [[Done]] takes you back.

Look out for the chip icon on [[Edit board]]. The picker marks every board
setting with it, such as the order your lights are wired in. These settings
describe your hardware, so they're shared by every scene.

<!-- board picker_board -->
<!-- if screens -->

### Screens: Showing a picture

Once the drive is open, the pictures and drawings on it appear on the
**Screens** tab, under the screen. Press the button under a picture to show it
there. Each screen has its own settings for the picture it shows, such as its
backlight, rotation and position, and the timing of an animation.

<!-- board picker_screens_picture -->
<!-- end -->
<!-- if screens -->

To add your own, drop GIF, PNG or JPEG files or drawings onto the **add pictures
or drawings** tile, and the picker copies them onto the drive. Each picture has a
button to delete it from the drive.
<!-- end -->
<!-- if two_screens -->

With two screens, each picture has an [[A]] and a [[B]] button, one for each
screen. To show the same thing on both, press [[Paired]] on either screen. Screen
B then shows whatever Screen A shows, in step and at the same speed, while each
screen keeps its own rotation and position. This matters most for a drawing,
which then runs once for both screens, so both show the same random choices.
Press [[Paired]] again to set them apart. Each scene can pair the screens or not.
<!-- end -->
<!-- if hub -->

### Screens: Using a Screen Hub

A Screen Hub plugs into both screen connectors and drives up to six screens, at
the positions A to F printed on the hub. To set one up, press [[Edit board]], open
**Screens** and choose **A Screen Hub across both**. Then pick which connector
carries the hub's SPI and which its Selects, as labelled on the hub, and set the
size of the screen at each position.

Back on **Screens**, the positions sit side by side under one shared backlight.
Each picture has a button for every position, or for every group once you've
made some, and [[all]] shows it everywhere.

To show one picture across several screens, put them in a group with the 1, 2
and 3 buttons under each position. A group is set as one, with one picture,
rotation and look, and the board sends that picture to all its screens at once,
so an animation plays as fast as on a single screen. Positions showing different
animations take turns, so each plays more slowly, and the picker says when that
happens. A group holds screens of one size, and each scene can group the hub its
own way.

```picker
screenmode: hub
hub: SPI on A, Selects on B
places: A=acrylic_lixie 1, B=acrylic_lixie 1, C=acrylic_lixie 1, D, E, F
pictures: acrylic_lixie=1, skyline.png, gold_macaw_card.png, medscan.gif
```
<!-- end -->
<!-- if sound -->

### Sound: Choosing a sound

Once the drive is open, the **Sound** tab lists the WAV files on it. Choose one
to play alongside the lights, or [[Silence]] for none. [[on repeat]] plays it
over and over instead of once, and the volume slider sets how loud the board
plays it. To add your own, drop a WAV file onto the tab and the picker copies it
onto the drive.

```picker
sounds: *rain.wav, doorbell.wav, Silence
```
<!-- end -->

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
<!-- if screens -->

A screen the scene leaves to Always on shows Always on's picture in the same
striped frame, with its settings greyed, as they're set on Always on. To turn a
screen off in a scene, press its button on the small black [[Off]] card at the
end of the first heading on **Screens**. The screen then shows black.
<!-- end -->
<!-- if sound -->

On **Sound**, Always on's sound wears the same stripes in a scene with none of
its own, and its [[on repeat]] and volume are greyed. Choose [[Silence]] to
quieten it while the scene shows.
<!-- end -->
<!-- if sensor -->

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
<!-- end -->

### Programs: Running a program

<!-- if examples -->
**Programs** lists the board's programs, __PROGRAMS_OFFERED__, and any of
your own programs on this drive, to run instead of the effects.
<!-- end -->
<!-- if not examples -->
**Programs** lists your own programs on this drive, to run instead of the
effects.
<!-- end -->
Choose one and save, and the board restarts to run it. The **With** buttons above
the list name the hardware the programs use, so turn off anything you don't have
and you'll only see programs that work without it. [[Choose none]] goes back to
the effects. [Your program in the picker](#your-program-in-the-picker) explains
how your own programs appear there.

<!-- board picker_programs_picture -->

### Saving: Sending to the board

[[Save to board]] writes your changes, and the board loads them a few seconds
later. The picker tells you when the board is playing your save, and whether it
found any problems. [[Check board]] asks the board again at any time.

The arrow beside [[Save to board]] opens the save settings. Untick "Play saves
without an eject" and the board waits for an eject or a single press of
**Boot**. Tick "Keep the drive hidden at start" and the drive stays hidden until
**Boot** is double-pressed.

```picker
header: __BOARD_TITLE__ Picker | Playing on the board. No problems reported.
savemenu:
```

On a Mac, each save shows "Disk Not Ejected Properly" once and closes any Finder
window on this drive. Don't worry, the drive comes back a few seconds later and
the page carries on.

The page can only reach the drive in Chrome, Edge or another Chromium-based
browser. Safari and Firefox cannot write to a drive from a web page, so the
picker says so there. [The editor](#the-editor) can still save from them, as a
download.
