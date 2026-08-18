#!/usr/bin/env python3
"""Turns a board's MANUAL.md into the HTML the FX drive carries.

Writes two files: MANUAL.html beside the source, for opening in a browser while
writing, and a frozen module holding the same text, which is what ships. The
module is committed and the HTML is not, so the generated page appears once.

The markdown accepted here is a deliberate subset, since this converter has one
input and no reason to grow: ATX headings, paragraphs, fenced code with an info
string, pipe tables, links, inline code and bold. A fence's info string reaches
the HTML as a class, which is how the checks find the lines that must parse.

    python3 tools/build_manual.py boards/PIMORONI_MIGHTYFX
"""

import argparse
import html
import os
import re
import sys

TEMPLATE_NAME = "manual_template.html"

# The generated module is read by fx_drive and written to the drive verbatim.
MODULE_HEADER = '''# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# Generated from manual/MANUAL.md. Edit that and rebuild; edits here are lost.

MANUAL = """\\
'''


def slug(text):
    """The anchor a heading gets, and what a link in the source points at."""
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def inline(text):
    """Inline markup, escaped first so the source cannot inject markup of its own."""
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)


def mark(role, text):
    return '<span class="{}">{}</span>'.format(role, text) if text else text


def setting(token):
    """A name=value pair, or a bare word where the line carries no value."""
    trailing = ""
    while token.endswith(","):
        token, trailing = token[:-1], token[-1:] + trailing
    name, divider, value = token.partition("=")
    if not divider:
        return mark("s-name", name) + trailing
    return mark("s-name", name) + mark("s-punc", "=") + mark("s-value", value) + trailing


def placeholders(text, roles):
    """Each <placeholder> marked by the position it stands in, spaces and all."""
    standing = [0]

    def taken(match):
        role = roles[min(standing[0], len(roles) - 1)]
        standing[0] += 1
        return mark(role, match.group(0))

    return re.sub(r"&lt;[^&]*&gt;", taken, text)


def highlight(line, shape=False):
    """An entry marked up by the part each word plays, over already-escaped text.

    Colour carries the same three roles the shape at the top of the manual names, so
    an example reads as an instance of it. A shape is positional, its placeholders
    standing where a selector, an effect and their settings go.
    """
    if line.lstrip().startswith("["):
        return mark("s-scene", line)

    before, divider, after = line.partition(":")
    if not divider:
        return line

    if shape:
        return (placeholders(before, ("s-target", "s-name"))
                + mark("s-colon", ":")
                + placeholders(after, ("s-effect", "s-name")))

    left = "".join(word if not word.strip()
                   else setting(word) if "=" in word
                   else mark("s-target", word)
                   for word in re.split(r"(\s+)", before))

    # The first word names the effect, unless it carries a value: a board entry is
    # settings the whole way and has no effect to name
    right = []
    named = False
    for word in re.split(r"(\s+)", after):
        if not word.strip():
            right.append(word)
        elif named or "=" in word:
            right.append(setting(word))
        else:
            right.append(mark("s-effect", word))
            named = True

    return left + mark("s-colon", ":") + "".join(right)


def cells(row):
    """A table row split on unescaped pipes, the escaped ones surviving as text."""
    parts = re.split(r"(?<!\\)\|", row.strip().strip("|"))
    return [part.replace("\\|", "|").strip() for part in parts]


def blocks(lines):
    """The source as (kind, payload) pairs, kind being what to render it as."""
    found = []
    index = 0
    while index < len(lines):
        line = lines[index]

        if not line.strip():
            index += 1
        elif line.startswith("```"):
            language = line[3:].strip()
            index += 1
            body = []
            while index < len(lines) and not lines[index].startswith("```"):
                body.append(lines[index])
                index += 1
            index += 1
            found.append(("code", (language, body)))
        elif line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            found.append(("heading", (level, line[level:].strip())))
            index += 1
        elif line.lstrip().startswith("|"):
            rows = []
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                rows.append(lines[index])
                index += 1
            found.append(("table", rows))
        elif line.startswith("- "):
            items = []
            while index < len(lines) and lines[index].startswith("- "):
                items.append(lines[index][2:].strip())
                index += 1
            found.append(("list", items))
        else:
            body = []
            while index < len(lines) and lines[index].strip() and not (
                    lines[index].startswith(("#", "```", "|", "- "))):
                body.append(lines[index].strip())
                index += 1
            found.append(("paragraph", " ".join(body)))

    return found


def render(found):
    """The page body, and the headings a contents list is built from."""
    out = []
    contents = []

    for kind, payload in found:
        if kind == "heading":
            level, text = payload
            anchor = slug(text)
            if level > 1:
                contents.append((level, anchor, text))
            out.append('<h{0} id="{1}">{2}</h{0}>'.format(level, anchor, inline(text)))

        elif kind == "paragraph":
            out.append("<p>{}</p>".format(inline(payload)))

        elif kind == "list":
            out.append("<ul>{}</ul>".format(
                "".join("<li>{}</li>".format(inline(item)) for item in payload)))

        elif kind == "code":
            language, body = payload
            escaped = [html.escape(line, quote=False) for line in body]
            if language in ("entry", "shape"):
                escaped = [highlight(line, language == "shape") for line in escaped]
            out.append('<pre class="{}"><code>{}</code></pre>'.format(
                language, "\n".join(escaped)))

        elif kind == "table":
            # Row two is the header separator, which carries nothing to render.
            header, _, *rest = payload
            out.append('<div class="scroll"><table>')
            out.append("<thead><tr>{}</tr></thead>".format(
                "".join("<th>{}</th>".format(inline(c)) for c in cells(header))))
            out.append("<tbody>")
            for row in rest:
                out.append("<tr>{}</tr>".format(
                    "".join("<td>{}</td>".format(inline(c)) for c in cells(row))))
            out.append("</tbody></table></div>")

    return "\n".join(out), contents


def table_of_contents(contents):
    """Sections, each folding its subsections away until asked for.

    A section with subsections becomes a details, so opening and closing needs no
    script. Its summary holds the section link, and following that link opens the
    section on the way past, which is what someone clicking a heading wants.
    """
    sections = []
    for level, anchor, text in contents:
        if level == 2 or not sections:
            sections.append((anchor, text, []))
        else:
            sections[-1][2].append((anchor, text))

    items = ['<nav class="contents"><h2>Contents</h2><ul>']
    for anchor, text, under in sections:
        link = '<a href="#{}">{}</a>'.format(anchor, inline(text))
        if not under:
            items.append("<li>{}</li>".format(link))
            continue
        items.append("<li><details><summary>{}</summary><ul>".format(link))
        for sub_anchor, sub_text in under:
            items.append('<li><a href="#{}">{}</a></li>'.format(
                sub_anchor, inline(sub_text)))
        items.append("</ul></details></li>")
    items.append("</ul></nav>")
    return "\n".join(items)


def build(board_dir, tools_dir):
    source = os.path.join(board_dir, "manual", "MANUAL.md")
    with open(source, encoding="utf-8") as f:
        lines = f.read().split("\n")

    found = blocks(lines)
    body, contents = render(found)

    title = next(text for kind, (level, text) in
                 ((k, p) for k, p in found if k == "heading") if level == 1)

    with open(os.path.join(tools_dir, TEMPLATE_NAME), encoding="utf-8") as f:
        template = f.read()

    page = template.replace("{{TITLE}}", html.escape(title, quote=False))
    page = page.replace("{{CONTENTS}}", table_of_contents(contents))
    page = page.replace("{{BODY}}", body)

    # The page is embedded in a triple-quoted Python string, so neither may appear.
    for forbidden in ('"""', "\\"):
        if forbidden in page:
            sys.exit("the page contains {!r}, which the frozen module cannot hold"
                     .format(forbidden))

    # fx_drive compares and writes the page a piece at a time, counting characters
    # against a file counting bytes, so one character has to be one byte.
    if not page.isascii():
        stray = sorted({c for c in page if not c.isascii()})
        sys.exit("the page contains {}, and it has to be ASCII to reach the drive "
                 "a piece at a time".format(", ".join(repr(c) for c in stray)))

    return page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board_dir", help="a board directory holding manual/MANUAL.md")
    args = parser.parse_args()

    tools_dir = os.path.dirname(os.path.abspath(__file__))
    page = build(args.board_dir, tools_dir)

    preview = os.path.join(args.board_dir, "manual", "MANUAL.html")
    with open(preview, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)

    module = os.path.join(args.board_dir, "frozen_libs", "fx_manual.py")
    with open(module, "w", encoding="utf-8", newline="\n") as f:
        f.write(MODULE_HEADER)
        f.write(page)
        f.write('"""\n')

    print("{} bytes of page: {} and {}".format(len(page), preview, module))


if __name__ == "__main__":
    main()
