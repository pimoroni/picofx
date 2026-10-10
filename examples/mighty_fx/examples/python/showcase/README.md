# Mighty FX Micropython Showcase Examples <!-- omit in toc -->

This folder contains a collection of *Showcase* examples, that bring together concepts presented by individual board and screen examples to create functional projects.

The posters the two billboards show live with the other example art in [assets/billboards](../assets/billboards), portrait and landscape in a folder each: the scrolling one walks the portrait ones, the trivision one turns the three landscape.

- [Roadworks Sign](#roadworks-sign)
- [Lane Control Gantry](#lane-control-gantry)
- [Flip Dot Sign](#flip-dot-sign)
- [Split Flap Clock](#split-flap-clock)
- [Split Flap Departures](#split-flap-departures)
- [Departure Board](#departure-board)
- [Departures List](#departures-list)
- [Bus Departures](#bus-departures)
- [Tram Stop Sign](#tram-stop-sign)
- [Trivision Billboard](#trivision-billboard)
- [Scrolling Billboard](#scrolling-billboard)
- [CRT Terminal](#crt-terminal)
- [Acrylic Lixie](#acrylic-lixie)
- [Nixie Tube](#nixie-tube)
- [Isometric Flight](#isometric-flight)
- [Programmed Route](#programmed-route)
- [Skyline](#skyline)
- [Status Panel](#status-panel)


## Roadworks Sign
[roadworks_sign.py](roadworks_sign.py)

Draw a roadworks sign, the kind towed to the side of a road: amber lamps behind a dark face, holding a message, not scrolling it.


## Lane Control Gantry
[lane_control_gantry.py](lane_control_gantry.py)

Draw a motorway lane control gantry, a signal to a lane, working through a lane closure.


## Flip Dot Sign
[flip_dot_sign.py](flip_dot_sign.py)

Draw a flip-dot sign, spelling its message in dots that turn over one column after the next.


## Split Flap Clock
[split_flap_clock.py](split_flap_clock.py)

Draw a split-flap clock, its digits climbing through the drum a flap at a time as a real board does.


## Split Flap Departures
[split_flap_departures.py](split_flap_departures.py)

Draw a split-flap departures board, every card climbing through the drum until it reaches its letter.


## Departure Board
[departure_board.py](departure_board.py)

Draw a railway departure board across a screen hub, a service to each panel, every one paging its calling points on its own clock.


## Departures List
[departures_list.py](departures_list.py)

Draw a railway departures list on one screen, or spread across a pair with both panels turning their page together.


## Bus Departures
[bus_departures.py](bus_departures.py)

Draw a bus departure board on a television used for signage: no mechanism simulated, just anti-aliased vector type on a panel plainly being a panel.


## Tram Stop Sign
[tram_stop_sign.py](tram_stop_sign.py)

Draw a tram stop sign across two screens: amber lamps behind a dark face, in a contiguous band per line, with the next tram pinned and the ones after it cycling underneath.


## Trivision Billboard
[trivision_billboard.py](trivision_billboard.py)

Draw a trivision billboard, its posters carried on three-sided slats that turn a third at a time.


## Scrolling Billboard
[scrolling_billboard.py](scrolling_billboard.py)

Draw a scrolling billboard, its posters carried on a loop and read from the card one at a time.


## CRT Terminal
[crt_terminal.py](crt_terminal.py)

Draw a green screen terminal, of the kind wheeled up to a minicomputer: an operator typing a command a character at a time and the machine answering a line at a time, on a tube that glows.


## Acrylic Lixie
[acrylic_lixie.py](acrylic_lixie.py)

Draw a lixie: ten engraved acrylic sheets stacked front to back with a digit on each, an LED under every sheet, and only the one being shown lit.


## Nixie Tube
[nixie_tube.py](nixie_tube.py)

Draw a nixie tube: ten cathodes bent into digits, stacked front to back inside one glass envelope, and the neon around the one carrying current glowing the colour it is famous for.


## Isometric Flight
[isometric_flight.py](isometric_flight.py)

Fly for ever over two isometric worlds, each drawn once into a tile the driver repeats.


## Programmed Route
[programmed_route.py](programmed_route.py)

Programme a route into a two wheeled robot with the Aye Arr Remote, then watch it drive what it was told, its wheels turned by a continuous rotation servo on each of the L and R connectors.


## Skyline
[skyline.py](skyline.py)

Drift past a city while the sky turns from noon to midnight and the windows come on.


## Status Panel
[status_panel.py](status_panel.py)

Draw a status panel for the company that made the board: the wordmark over a cycling ribbon, the coin as a badge, a few statuses, and the seven RGB outputs standing in for the line the board came down.
