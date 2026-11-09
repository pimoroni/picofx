# Mighty FX Micropython Showcase Examples <!-- omit in toc -->

This folder contains a collection of *Showcase* examples, that bring together concepts presented by individual board and screen examples to create functional projects.

The posters the billboards show live with the other example art in [pictures/billboards](../../pictures/billboards), portrait and landscape in a folder each: the scrolling and street ones walk the portrait ones, the trivision one turns the three landscape.

- [Transport Signs](#transport-signs)
  - [Roadworks Sign](#roadworks-sign)
  - [Lane Control Gantry](#lane-control-gantry)
  - [Split Flap Departures](#split-flap-departures)
  - [Departure Board](#departure-board)
  - [Departures List](#departures-list)
  - [Bus Departures](#bus-departures)
  - [Tram Stop Sign](#tram-stop-sign)
- [Retro Displays](#retro-displays)
  - [Flip Dot Sign](#flip-dot-sign)
  - [Split Flap Clock](#split-flap-clock)
  - [CRT Terminal](#crt-terminal)
  - [Acrylic Lixie](#acrylic-lixie)
  - [Nixie Tube](#nixie-tube)
  - [Segment Clock](#segment-clock)
  - [Segment Sign](#segment-sign)
  - [Odometer](#odometer)
  - [Lamp Matrix](#lamp-matrix)
  - [Oscilloscope](#oscilloscope)
- [Billboards and Panels](#billboards-and-panels)
  - [Trivision Billboard](#trivision-billboard)
  - [Scrolling Billboard](#scrolling-billboard)
  - [Street Billboard](#street-billboard)
  - [Status Panel](#status-panel)
- [Animated Scenes](#animated-scenes)
  - [Isometric Flight](#isometric-flight)
  - [Skyline](#skyline)
  - [Laser Show](#laser-show)
  - [Fireplace](#fireplace)
  - [Portal](#portal)
  - [Pool](#pool)
  - [Neon Corridor](#neon-corridor)
  - [Creature Eyes](#creature-eyes)
- [Moving Things](#moving-things)
  - [Programmed Route](#programmed-route)


## Transport Signs

Departure boards and road signs.

### Roadworks Sign
<img src="transport_signs/roadworks_sign.png" align="left" alt="Roadworks Sign">

[transport_signs/roadworks_sign.py](transport_signs/roadworks_sign.py)

Draw a roadside roadworks sign with its message in amber lamps.

<br clear="left">


### Lane Control Gantry
<img src="transport_signs/lane_control_gantry.png" align="left" alt="Lane Control Gantry">

[transport_signs/lane_control_gantry.py](transport_signs/lane_control_gantry.py)

Draw the lane signals on a motorway gantry as they close a lane.

<br clear="left">


### Split Flap Departures
<img src="transport_signs/split_flap_departures.png" align="left" alt="Split Flap Departures">

[transport_signs/split_flap_departures.py](transport_signs/split_flap_departures.py)

Draw a split-flap departures board with each letter flipping into place.

<br clear="left">


### Departure Board
<img src="transport_signs/departure_board.png" align="left" alt="Departure Board">

[transport_signs/departure_board.py](transport_signs/departure_board.py)

Draw a railway departure board across a Screen Hub with one train on each screen.

<br clear="left">


### Departures List
<img src="transport_signs/departures_list.png" align="left" alt="Departures List">
<img src="transport_signs/departures_list-2.png" align="left" alt="Departures List, second screen">

[transport_signs/departures_list.py](transport_signs/departures_list.py)

Draw a railway departures list on one screen or on two screens that change page together.

<br clear="left">


### Bus Departures
<img src="transport_signs/bus_departures.png" align="left" alt="Bus Departures">
<img src="transport_signs/bus_departures-2.png" align="left" alt="Bus Departures, second screen">

[transport_signs/bus_departures.py](transport_signs/bus_departures.py)

Draw a bus departure board as shown on a TV screen at a bus station. A second panel lengthens the board, with one listing across both.

<br clear="left">


### Tram Stop Sign
<img src="transport_signs/tram_stop_sign.png" align="left" alt="Tram Stop Sign">
<img src="transport_signs/tram_stop_sign-2.png" align="left" alt="Tram Stop Sign, second screen">

[transport_signs/tram_stop_sign.py](transport_signs/tram_stop_sign.py)

Draw a tram stop sign across two screens with the next tram at the top and later ones cycling below.

<br clear="left">


## Retro Displays

Mechanical, glowing and segment displays.

### Flip Dot Sign
<img src="retro_displays/flip_dot_sign.png" align="left" alt="Flip Dot Sign">

[retro_displays/flip_dot_sign.py](retro_displays/flip_dot_sign.py)

Draw a flip-dot sign that spells its message by flipping one column of dots at a time.

<br clear="left">


### Split Flap Clock
<img src="retro_displays/split_flap_clock.png" align="left" alt="Split Flap Clock">

[retro_displays/split_flap_clock.py](retro_displays/split_flap_clock.py)

Draw a split-flap clock with each digit flipping through to the next.

<br clear="left">


### CRT Terminal
<img src="retro_displays/crt_terminal.png" align="left" alt="CRT Terminal">

[retro_displays/crt_terminal.py](retro_displays/crt_terminal.py)

Draw an old green-screen computer terminal. An operator types a command a character at a time and the machine answers a line at a time, on a tube that glows.

<br clear="left">


### Acrylic Lixie
<img src="retro_displays/acrylic_lixie.png" align="left" alt="Acrylic Lixie">

[retro_displays/acrylic_lixie.py](retro_displays/acrylic_lixie.py)

Draw a lixie display that lights one engraved acrylic sheet at a time to show each digit.

<br clear="left">


### Nixie Tube
<img src="retro_displays/nixie_tube.png" align="left" alt="Nixie Tube">

[retro_displays/nixie_tube.py](retro_displays/nixie_tube.py)

Draw a nixie tube with each digit lighting up inside the glass. The digit carrying current glows red-orange through the anode mesh.

<br clear="left">


### Segment Clock
<img src="retro_displays/segment_clock.png" align="left" alt="Segment Clock">

[retro_displays/segment_clock.py](retro_displays/segment_clock.py)

Draw a seven-segment LED clock behind a coloured filter.

<br clear="left">


### Segment Sign
<img src="retro_displays/segment_sign.png" align="left" alt="Segment Sign">

[retro_displays/segment_sign.py](retro_displays/segment_sign.py)

Draw a three-line fourteen-segment LED sign in a brushed metal case. A row too long for its window scrolls through it.

<br clear="left">


### Odometer
<img src="retro_displays/odometer.png" align="left" alt="Odometer">

[retro_displays/odometer.py](retro_displays/odometer.py)

Draw a mechanical odometer with number drums rolling in a brass frame. The last drum turns steadily, and each of the others is carried round as the drum to its right passes from 9 to 0.

<br clear="left">


### Lamp Matrix
<img src="retro_displays/lamp_matrix.png" align="left" alt="Lamp Matrix">

[retro_displays/lamp_matrix.py](retro_displays/lamp_matrix.py)

Draw a grid of stage lamps running through a light show. Tungsten lamps glow up quickly and fade slowly, white hot through orange to a dull red as each filament cools. LAMPS = "led" switches each instantly to one of a handful of colours, or off, instead.

<br clear="left">


### Oscilloscope
<img src="retro_displays/oscilloscope.png" align="left" alt="Oscilloscope">

[retro_displays/oscilloscope.py](retro_displays/oscilloscope.py)

Draw an oscilloscope tracing waves that slowly fade on the screen. A scrolling sine grows into a square wave a harmonic at a time and melts back, then the scope switches to XY mode for a turning Lissajous figure. SENSOR = True traces the voltage on the sensor connector instead.

<br clear="left">


## Billboards and Panels

Posters and signs that change on screen.

### Trivision Billboard
<img src="billboards/trivision_billboard.png" align="left" alt="Trivision Billboard">

[billboards/trivision_billboard.py](billboards/trivision_billboard.py)

Draw a trivision billboard whose three-sided slats turn to change the poster.

<br clear="left">


### Scrolling Billboard
<img src="billboards/scrolling_billboard.png" align="left" alt="Scrolling Billboard">

[billboards/scrolling_billboard.py](billboards/scrolling_billboard.py)

Draw a scrolling billboard that rolls its posters past one at a time.

<br clear="left">


### Street Billboard
<img src="billboards/street_billboard.png" align="left" alt="Street Billboard">

[billboards/street_billboard.py](billboards/street_billboard.py)

Show a folder of posters as if each stood in a case behind glass.

<br clear="left">


### Status Panel
<img src="status_panel.png" align="left" alt="Status Panel">

[status_panel.py](status_panel.py)

Draw a Pimoroni status panel with the RGB outputs lighting in step with its production line.

<br clear="left">


## Animated Scenes

Drawn in code.

### Isometric Flight
<img src="animated_scenes/isometric_flight.png" align="left" alt="Isometric Flight">
<img src="animated_scenes/isometric_flight-2.png" align="left" alt="Isometric Flight, second screen">

[animated_scenes/isometric_flight.py](animated_scenes/isometric_flight.py)

Fly endlessly over two isometric worlds.

<br clear="left">


### Skyline
<img src="animated_scenes/skyline.png" align="left" alt="Skyline">

[animated_scenes/skyline.py](animated_scenes/skyline.py)

Drift past a city while the sky turns from noon to midnight and the windows come on.

<br clear="left">


### Laser Show
<img src="animated_scenes/laser_show.png" align="left" alt="Laser Show">

[animated_scenes/laser_show.py](animated_scenes/laser_show.py)

Draw a laser show of beams fanning and sweeping across a dark hall. Each scene switches its projectors on and off as it goes. An upright or square panel has room for the outer two projectors only.

<br clear="left">


### Fireplace
<img src="animated_scenes/fireplace.png" align="left" alt="Fireplace">

[animated_scenes/fireplace.py](animated_scenes/fireplace.py)

Draw a fire and flicker the RGB outputs with it like firelight in a room. The fire fills the panel, leaving the surround to whatever it is mounted in.

<br clear="left">


### Portal
<img src="animated_scenes/portal.png" align="left" alt="Portal">

[animated_scenes/portal.py](animated_scenes/portal.py)

Draw a glowing portal with arms spiralling into a dark opening and specks of light falling in. Each arm dims to black before the opening, so it seems to fall away without end. STONES = True sets it into a stone wall, and RIM_WIDTH and RIM_HEIGHT size it to a cutout in front of the panel.

<br clear="left">


### Pool
<img src="animated_scenes/pool.png" align="left" alt="Pool">

[animated_scenes/pool.py](animated_scenes/pool.py)

Draw the floor of a pool through rippling water that throws bright lines of light over the tiles. STYLE chooses the floor to start on, a modern pool's blue mosaic or a Roman bath's cream stones round an octagon, and "Boot" swaps to the other.

<br clear="left">


### Neon Corridor
<img src="animated_scenes/neon_corridor.png" align="left" alt="Neon Corridor">

[animated_scenes/neon_corridor.py](animated_scenes/neon_corridor.py)

Walk without end down a corridor of neon, as rings of light come out of the haze towards you and a bright light shines at the far end. SCHEME sets its colours to neon, plaid, emerald, magenta or blueprint, and "Boot" steps to the next. SPEED sets a slow, normal, fast or ludicrous pace, and OBLONG = True stretches the corridor to the panel's shape.

<br clear="left">


### Creature Eyes
<img src="animated_scenes/creature_eyes.png" align="left" alt="Creature Eyes">
<img src="animated_scenes/creature_eyes-2.png" align="left" alt="Creature Eyes, second screen">

[animated_scenes/creature_eyes.py](animated_scenes/creature_eyes.py)

Draw a creature's eyes on two screens as they look around and blink. CREATURE chooses the cat, owl, goat, alien, robot or zombie, each with its own eyes and its own way of looking about, and "Boot" steps to the next.

<br clear="left">


## Moving Things

Servos and motors.

### Programmed Route
[programmed_route.py](programmed_route.py)

Program a route into a two-wheeled robot with the IR remote and watch it drive.
