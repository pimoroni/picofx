"""Draws the pictures of the picker that the manual shows, from a ```picker fence in its parts.

A picture is built from simplified copies of the picker's own parts, so it costs a few hundred
bytes where a screenshot would cost tens of thousands, and the manual template holds the styles
that make it look like the picker. Each line of the fence draws one part, in the order given,
and the function drawing that part describes what its line holds. A * before an item marks it
as the one the picture shows selected.

    ```picker
    tabs: *Outputs=Rainbow, Left strip, Right strip, Screens=2.8" 1.54", Sound
    colour: Rainbow 4, *Solid 3
    tools:
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
CHIP_BUTTONS = ("Edit board", "Done")

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

# How the picker draws a light playing nothing, and a strip's LED playing nothing
UNLIT_LIGHT = "#2a2d30"
UNLIT_LED = "#e4e0d9"

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


def look_swatch(name, mono=False):
    """The background that shows a look in a small space, or the picker's hatching for Nothing."""
    colours = look_colours(name, len(LOOK_COLOURS.get(name, [])) or 1, mono)
    return "background:{}".format(gradient(colours)) if colours[0] else ""


def thumb_tint(name):
    """A stand-in for a thumbnail, a dark wash tinted by the name."""
    tint = THUMB_TINTS[sum(name.encode()) % len(THUMB_TINTS)]
    return "background:linear-gradient(150deg, {}, #191b1d 85%)".format(tint)


def lamp(colour, label, ringed=False):
    return '<span class="lamp{}"><i style="background:{}"></i><b>{}</b></span>'.format(
        " ringed" if ringed else "", colour, html.escape(label))


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
        return '<span class="tabsays">silence</span><span class="tabsound {}"></span>'.format(HATCH)
    mono = preview.startswith("mono ")
    look = preview[5:] if mono else preview
    swatch = look_swatch(look, mono) if look else ""
    return '<span class="tabswatch {}" style="{}"></span>'.format("" if swatch else HATCH, swatch)


def mockup_tabs(text, editing):
    """The row of tabs under Effects, written as "*Outputs=Rainbow, Left strip, Screens=2.8"
    1.54", Sound". A look after an equals sign is what that tab's lights play, "mono Wave" on
    mono lights, and a ~ greys a tab out. The row ends in Edit board, or in Done while the
    board is being set up."""
    tabs = []
    for item, selected in selected_items(text):
        greyed = item.startswith("~")
        name, _, preview = item.lstrip("~").partition("=")
        boxed = " boxed" if name in ("Screens", "Sound") else ""
        tabs.append('<span class="tab{}{}{}"><span class="tabname">{}</span>{}</span>'.format(
            " picked" if selected else "", " greyed" if greyed else "", boxed,
            html.escape(name.replace('"', "")), tab_preview(name, preview)))
    end = '<span class="button{}">{}{}</span>'.format(
        " done" if editing else "", CHIP_ICON, "Done" if editing else "Edit board")
    return '<div class="tabrow{}">{}{}</div>'.format(" editing" if editing else "", "".join(tabs), end)


def mockup_scenes(text):
    """The scene tabs, written as "Always on, *Scene 1 10s", and under them the selected scene's
    own settings."""
    tabs = []
    settings = ""
    for item, selected in selected_items(text):
        name, _, seconds = item.rpartition(" ")
        if not (seconds.endswith("s") and seconds[:-1].isdigit()):
            name, seconds = item, ""
        stripe = ('<i class="scenestripe {}"></i>'.format(HATCH) if not seconds else
                  '<i class="scenestripe" style="background:{}"></i>'.format(
                      gradient(LOOK_COLOURS["Rainbow"])))
        small = seconds if seconds else "under every scene"
        cross = '<span class="cross">&#215;</span>' if seconds else ""
        tabs.append('<span class="scenetab{}">{}{}{}<small>{}</small></span>'.format(
            " picked" if selected else "", stripe, html.escape(name), cross, html.escape(small)))
        if selected and seconds:
            settings = ('<div class="scenerow"><span class="field wide">{}</span><span class="dim">'
                        'shows for</span><span class="field">{}</span><span class="dim">seconds'
                        '</span><span class="button">&#8630; Restart</span></div>').format(
                            html.escape(name), seconds[:-1])
    tabs.append('<span class="scenetab add">+ another scene</span>')
    return '<div class="scenetabs">{}</div>{}'.format("".join(tabs), settings)


def mockup_badge(text, kind):
    """The board setting label at the top of a tab, written as its name and what it says, then
    any hint after a bar, "Wiring, every output is one colour light | Drag each light ..."."""
    label, _, hint = text.partition("|")
    name, _, note = label.partition(",")
    said = '<span class="hint">{}</span>'.format(html.escape(hint.strip())) if hint else ""
    return '<div class="badgerow"><span class="badge {}">{}<b>{}</b> {}</span>{}</div>'.format(
        kind, CHIP_ICON, html.escape(name.strip()), html.escape(note.strip()), said)


def strip_drawing(colours, ringed):
    """A strip drawn as the picker's wireRun draws it, its LEDs as beads on a wire that snakes
    back and forth thirty to a row, with a block at the lead and a ring at the tail. Each of
    colours is one LED's, or None where it is unlit, and ringed is the first and last LED of
    the selected stretch, or None."""
    size, gap, per_row, edge, tail, room = 11, 2.5, 30, 10, 6, 4
    count = len(colours)
    rows = -(-count // per_row)
    across = min(count, per_row)
    wide = across * size + (across - 1) * gap
    pitch = size + gap * 2
    high = rows * pitch - gap * 2 + 2
    full = edge * 2 + wide
    wire = 'fill="none" stroke="#c9c3b9" stroke-width="1.8"'

    def place(led):
        row, column = divmod(led, per_row)
        # Every other row runs back the way the one before it came
        if row % 2:
            column = per_row - 1 - column
        return edge + column * (size + gap), row * pitch + 1, row

    def middle(row):
        return row * pitch + 1 + size / 2

    parts = []
    for row in range(rows - 1):
        x = edge + wide if row % 2 == 0 else edge
        bulge = x + edge if row % 2 == 0 else x - edge
        parts.append('<path d="M{0:g} {1:g} C{2:g} {1:g} {2:g} {3:g} {0:g} {3:g}" {4}/>'.format(
            x, middle(row), bulge, middle(row + 1), wire))
    for row in range(rows):
        xs = [place(led)[0] for led in range(row * per_row, min(count, (row + 1) * per_row))]
        parts.append('<path d="M{:g} {:g} L{:g} {:g}" {}/>'.format(
            min(xs), middle(row), max(xs) + size, middle(row), wire))
    parts.append('<path d="M0 {0:g} L{1:g} {0:g}" {2}/><rect x="0" y="{3:g}" width="4.6" height="6.8" '
                 'rx="1.4" fill="#8f8a81"/>'.format(middle(0), place(0)[0], wire, middle(0) - 3.4))
    for led, colour in enumerate(colours):
        x, y, _ = place(led)
        parts.append('<rect x="{:g}" y="{:g}" width="{}" height="{}" rx="2.4" fill="{}" '
                     'stroke="rgba(0,0,0,.12)" stroke-width="0.6"/>'.format(
                         x, y, size, size, colour or UNLIT_LED))

    # The selected stretch is outlined row by row, as it wraps
    if ringed:
        spans = {}
        for led in range(ringed[0], ringed[1] + 1):
            x, y, row = place(led)
            low, high_x, _ = spans.get(row, (x, x, y))
            spans[row] = (min(low, x), max(high_x, x), y)
        for low, high_x, y in spans.values():
            parts.append('<rect class="ringed" x="{:g}" y="{:g}" width="{:g}" height="{:g}" '
                         'rx="4"/>'.format(low - gap / 2, y - 2.2, high_x - low + size + gap,
                                           size + 4.4))

    last_x, _, last_row = place(count - 1)
    rightward = last_row % 2 == 0
    start = last_x + size if rightward else last_x
    end = start + (tail if rightward else -tail)
    parts.append('<path d="M{0:g} {1:g} L{2:g} {1:g}" {3}/><circle cx="{2:g}" cy="{1:g}" r="2.4" '
                 'fill="#fff" stroke="#a9a49b" stroke-width="1.6"/>'.format(
                     start, middle(last_row), end, wire))
    return ('<svg class="stripdrawing" viewBox="{:g} {:g} {:g} {:g}" preserveAspectRatio="xMinYMid '
            'meet" aria-hidden="true">{}</svg>').format(-room, -room, full + room * 2,
                                                       high + room * 2, "".join(parts))


def mockup_run(kind, label, text):
    """One run of lights in its white box, then the bar of its stretches, written as
    "Rainbow 4, *Solid 3".

    A light is numbered along the run unless label names every light in it, and a strip's LEDs
    are drawn small and carry no number.
    """
    lights = []
    strip_colours = []
    ringed = None
    sections = []
    for item, selected in selected_items(text):
        name, _, length = item.rpartition(" ")
        length = int(length)
        colours = look_colours(name, length, kind == "mono")
        if kind == "strip":
            if selected:
                ringed = (len(strip_colours), len(strip_colours) + length - 1)
            strip_colours.extend(colours)
        else:
            for colour in colours:
                lights.append(lamp(colour or UNLIT_LIGHT, label or str(len(lights) + 1), selected))

        if colours[0]:
            if length > BAR_BLEND_LIMIT:
                colours = look_colours(name, len(LOOK_COLOURS[name]), kind == "mono")
            lit = '<span class="lit" style="background:{}"></span>'.format(gradient(colours))
        else:
            lit = '<span class="lit {}"></span>'.format(HATCH)
        sections.append('<span class="sec{}" style="flex:{} 1 0">{}<span class="says">{} '
                        '<em>{}</em></span></span>'.format(" picked" if selected else "", length,
                                                           lit, html.escape(name), length))

    stretches = len(sections)
    if kind == "strip":
        drawn = strip_drawing(strip_colours, ringed)
        zoom = ('<span class="round">&#8722;</span><span class="dim">100%</span>'
                '<span class="round">+</span>')
    else:
        drawn = "".join(lights)
        zoom = ""
    return ('<div class="run" style="flex:{} 1 0"><div class="lightbox {}">{}</div>'
            '<div class="cutrow"><span class="dim">Cut into {} stretch{}</span>{}'
            '<span class="round">{}</span><span class="round">{}</span></div>'
            '<div class="bar">{}</div></div>').format(
                len(strip_colours) or len(lights), "strip" if kind == "strip" else "lamps", drawn,
                stretches, "" if stretches == 1 else "es", zoom, UNDO_ICON, REDO_ICON,
                "".join(sections))


def mockup_tools(text):
    """The tools under a stretch bar, written as the number Split into offers and the number
    Repeat takes, "3, 2"."""
    counts = [count.strip() for count in text.split(",") if count.strip()] or ["3", "2"]
    split, repeat = (counts + ["2"])[:2]
    return ('<div class="tools"><span class="toolset"><span class="toolsays">&#9986; Split into'
            '<span class="field">{}</span></span><span class="toolact">stretches</span>'
            '<span class="toolact">lights each</span></span><span class="toolset off">'
            '<span class="toolsays">&#10231; Join all</span></span><span class="toolset">'
            '<span class="toolsays">&#8649; Repeat<span class="field">{}</span></span>'
            '<span class="toolact off">to the end</span></span></div>').format(split, repeat)


def mockup_settings(text):
    """The selected stretch's settings, written as its look, where it plays, then each setting
    and where its slider sits out of 100, "Rainbow, on outputs 1 to 7, Brightness 100, Speed 45".
    A colour, "colour yellow", draws the row of colours with that one chosen."""
    parts = [part.strip() for part in text.split(",")]
    look, where, settings = parts[0], parts[1], parts[2:]
    reverse = '<span class="button reverse{}">{} Reverse</span>'.format(
        " off" if look in NO_DIRECTION else "", REVERSE_ICON)
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
    return ('<div class="settings"><div class="sethead"><b>{}</b> <span class="dim">{}</span>{}</div>'
            '{}{}</div>').format(html.escape(look), html.escape(where), reverse, swatches, sliders)


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


def mockup_wiring(text, look):
    """The lights in build order above the board's connectors, written as their labels with a
    bar between groups drawn apart, "1, 2, 3, 4, 5, 6 | RGB". Lights after the first group are
    colour lights, and look colours them as the picker would show it playing."""
    groups = []
    connectors = []
    for at, group in enumerate(text.split("|")):
        labels = [label.strip() for label in group.split(",")]
        mono = look.startswith("mono ") and at == 0
        colours = look_colours(look[5:] if mono else look, len(labels), mono) if look else [None]
        colours = [colour or UNLIT_LED for colour in colours] * len(labels)
        groups.append('<span class="lampgroup">{}</span>'.format(
            "".join(lamp(colours[number], label) for number, label in enumerate(labels))))
        connectors.extend(labels)
    plugs = "".join('<span class="plug"><b>{}</b></span>'.format(html.escape(label))
                    for label in connectors)
    return ('<div class="lightbox wiring">{}</div><div class="connectors">{}</div>'
            '<div class="dim small">All lights are in wiring order. Hover over a light or connector '
            'to highlight its wire.</div>').format("".join(groups), plugs)


def mockup_strip_setup(text):
    """A strip's settings while the board is set up, written as its number of LEDs, and the
    strip's LEDs under them."""
    count = int(text.strip())
    return ('<div class="badgerow"><span class="badge strip">{}<b>Strip</b><span class="field">{}'
            '</span> LEDs <span class="field">GRB (most strips) &#9662;</span> &#215;</span></div>'
            '<div class="lightbox strip">{}</div>').format(
                CHIP_ICON, count, strip_drawing([None] * count, None))


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
            '{}{} &#9662;</span></span><span class="backlight"><span class="dim">backlight</span>'
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
    """The sounds on the drive, written as their names with Silence among them, the selected one
    marked with a *. Loop and Silence sit on one line above the sounds, as the picker has them."""
    cards = []
    silence = False
    for name, selected in selected_items(text):
        if name == "Silence":
            silence = selected
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
            '<i class="{}"></i>Silence</span></div><div class="galleryhead"><span class="fold">'
            '&#8963;</span>On the drive<span class="dim">your own sounds</span></div>'
            '<div class="sounds">{}</div>').format(" on" if looping else "",
                                                   " picked" if silence else "", HATCH,
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
            runs.append(mockup_run(kind, " ".join(rest), text))
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
            parts.append(mockup_tabs(text, rest == ["editing"]))
        elif kind == "badge":
            parts.append(mockup_badge(text, " ".join(rest)))
        elif kind == "tools":
            parts.append(mockup_tools(text))
        elif kind == "settings":
            parts.append(mockup_settings(text))
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
