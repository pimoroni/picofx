"""Draws the pictures of the picker that the manual shows, from a ```picker fence in its parts.

A picture is built from simplified copies of the picker's own parts, so it costs a few hundred
bytes where a screenshot would cost tens of thousands, and the manual template holds the styles
that make it look like the picker. Each line of the fence draws one part, in the order given,
and the function drawing that part describes what its line holds. A * before an item marks it
as the one the picture shows selected.

    ```picker
    tabs: *Outputs=Rainbow, Left strip, Right strip, Screens=2.8" 1.54", Sound
    badge: Wiring, every output is one colour light
    colour: Rainbow 4, *Solid 3
    settings: Solid, on outputs 5 to 7, Brightness 100
    cards Along the lights: Rainbow, Wave, Scanner, Chase, Marquee
    ```

The pictures are not interactive and never run the picker, so a change to the picker's look
needs the matching change here and in the template.
"""

import html
import sys

# The chip the picker draws on everything that sets up the board, the same in every scene
CHIP_ICON = ('<svg class="chipicon" viewBox="0 0 14 14" width="13" height="13" aria-hidden="true">'
             '<rect x="3" y="3" width="8" height="8" rx="1" fill="none" stroke="currentColor" '
             'stroke-width="1.3"/><path d="M4 0.8V3M7 0.8V3M10 0.8V3M4 11v2.2M7 11v2.2M10 11v2.2'
             'M0.8 4H3M0.8 7H3M0.8 10H3M11 4h2.2M11 7h2.2M11 10h2.2" stroke="currentColor" '
             'stroke-width="1.3" stroke-linecap="round"/></svg>')

# The buttons the picker draws with the chip
CHIP_BUTTONS = ("add this strip", "add this screen", "add a panel", "add a sensor")

# The palette the picker marks a card with when its look takes a colour
PALETTE_ICON = ('<svg class="palette" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" '
                'd="M8 1.2a6.8 6.8 0 0 0 0 13.6c1.1 0 1.7-.6 1.7-1.4 0-.9-.7-1.1-.7-1.9 0-.8.6-1.3 '
                '1.4-1.3h1.8a3 3 0 0 0 3-3C15.2 3.8 12 1.2 8 1.2Z"/><circle cx="4.6" cy="8" r="1.2" '
                'fill="#fff"/><circle cx="5.6" cy="4.6" r="1.2" fill="#fff"/><circle cx="9" cy="3.6" '
                'r="1.2" fill="#fff"/><circle cx="12" cy="5.6" r="1.2" fill="#fff"/></svg>')

# The line drawings beside a look's settings, as the picker draws them
SETTING_ICONS = {
    "Brightness": "<circle cx='8' cy='8' r='2.8'/><path d='M8 1.5v1.8M8 12.7v1.8M1.5 8h1.8M12.7 8h1.8"
                  "M3.4 3.4l1.3 1.3M11.3 11.3l1.3 1.3M3.4 12.6l1.3-1.3M11.3 4.7l1.3-1.3'/>",
    "Speed": "<path d='M2.4 12A6 6 0 1 1 13.6 12'/><path d='M8 10.2L11 5.6'/>",
    "Spread": "<path d='M1.5 8h13M4 5.5L1.5 8 4 10.5M12 5.5L14.5 8 12 10.5'/>",
    "Wave length": "<path d='M1.5 8h13M4 5.5L1.5 8 4 10.5M12 5.5L14.5 8 12 10.5'/>",
    "Trail": "<path d='M1.6 8h6.8M3.2 5.2h5.2M3.2 10.8h5.2'/><circle cx='12.4' cy='8' r='2.2'/>",
}

# The undo and redo arrows above a stretch bar
UNDO_ICON = ("<svg viewBox='0 0 17 17' width='13' height='13' aria-hidden='true'><path d='M6.5 4.5 "
             "L2.5 8 L6.5 11.5'/><path d='M2.5 8 H9.5 A4 4 0 0 1 9.5 15'/></svg>")
REDO_ICON = ("<svg viewBox='0 0 17 17' width='13' height='13' aria-hidden='true'><path d='M9.5 4.5 "
             "L13.5 8 L9.5 11.5'/><path d='M13.5 8 H6.5 A4 4 0 0 0 6.5 15'/></svg>")

# The Reverse button's drawing, a block with an arrow leaving it
REVERSE_ICON = ("<svg width='22' height='11' viewBox='0 0 28 13' aria-hidden='true'><rect x='1' "
                "y='2.5' width='8' height='8' rx='2' fill='currentColor'/><path d='M11 6.5 L16.5 6.5 "
                "M14 3.5 L17 6.5 L14 9.5' fill='none' stroke='currentColor' stroke-width='1.6'/></svg>")

# The colours a picture gives each look, close to the picker's own card faces. A look not
# listed here, such as Nothing, leaves its lights unlit.
LOOK_COLOURS = {
    "Rainbow": ["#ff1a1a", "#ff8c1a", "#ffe600", "#2ee62e", "#1ae6e6", "#1a5cff", "#9b1aff"],
    "Wave": ["#a3b4d1", "#6f7f9c", "#3d475c", "#1f242e", "#1f242e", "#3d475c", "#a3b4d1"],
    "Scanner": ["#2a0606", "#8a1010", "#ff2a1a", "#c01818", "#5a0c0c", "#2a0606"],
    "Chase": ["#ffd21a", "#1f1a08", "#1f1a08", "#6b5a12", "#c9a515", "#ffd21a"],
    "Marquee": ["#1d1712", "#ffbf73", "#1d1712", "#1d1712", "#ffbf73", "#1d1712"],
    "Campfire": ["#ff5a00", "#7a2a00", "#ff5a00", "#ff7a1a", "#ff5a00"],
    "Emergency": ["#1e0606", "#1e0606", "#060b1e", "#060b1e"],
    "Party": ["#14100c", "#ff2bd1", "#14100c", "#ff2bd1", "#0e1e10", "#ff2bd1"],
    "Solid": ["#ffe600"],
    "Colour cycle": ["#ff3b0a"],
    "Colour steps": ["#ff0d0d"],
    "Breathe": ["#1a857d"],
    "Blink": ["#ff2e1f"],
    "Sparkle": ["#3c3c3c", "#d8d8d8", "#666666", "#f2f2f2", "#4a4a4a", "#b0b0b0"],
    "Counter": ["#0e1e10", "#22c55e", "#0e1e10", "#0e1e10"],
    "Traffic light": ["#ff2e1f", "#1e1a16", "#1e1a16", "#1e1a16"],
    "Pelican crossing": ["#ff2e1f", "#1e1a16", "#22c55e", "#1e1a16"],
}

# The looks whose cards carry the palette, since each takes a colour
TAKES_COLOUR = ("Wave", "Scanner", "Chase", "Marquee", "Solid", "Breathe", "Blink", "Sparkle",
                "Counter")

# The looks that play the same from either end, whose Reverse button is greyed
NO_DIRECTION = ("Solid", "Colour cycle", "Colour steps", "Breathe", "Blink", "Sparkle", "Nothing")

# The gallery's groups with the words beside each heading, as the picker shows them
LOOK_GROUPS = {
    "Along the lights": "travelling from one end to the other",
    "Ready-made": "combinations of other looks",
    "All together": "every light shows the same",
    "Individual": "each light plays its own part",
}

# The colours a stretch can be given, in the picker's order, and the swatch for each
NAMED_COLOURS = [("red", "#ff0000"), ("orange", "#ff7a00"), ("yellow", "#ffee00"),
                 ("green", "#00ee00"), ("cyan", "#00f0f0"), ("blue", "#0000ff"),
                 ("purple", "#8000ff"), ("magenta", "#ff00ee"), ("pink", "#ff8080"),
                 ("warm", "#ffc070"), ("white", "#ffffff"), ("cool", "#70b8ff")]

# How the picker draws a light or a strip's LED playing nothing
UNLIT_LIGHT = "#2a2d30"

# How many LEDs a strip has where the picker draws them as beads apart at full size across the
# manual's width, and from how many they have closed up into one continuous strip. Between the
# two, the beads close up in a straight line
BEADS_APART_UP_TO = 30
BEADS_JOIN_FROM = 120

# How many lights a tab's picture shows, a cell for each as the picker draws them
TAB_LIGHTS = 7

# A mono light's colour when off and at full brightness, as red, green and blue
MONO_OFF = (42, 37, 32)
MONO_FULL = (252, 213, 154)

# The longest stretch whose bar blends every light's colour. A longer one blends the look's
# own colours, which draw the same and keep the page smaller.
BAR_BLEND_LIMIT = 8

# The colour of each of the hub's groups, as the picker draws them
GROUP_INKS = {"1": "#d98a1a", "2": "#2f9e6a", "3": "#d0508a"}

# The tints that stand in for a picture or a program's thumbnail, chosen by its name
THUMB_TINTS = ["#1f6feb", "#a347d1", "#c2570f", "#0a7f78", "#b8324a", "#6b7f1a"]

HATCH = "hatch"

# The wiring picture's layout in rem, from manual_mockups.css, which places the ends of its wires.
# A picture has no layout to measure, so the wires are drawn for the manual's full width, where
# the runs are 43.5rem wide, and scale with the picture at any other
WIRE_WIDTH = 43.5
RUN_GAP = 1
CARD_BORDER = 0.125
BOARD_SIDE = 0.6
PLUG_WIDTH = 2.2
LAMP_FOOT = 3.71
PLUG_TOP = 7.47


def selected_items(text):
    """The comma-separated items in a line, each with whether a * marks it selected."""
    items = []
    for item in text.split(","):
        item = item.strip()
        if item:
            items.append((item.lstrip("*").strip(), item.startswith("*")))
    return items


def hex_colour(rgb):
    return "#{:02x}{:02x}{:02x}".format(*(round(part) for part in rgb))


def colour_parts(colour):
    return tuple(int(colour[at:at + 2], 16) for at in (1, 3, 5))


def as_mono(colour):
    """A colour as a mono light shows it, a warm white at the colour's brightness."""
    red, green, blue = colour_parts(colour)
    level = (0.3 * red + 0.59 * green + 0.11 * blue) / 255
    return hex_colour(off + (full - off) * level for off, full in zip(MONO_OFF, MONO_FULL))


def look_colours(name, count, mono):
    """A look's colours blended across count lights, or None for each light it leaves unlit."""
    stops = LOOK_COLOURS.get(name)
    if not stops:
        return [None] * count
    colours = []
    for at in range(count):
        place = at * (len(stops) - 1) / max(count - 1, 1)
        below = int(place)
        above = min(below + 1, len(stops) - 1)
        share = place - below
        blend = hex_colour(low + (high - low) * share for low, high in
                           zip(colour_parts(stops[below]), colour_parts(stops[above])))
        colours.append(as_mono(blend) if mono else blend)
    return colours


def gradient(colours):
    """A left-to-right blend of colours, the one colour given twice where there is only one."""
    return "linear-gradient(90deg, {})".format(", ".join(colours if len(colours) > 1 else colours * 2))


def thumb_tint(name):
    """A stand-in for a thumbnail, a dark wash tinted by the name."""
    tint = THUMB_TINTS[sum(name.encode()) % len(THUMB_TINTS)]
    return "background:linear-gradient(150deg, {}, #191b1d 85%)".format(tint)


def card_lamp(colour, label):
    """One light in a stretch's card, its face lit in colour, or on the picker's hatched tile where
    colour is None for a light playing nothing."""
    return '<span class="cardlamp{}"><i style="background:{}"></i><b>{}</b></span>'.format(
        "" if colour else " unset", colour or UNLIT_LIGHT, html.escape(label))


def strip_beads(colours, apart):
    """A strip stretch's LEDs as beads on a wire, each lit in its colour or unlit where None, and
    closed up by apart, 1 for beads apart at full size and 0 for one continuous strip."""
    beads = "".join('<i><b style="background:{}"></b></i>'.format(colour or UNLIT_LIGHT)
                    for colour in colours)
    return '<span class="stripbeads{}" style="--apart:{:.2f}">{}</span>'.format(
        "" if colours[0] else " unset", apart, beads)


def beads_apart(count):
    """How far a strip of count LEDs is from one continuous strip, as the picker draws one that
    long across the manual's width, 1 for beads apart at full size and 0 for joined."""
    return max(0.0, min(1.0, (BEADS_JOIN_FROM - count) / (BEADS_JOIN_FROM - BEADS_APART_UP_TO)))


def head_steps(stretches, strip, standing_back):
    """The steps at the right of a run's chip row, a strip's zoom then Undo, Redo and Join all,
    greyed while there is one stretch, all standing back in the outputs' wiring view."""
    zoom = ('<span class="round">&#8722;</span><span class="dim">100%</span>'
            '<span class="round">+</span>') if strip else ""
    return ('<span class="headsteps{}">{}<span class="round">{}</span><span class="round">{}</span>'
            '<span class="joinall{}">&#10231; Join all</span></span>').format(
                " back" if standing_back else "", zoom, UNDO_ICON, REDO_ICON,
                " off" if stretches < 2 else "")


def mockup_header(text):
    """The picker's header, written as its title, "Mighty FX Picker". A status after a bar,
    "Mighty FX Picker | Saved.", shows the drive as open, as the header then draws it."""
    title, _, status = text.partition("|")
    if status:
        buttons = ('<span class="button">Change drive</span><span class="button primary">Save to '
                   'board</span>')
        said = '<span class="status">{}</span>'.format(html.escape(status.strip()))
    else:
        buttons = ('<span class="button primary">Open FX drive</span><span class="button off">Save '
                   'to board</span>')
        said = ""
    return ('<div class="pickerhead"><b>{}</b>{}<span class="button arrow">&#9662;</span>'
            '<span class="button">Check board</span>{}</div>').format(
                html.escape(title.strip()), buttons, said)


def mockup_save_menu():
    """The menu under the arrow beside Save to board, with its first setting ticked."""
    return ('<div class="savemenu"><span><i class="tick on"></i>Play saves without an eject'
            '</span><span><i class="tick"></i>Keep the drive hidden at start</span></div>')


def mockup_pages(text, scenes):
    """The two large tabs, written as "*Effects, Programs". A program after an equals sign,
    "Programs=Flip dot sign", is the one chosen. The Effects tab carries the button that adds
    scenes until the picture shows scenes."""
    pages = []
    for item, selected in selected_items(text):
        name, _, chosen = item.partition("=")
        thumb = "effects" if name == "Effects" else "programs"
        extra = ""
        if name == "Effects" and not scenes:
            extra = '<span class="button splitscenes">+ split into scenes</span>'
        elif chosen:
            extra = "<small>{}</small>".format(html.escape(chosen))
        pages.append('<span class="toptab{}"><i class="thumb {}"></i>{}{}</span>'.format(
            " picked" if selected else "", thumb, html.escape(name), extra))
    return '<div class="toptabs">{}</div>'.format("".join(pages))


def tab_preview(name, preview):
    """The small picture under a tab's name of what that part of the board plays."""
    if name == "Screens":
        sizes = preview.split()
        return ('<span class="tabsays">{}</span><span class="tabscreens">{}</span>'.format(
            html.escape(", ".join(sizes)), "<i></i>" * max(len(sizes), 1)))
    if name == "Sound":
        return '<span class="tabsays">nothing</span><span class="tabsound {}"></span>'.format(HATCH)
    # The Sensor tab names what is fitted, with no picture
    if name == "Sensor":
        return '<span class="tabsays">{}</span>'.format(html.escape(preview or "none"))
    mono = preview.startswith("mono ")
    look = preview[5:] if mono else preview
    colours = look_colours(look, TAB_LIGHTS, mono) if look else [None]
    if not colours[0]:
        return '<span class="tabswatch {}"></span>'.format(HATCH)
    return '<span class="tabswatch">{}</span>'.format(
        "".join('<i style="background:{}"></i>'.format(colour) for colour in colours))


def mockup_tabs(text):
    """The row of tabs under Effects, written as "*Outputs=Rainbow, Left strip, Screens=2.8"
    1.54", Sound". A look after an equals sign is what that tab's lights play, "mono Wave" on
    mono lights, and a ~ greys a tab out."""
    tabs = []
    for item, selected in selected_items(text):
        greyed = item.startswith("~")
        name, _, preview = item.lstrip("~").partition("=")
        boxed = " boxed" if name in ("Screens", "Sound") else ""
        tabs.append('<span class="tab{}{}{}"><span class="tabname">{}</span>{}</span>'.format(
            " picked" if selected else "", " greyed" if greyed else "", boxed,
            html.escape(name.replace('"', "")), tab_preview(name, preview)))
    return '<div class="tabrow">{}</div>'.format("".join(tabs))


# Each scene's colour, the Aye Arr Remote's number button in its place, as the picker gives them
SCENE_COLOURS = ("#ed1c24", "#00a651", "#2e3192", "#00aeef", "#ec008c", "#fff200", "#fbad5d",
                 "#d9d6d0", "#84c1ff")

# The picker's icon for the outputs, three lights over a line, and the grip a card is dragged by
LIGHTS_ICON = ('<svg class="partsicon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="3.8" '
               'cy="10" r="3"/><circle cx="12" cy="10" r="3"/><circle cx="20.2" cy="10" r="3"/>'
               '<path d="M1.5 18h21" fill="none" stroke="currentColor" stroke-width="2.2"/></svg>')
GRIP_ICON = ('<svg class="grip" viewBox="0 0 8 12" aria-hidden="true"><circle cx="2" cy="2" r="1.1"/>'
             '<circle cx="6" cy="2" r="1.1"/><circle cx="2" cy="6" r="1.1"/><circle cx="6" cy="6" '
             'r="1.1"/><circle cx="2" cy="10" r="1.1"/><circle cx="6" cy="10" r="1.1"/></svg>')


def mockup_scenes(text):
    """The scenes, written as "Always on, *Scene 1 10s", a scene without a time waiting. They are
    drawn as the picker's tray, Always on's card its first column and each scene a card in its
    colour, and under them the folder tab holding the selected one's own settings."""
    items = list(selected_items(text))
    scenes = [(item, selected) for item, selected in items if item != "Always on"]
    always_picked = any(selected for item, selected in items if item == "Always on")
    cards = []
    tab = ""
    named = [item.rpartition(" ")[0] or item for item, _ in scenes]
    for at, (item, selected) in enumerate(scenes):
        name, _, seconds = item.rpartition(" ")
        if not (seconds.endswith("s") and seconds[:-1].isdigit()):
            name, seconds = item, ""
        colour = SCENE_COLOURS[at % len(SCENE_COLOURS)]
        # The only scene with a time goes back to itself, which the picker says on its card and tab
        lone = len(scenes) == 1
        turn = seconds + (", again" if lone else "") if seconds else "waits"
        cards.append('<span class="scenecard{}" style="--scene:{}"><b>{}{}</b><span class="parts">{}'
                     '</span><small>{}</small></span>'.format(
                         " picked" if selected else "", colour, html.escape(name), GRIP_ICON,
                         LIGHTS_ICON, html.escape(turn)))
        if selected:
            if not seconds:
                ending, place = "", "waits forever"
            elif lone:
                ending = ('<span class="field">{}</span><span class="dim">s, then itself</span>'
                          .format(seconds[:-1]))
                place = "then itself"
            else:
                ending = ('<span class="field">{}</span><span class="dim">s, then</span><span '
                          'class="field">the next scene</span>'.format(seconds[:-1]))
                place = "then " + named[(at + 1) % len(scenes)]
            tab = ('<div class="scenefold" style="--scene:{}"><div class="scenetab"><span class="field '
                   'wide">{}</span><span class="dim">{}</span>{}<span class="button">&#8630; Restart'
                   '</span></div><span class="dim small">Scene {} of {}, {}</span><span '
                   'class="button">Remove scene</span></div>').format(
                       colour, html.escape(name), "shows for" if seconds else "waits", ending,
                       at + 1, len(scenes), html.escape(place))
    if always_picked:
        tab = ('<div class="scenefold" style="--scene:#8f8a82"><div class="scenetab"><span class="dim">'
               'Always on plays under every scene. A scene that uses the same lights, screen or '
               'sound overrides it while showing.</span></div><span class="dim small">Under {} '
               'scene{}</span></div>').format(len(scenes), "" if len(scenes) == 1 else "s")
    always = ('<span class="alwayscard"><b>Always on</b><small>Plays under every scene</small>'
              '<span class="parts">{}</span></span>').format(LIGHTS_ICON)
    cards.append('<span class="scenecard add">+ another scene</span>')
    return '<div class="scenetray{}">{}<div class="scenecards">{}</div></div>{}'.format(
        " picked" if always_picked else "", always, "".join(cards), tab)


# A strip's colour order as its choice names it, where the choice says more than the order
ORDERS_SHOWN = {"GRB": "GRB (most strips)"}


def strip_chip(count, order):
    """A strip's chip as the picker draws it, its number of LEDs and its colour order to change,
    then its remove button."""
    return ('<span class="badge strip">{}<b>Strip</b><span class="field">{}</span> LEDs '
            '<span class="field">{} &#9662;</span><span class="remove">remove</span></span>').format(
                CHIP_ICON, html.escape(count), html.escape(ORDERS_SHOWN.get(order, order)))


def mockup_badge(text, kind, steps):
    """The board setting label at the top of a tab, written as its name and what it says, then
    any hint after a bar, "Wiring, every output is one colour light | Drag each light ...". A
    strip's is written "Strip, 66 LEDs, GRB" and drawn as its chip. A strip's count of
    stretches follows its label, and steps go at the right of the row."""
    label, _, hint = text.partition("|")
    name, _, note = label.partition(",")
    said = '<span class="hint">{}</span>'.format(html.escape(hint.strip())) if hint else ""
    if kind == "strip":
        count, _, order = note.partition(",")
        return '<div class="badgerow">{}{}{}</div>'.format(
            strip_chip(count.split()[0], order.strip()), said, steps)
    return '<div class="badgerow"><span class="badge {}">{}<b>{}</b> {}</span>{}{}</div>'.format(
        kind, CHIP_ICON, html.escape(name.strip()), html.escape(note.strip()), said, steps)


def mockup_run(kind, label, text, labels=None, pointed=False):
    """One run of lights as the picker shows it, a card for each stretch holding its lights over a
    band of what it plays, written as "Rainbow 4, *Solid 3".

    A light is numbered along the run unless label names every light in it, or labels names
    each light in turn. A strip's LEDs are beads on a wire, from a lead block before the first card
    to a ring after the last. The selected stretch carries the notch of the settings under it
    where pointed is set.
    """
    items = []
    for item, selected in selected_items(text):
        name, _, length = item.rpartition(" ")
        items.append((name, int(length), selected))
    total = sum(length for _, length, _ in items)
    strip = kind == "strip"
    apart = beads_apart(total)
    cards = []
    count = 0
    for name, length, selected in items:
        colours = look_colours(name, length, kind == "mono")
        if strip:
            inside = strip_beads(colours, apart)
        else:
            inside = '<span class="cardlamps">{}</span>'.format("".join(
                card_lamp(colour, labels[count + at] if labels else label or str(count + at + 1))
                for at, colour in enumerate(colours)))
        if colours[0]:
            if length > BAR_BLEND_LIMIT:
                colours = look_colours(name, len(LOOK_COLOURS[name]), kind == "mono")
            lit = '<span class="lit" style="background:{}"></span>'.format(gradient(colours))
        else:
            lit = '<span class="lit {}"></span>'.format(HATCH)
        picked = (" picked pointed" if pointed else " picked") if selected else ""
        cards.append('<span class="sec{}" style="flex:{} 1 0">{}{}<span class="says">{} <em>{}</em>'
                     '</span></span>'.format(picked, length, inside, lit, html.escape(name), length))
        count += length
    if strip:
        cards = ['<span class="wireend"><i class="lead"></i></span>'] + cards + [
            '<span class="wireend"><i class="tail"></i></span>']
    return '<div class="run" style="flex:{} 1 0"><div class="bar{}">{}</div></div>'.format(
        total, " strip" if strip else "", "".join(cards))


def mockup_settings(text, pointing, split):
    """The selected stretch's settings, written as its look, where it plays, then each setting
    and where its slider sits out of 100, "Rainbow, on outputs 1 to 7, Brightness 100, Speed 45".
    A colour, "colour yellow", draws the row of colours with that one chosen.

    The settings are drawn in the picked stretch's colour where pointing is set, its card drawing
    the notch over their top edge. A strip's stretch has Split into beside Reverse where split is
    set.
    """
    parts = [part.strip() for part in text.split(",")]
    look, where, settings = parts[0], parts[1], parts[2:]
    reverse = '<span class="button reverse{}">{} Reverse</span>'.format(
        " off" if look in NO_DIRECTION else "", REVERSE_ICON)
    if split:
        reverse = ('<span class="setbuttons"><span class="toolset"><span class="toolsays">&#9986; Split '
                   'into<span class="field">3</span></span><span class="toolact">stretches</span>'
                   '<span class="toolact">lights each</span></span>{}</span>').format(reverse)
    rows = []
    swatches = ""
    for setting in settings:
        name, _, value = setting.rpartition(" ")
        if name == "colour":
            swatches = '<div class="swatches">{}<span class="swatch"><i class="custom"></i>custom</span></div>'.format(
                "".join('<span class="swatch{}"><i style="background:{}"></i>{}</span>'.format(
                    " chosen" if colour == value else "", ink, colour)
                    for colour, ink in NAMED_COLOURS))
            continue
        icon = SETTING_ICONS.get(name, "")
        rows.append('<span class="setname"><svg class="seticon" viewBox="0 0 16 16" aria-hidden="true">'
                    '{}</svg>{}</span><span class="slider"><i style="width:{}%"></i></span>'.format(
                        icon, html.escape(name), int(value)))
    sliders = ('<div class="sliders"><div class="setgrid">{}</div><span class="drawer">&#8249;</span>'
               '</div>').format("".join(rows)) if rows else ""
    return ('<div class="settings{}"><div class="sethead"><b>{}</b> <span class="dim">{}</span>{}'
            '</div>{}{}</div>').format(" pointing" if pointing else "", html.escape(look), html.escape(where), reverse,
                                      swatches, sliders)


def mockup_cards(text, mono, group):
    """A row of gallery cards under its group's heading, the first group carrying Nothing, as
    the picker shows them. Cards are drawn in a mono light's colours where mono is set."""
    items = selected_items(text)
    head = ""
    if group:
        # Nothing is the small card at the end of the first group's heading, not a card of its own
        nothing = ""
        if group == "Along the lights":
            chosen = any(name == "Nothing" and selected for name, selected in items)
            nothing = '<span class="nothingcard{}"><i class="{}"></i>Nothing</span>'.format(
                " picked" if chosen else "", HATCH)
            items = [item for item in items if item[0] != "Nothing"]
        head = ('<div class="galleryhead"><span class="fold">&#8963;</span>{}<span class="dim">{}'
                '</span>{}</div>').format(html.escape(group), LOOK_GROUPS.get(group, ""), nothing)
    cards = []
    for name, selected in items:
        stops = LOOK_COLOURS.get(name, [])
        faces = "".join('<span style="background:{}"></span>'.format(
            as_mono(colour) if mono else colour) for colour in stops)
        mark = PALETTE_ICON if name in TAKES_COLOUR else ""
        cards.append('<span class="card{}{}"><span class="face">{}</span>'
                     '<span class="name">{}{}</span></span>'.format(
                         " picked" if selected else "", "" if stops else " nothing", faces,
                         html.escape(name), mark))
    return '{}<div class="gallery">{}</div>'.format(head, "".join(cards))


def wire_lines(counts):
    """The wires from each connector to the light it feeds, as the picker draws them, faint curves
    leaving the connector straight up and meeting the light straight down. Each run takes its
    share of the width by its count of lights."""
    room = WIRE_WIDTH - RUN_GAP * (len(counts) - 1)
    lamps = []
    left = 0
    for count in counts:
        width = room * count / sum(counts)
        inside = width - 2 * CARD_BORDER
        lamps.extend(left + CARD_BORDER + (at + 0.5) * inside / count for at in range(count))
        left += width + RUN_GAP
    total = len(lamps)
    step = (WIRE_WIDTH - 2 * BOARD_SIDE - PLUG_WIDTH) / max(total - 1, 1)
    plugs = [BOARD_SIDE + PLUG_WIDTH / 2 + at * step for at in range(total)]
    tall = PLUG_TOP - LAMP_FOOT
    paths = "".join('<path d="M{0:.2f} {2:.2f}C{0:.2f} {3:.2f} {1:.2f} {3:.2f} {1:.2f} 0"/>'.format(
        plug, lamp, tall, tall / 2) for plug, lamp in zip(plugs, lamps))
    return ('<svg class="wirelines" viewBox="0 0 {} {:.2f}" preserveAspectRatio="none" '
            'style="top:{}rem;height:{:.2f}rem" aria-hidden="true">{}</svg>').format(
                WIRE_WIDTH, tall, LAMP_FOOT, tall, paths)


def mockup_wiring(text, look):
    """The lights while the board is set up, a tile each in a stretch's card, over the board's
    edge with its connectors and a wire from each connector to its light, written as their labels
    with a bar between the two sides, "1, 2, 3, 4, 5, 6 | RGB". The first side is mono where look
    starts "mono ", and look colours the lights as the picker would show it playing. The board's
    edge says the lights are in wiring order, so Reset wiring is greyed."""
    sides = []
    connectors = []
    counts = []
    for at, group in enumerate(text.split("|")):
        labels = [label.strip() for label in group.split(",")]
        mono = look.startswith("mono ") and at == 0
        name = look[5:] if look.startswith("mono ") else look
        played = "{} {}".format(name or "Nothing", len(labels))
        side = mockup_run("mono" if mono else "colour", "", played, labels)
        sides.append(side)
        connectors.extend(labels)
        counts.append(len(labels))
    plugs = "".join('<span class="plug"><b>{}</b></span>'.format(html.escape(label))
                    for label in connectors)
    return ('<div class="wiring"><div class="runs setup">{}</div>{}<div class="wireboard">'
            '<div class="connectors">{}</div><div class="wirefoot"><span>All lights are in wiring '
            'order. Hover over a light or connector to highlight its wire.</span>'
            '<span class="wirereset off">Reset wiring</span></div></div></div>').format(
                "".join(sides), wire_lines(counts), plugs)


def mockup_strip_setup(text):
    """A strip's chip, written as its number of LEDs, and the strip's LEDs under it in one
    stretch playing nothing."""
    count = int(text.strip())
    run = mockup_run("strip", "", "Nothing {}".format(count))
    return ('<div class="badgerow">{}<span class="hint">Cut into 1 stretch</span>{}</div>'
            '<div class="runs">{}</div>').format(strip_chip(str(count), "GRB"),
                                                 head_steps(1, True, False), run)


def mockup_screen_mode(text):
    """The choice between a screen on each connector and a Screen Hub across both, written as
    "hub" where the hub is chosen."""
    hub = text.strip() == "hub"
    return ('<div class="segment"><span class="{}">{}A screen on each connector</span>'
            '<span class="{}">A Screen Hub across both</span></div>').format(
                "" if hub else "on", CHIP_ICON, "on" if hub else "")


def places_said(places):
    """Hub positions as the picker names them, a run of three or more letters as "A-C"."""
    runs = []
    for place in places:
        if runs and ord(place) == ord(runs[-1][-1]) + 1:
            runs[-1].append(place)
        else:
            runs.append([place])
    return ",".join(run[0] + "-" + run[-1] if len(run) > 1 else run[0] for run in runs)


def hub_places(text):
    """The hub's positions in order, each written as its letter, then the picture it shows and
    its group after an equals sign, "A=skyline.png 1", as (letter, picture, group)."""
    places = []
    for item in text.split(","):
        letter, _, shows = item.strip().partition("=")
        picture, _, group = shows.strip().partition(" ")
        places.append((letter.strip(), picture, group.strip()))
    return places


def mockup_hub(text, places):
    """The Screen Hub's box, written as how its cables are plugged in, "SPI on A, Selects on B",
    with its positions under one shared backlight and a note on how fast a group plays."""
    cells = []
    for letter, picture, group in places:
        members = [other for other, _, theirs in places if group and theirs == group]
        others = [other for other in members if other != letter]
        if not group:
            said = "on its own"
        elif others:
            said = "grouped with " + places_said(others)
        else:
            said = "alone in group " + group
        numbers = "".join('<span class="{}"{}>{}</span>'.format(
            "on" if number == group else "",
            ' style="background:{}"'.format(GROUP_INKS[number]) if number == group else "", number)
            for number in GROUP_INKS)
        display = ('<i class="lcd small" style="{}"></i>'.format(thumb_tint(picture)) if picture
                   else '<i class="lcd small"><small>no picture</small></i>')
        ink = ' style="--group:{}"'.format(GROUP_INKS[group]) if group else ""
        cells.append('<span class="place{}"{}><span class="placehead"><b>{}</b><span>{}2.8"</span>'
                     '</span><span class="breakout small"><span class="holes"></span>{}'
                     '<span class="holes"></span></span><span class="dim small">{}</span>'
                     '<span class="remove">remove</span>'
                     '<span class="segment small groups">{}</span><span class="groupsaid">{}</span>'
                     '</span>'.format(" grouped" if group else "", ink, letter, CHIP_ICON, display,
                                      html.escape(picture or "nothing"), numbers, said))

    notes = ""
    for number in GROUP_INKS:
        members = [letter for letter, _, group in places if group == number]
        pictures = {picture for letter, picture, group in places if group == number}
        if members and pictures and "" not in pictures:
            moving = next(iter(pictures)).endswith(".gif")
            notes += '<div class="hubnote"><b>{}</b> {}</div>'.format(
                places_said(members),
                "play the same animation together, as fast as a single screen." if moving
                else "show a still picture, sent once, so nothing slows down.")

    return ('<div class="screens"><span class="screen hub"><span class="screenhead"><b>Screen Hub'
            '</b><span class="field">{}{} &#9662;</span><span class="small">{} of {} fitted</span>'
            '</span><span class="backlight"><span class="dim">shared backlight</span><span '
            'class="slider"><i style="width:100%"></i></span><span>100%</span></span><span '
            'class="places">{}</span>{}</span></div>').format(CHIP_ICON, html.escape(text.strip()), len(places), len(places),
                                "".join(cells), notes)


def hub_targets(places):
    """What a picture can be sent to on a hub, each group by its number then each position on
    its own, as the buttons under a picture show them."""
    groups = [number for number in GROUP_INKS if any(group == number for _, _, group in places)]
    return groups + [letter for letter, _, group in places if not group]


def mockup_screen(letter, text, paired):
    """One screen as the Screens tab draws it, written as its size then the picture it shows,
    "2.8 inch, skyline.png". A screen with a partner carries the Paired button, drawn pressed
    where paired is "on"."""
    size, _, shown = text.partition(",")
    size = size.strip()
    shown = shown.strip()
    title = "Screen {}".format(letter) if letter else "Screen"
    display = ('<i class="lcd" style="{}"></i>'.format(thumb_tint(shown)) if shown
               else '<i class="lcd"><small>no picture</small></i>')
    partner = "B" if letter == "A" else "A"
    if paired == "on":
        pair = ('<span class="button small paired">Paired</span><span class="dim small">paired with '
                'Screen {}</span>').format(partner)
    elif paired:
        pair = '<span class="button small">Paired</span><span class="dim small">on its own</span>'
    else:
        pair = ""
    showing = ("<span>{}</span>".format(html.escape(shown)) if shown else
               "<span>nothing showing</span>")
    turns = "".join('<span class="{}">{}&#176;</span>'.format("on" if turn == 0 else "", turn)
                    for turn in (0, 90, 180, 270))
    return ('<span class="screen screen{}"><span class="screenhead"><b>{}</b><span class="field">'
            '{}{} &#9662;</span><span class="remove">remove</span></span>'
            '<span class="backlight"><span class="dim">backlight</span>'
            '<span class="slider"><i style="width:100%"></i></span><span>100%</span></span>'
            '<span class="breakout"><span class="holes"></span><small>{}" LCD</small>{}'
            '<span class="holes"></span></span>{}<span class="showing">{}</span>'
            '<span class="orientation"><span class="dim">Rotation</span><span class="segment small">'
            '{}</span><span class="button small">&#8646; Mirror</span></span></span>').format(
                letter or "A", title, CHIP_ICON, html.escape(size), html.escape(size.split()[0]),
                display, pair, showing, turns)


def mockup_pictures(text, letters, targets):
    """The pictures on the drive, each written with what shows it after an equals sign,
    "skyline.png=A", and a bar of buttons under each. The buttons are one for each screen, or
    on a hub one for each of targets and then all."""
    tiles = []
    for item in text.split(","):
        name, _, showing = item.strip().partition("=")
        kind = "gif" if name.endswith(".gif") else "drawing" if "." not in name else ""
        tag = '<small class="tag">{}</small>'.format(kind) if kind else ""
        if targets:
            buttons = "".join('<span class="{}"{}>{}</span>'.format(
                "on" if target == showing else "",
                ' style="background:{}"'.format(GROUP_INKS[target])
                if target == showing and target in GROUP_INKS else "", target)
                for target in targets) + "<span>all</span>"
        elif letters:
            buttons = "".join('<span class="{}">{}</span>'.format(
                "on screen" + letter if showing == letter else "", letter) for letter in letters)
        else:
            buttons = '<span class="{}">Show</span>'.format("on screenA" if showing else "")
        tiles.append('<span class="picture"><span class="face" style="{}">{}</span>'
                     '<span class="pickbar">{}</span></span>'.format(thumb_tint(name), tag, buttons))
    tiles.append('<span class="addtile"><b>+</b>add pictures or drawings</span>')
    return ('<div class="galleryhead"><span class="fold">&#8963;</span>On the drive<span class="dim">'
            'your own pictures and drawings</span></div><div class="pictures">{}</div>').format(
                "".join(tiles))


def mockup_sounds(text, looping):
    """The sounds on the drive, written as their names with Nothing among them, the selected one
    marked with a *. Loop and Nothing sit on one line above the sounds, as the picker has them
    before there are scenes, and Silence is read as Nothing."""
    cards = []
    nothing = False
    for name, selected in selected_items(text):
        if name in ("Nothing", "Silence"):
            nothing = selected
            continue
        # A sound's preview is its outline, loud peaks red over a quiet blue line
        heights = [95, 70, 100, 60, 90, 80, 100, 65, 95, 85, 100, 70, 90, 75, 100, 60, 85, 95]
        face = "".join('<i style="height:{}%"></i><b></b>'.format(height) for height in heights)
        cards.append('<span class="sound{}"><span class="wave">{}</span><span class="name">{}'
                     '</span><span class="soundfoot"><span class="dim">1s</span><span class="play">'
                     '&#9654;</span></span></span>'.format(" picked" if selected else "", face,
                                                         html.escape(name)))
    cards.append('<span class="addtile"><b>+</b>add sounds</span>')
    return ('<div class="soundhead"><span class="button{}">&#8635; Loop</span><span class="soundvolume">'
            '<span class="dim">volume</span><span class="slider"><i style="width:100%"></i></span>'
            '<span>100%</span></span><span class="nothingcard{}">'
            '<i class="{}"></i>Nothing</span></div><div class="galleryhead"><span class="fold">'
            '&#8963;</span>On the drive<span class="dim">your own sounds</span></div>'
            '<div class="sounds">{}</div>').format(" on" if looping else "",
                                                   " picked" if nothing else "", HATCH,
                                                   "".join(cards))


def mockup_note(text):
    """The note at the top of the Programs tab, written as the chosen program's file, or left
    empty when none is chosen."""
    program = text.strip()
    if program:
        said = ("The board runs {} instead of the effects. The effects are kept, and play if the "
                "program is missing or stops, with the reason in errors.txt.").format(
                    html.escape(program))
        none = '<span class="button">Choose none</span>'
    else:
        said = "No program chosen, so the board plays the effects. Choose one below to run it instead."
        none = ""
    return '<div class="prognote">{}<span>{}</span>{}</div>'.format(CHIP_ICON, said, none)


def mockup_hero(text):
    """The chosen program's preview, written as its name, what it does and its file, separated
    by bars."""
    name, does, path = (part.strip() for part in text.split("|"))
    return ('<div class="proghero"><span class="herothumb" style="{}"></span><span><b>{}</b>'
            '<span>{}</span><span class="dim small">{}</span></span></div>').format(
                thumb_tint(name), html.escape(name), html.escape(does), html.escape(path))


def mockup_with(text):
    """The hardware buttons that filter the programs, all turned on, then all and none."""
    return '<div class="filters"><span class="dim">With:</span>{}<u>all</u><u>none</u></div>'.format(
        "".join('<span class="chip">{}</span>'.format(html.escape(name.strip()))
                for name in text.split(",")))


def mockup_programs(heading, text):
    """One group of programs under its heading, written with the words beside the heading
    after a bar, "Retro displays | mechanical, glowing and segment displays", and the chosen
    program marked with a *."""
    name, _, says = heading.partition("|")
    cards = "".join('<span class="progcard{}"><span class="face" style="{}"></span>'
                    '<span class="name">{}</span></span>'.format(
                        " picked" if selected else "", thumb_tint(card), html.escape(card))
                    for card, selected in selected_items(text))
    return ('<div class="galleryhead"><span class="fold">&#8963;</span>{}<span class="dim">{}</span>'
            '</div><div class="programs">{}</div>').format(
                html.escape(name.strip()), html.escape(says.strip()), cards)


def picker_mockup(body):
    """A picture of part of the picker, from the lines of a ```picker fence.

    Runs of lights on consecutive lines sit side by side, as do screens. A line whose key the
    picture has no part for stops the build, naming the key.
    """
    keys = [line.partition(":")[0].split()[0] for line in body if line.strip()]
    parts = []
    runs = []
    screens = []
    run_lines = [line for line in body if line.partition(":")[0].split()[:1] in (
        ["colour"], ["mono"], ["strip"])]
    # The settings point up at the selected stretch where the picture has both
    pointing = "settings" in keys and any("*" in line for line in run_lines)
    strip = any(line.startswith("strip") for line in run_lines)
    stretches = sum(len(selected_items(line.partition(":")[2])) for line in run_lines)
    # The chip row carries the run's steps, and a strip's count of its stretches. In the outputs'
    # wiring view, its lights are drawn by the wiring line and the steps stand back
    steps = head_steps(stretches, strip, "wiring" in keys) if run_lines or "wiring" in keys else ""
    if strip:
        steps = '<span class="hint">Cut into {} stretch{}</span>{}'.format(
            stretches, "" if stretches == 1 else "es", steps)
    letters = [line.partition(":")[0].split()[1] for line in body
               if line.startswith("screen ") and len(line.partition(":")[0].split()) > 1]
    # A hub's positions are given on their own line and drawn with the hub's box
    places = [hub_places(line.partition(":")[2]) for line in body if line.startswith("places:")]
    places = places[0] if places else []
    for line in body:
        if not line.strip():
            continue
        key, _, text = line.partition(":")
        kind, *rest = key.split()
        if kind in ("colour", "mono", "strip"):
            runs.append(mockup_run(kind, " ".join(rest), text, pointed=pointing))
            continue
        if kind == "screen":
            pairing = "on" if "paired" in rest else len(letters) > 1
            screens.append(mockup_screen(rest[0] if rest else "", text, pairing))
            continue
        if kind == "places":
            continue
        if runs:
            parts.append('<div class="runs">{}</div>'.format("".join(runs)))
            runs = []
        if screens:
            parts.append('<div class="screens">{}</div>'.format("".join(screens)))
            screens = []

        if kind == "header":
            parts.append(mockup_header(text))
        elif kind == "savemenu":
            parts.append(mockup_save_menu())
        elif kind == "pages":
            parts.append(mockup_pages(text, "scenes" in keys))
        elif kind == "scenes":
            parts.append(mockup_scenes(text))
        elif kind == "tabs":
            parts.append(mockup_tabs(text))
        elif kind == "badge":
            parts.append(mockup_badge(text, " ".join(rest), steps))
        elif kind == "settings":
            parts.append(mockup_settings(text, pointing, strip))
        elif kind == "cards":
            mono = rest[:1] == ["mono"]
            parts.append(mockup_cards(text, mono, " ".join(rest[1:] if mono else rest)))
        elif kind == "wiring":
            parts.append(mockup_wiring(text, " ".join(rest)))
        elif kind == "stripsetup":
            parts.append(mockup_strip_setup(text))
        elif kind == "screenmode":
            parts.append(mockup_screen_mode(text))
        elif kind == "hub":
            parts.append(mockup_hub(text, places))
        elif kind == "pictures":
            parts.append(mockup_pictures(text, letters, hub_targets(places) if places else []))
        elif kind == "sounds":
            parts.append(mockup_sounds(text, rest == ["loop"]))
        elif kind == "note":
            parts.append(mockup_note(text))
        elif kind == "hero":
            parts.append(mockup_hero(text))
        elif kind == "with":
            parts.append(mockup_with(text))
        elif kind == "programs":
            parts.append(mockup_programs(" ".join(rest), text))
        else:
            sys.exit("a picker picture has no {!r} line".format(kind))
    if runs:
        parts.append('<div class="runs">{}</div>'.format("".join(runs)))
    if screens:
        parts.append('<div class="screens">{}</div>'.format("".join(screens)))

    return '<div class="mockup" role="img" aria-label="Part of the picker">\n{}\n</div>'.format(
        "\n".join(parts))
