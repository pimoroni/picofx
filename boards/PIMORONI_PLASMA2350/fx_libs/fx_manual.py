# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# Generated from manual/MANUAL.md. Edit that and rebuild; edits here are lost.

MANUAL = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Plasma 2350</title>
<style>
:root {
  /* Browser-painted furniture, scrollbars included, follows the page rather than
     defaulting to light. Without it a nested scroller does not match the page one. */
  color-scheme: light dark;

  --page: #ffffff;
  --panel: #f5f6f7;
  --ink: #22262b;
  --faint: #5d656e;
  --rule: #dfe3e7;
  --accent: #0a7f78;
  --code-ink: #1d4f5c;
  --entry: #0a7f78;

  /* Three roles, matching the shape at the top of the manual: what is being
     driven, what drives it, and the values given to either. */
  --target: #1f6feb;
  --effect: #0a7f78;
  --value: #a8500a;
  --scene: #7b3fb8;
}

@media (prefers-color-scheme: dark) {
  :root {
    --page: #16191d;
    --panel: #1e2227;
    --ink: #dfe3e7;
    --faint: #9aa3ad;
    --rule: #2e343b;
    --accent: #56cfc3;
    --code-ink: #8fd3e0;
    --entry: #56cfc3;

    --target: #79b8ff;
    --effect: #56cfc3;
    --value: #e8a05c;
    --scene: #c9a2f0;
  }
}

* { box-sizing: border-box; }

body {
  margin: 0;
  padding: 0;
  background: var(--page);
  color: var(--ink);
  font: 16px/1.62 system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.page {
  max-width: 68rem;
  margin: 0 auto;
  padding: 2rem 1.25rem 4rem;
  display: grid;
  gap: 2.5rem;
  grid-template-columns: 1fr;
}

@media (min-width: 62rem) {
  .page { grid-template-columns: 15rem 1fr; }
  /* The sidebar stretches to the row so the box inside it has somewhere to travel;
     a sticky element in a start-aligned grid item cannot move at all. */
  .contents {
    position: sticky;
    top: 2rem;
    max-height: calc(100vh - 4rem);
    overflow-y: auto;
  }
}

.contents {
  background: var(--panel);
  border: 1px solid var(--rule);
  border-radius: 0.5rem;
  padding: 1rem 1.1rem;
  font-size: 0.9rem;
}

.contents h2 {
  margin: 0 0 0.6rem;
  font-size: 0.75rem;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--faint);
  border: 0;
}

.contents ul { list-style: none; margin: 0; padding: 0; }
.contents li { margin: 0.18rem 0; }
.contents a { color: var(--ink); text-decoration: none; }
.contents a:hover { color: var(--accent); text-decoration: underline; }

.contents summary {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  cursor: pointer;
  list-style: none;
}

.contents summary::-webkit-details-marker { display: none; }

/* The triangle is drawn rather than a glyph, so it turns with the section. */
.contents summary::before {
  content: "";
  flex: none;
  width: 0;
  height: 0;
  border-left: 0.32rem solid var(--faint);
  border-top: 0.26rem solid transparent;
  border-bottom: 0.26rem solid transparent;
  transition: transform 0.12s ease;
}

.contents details[open] > summary::before { transform: rotate(90deg); }

.contents details > ul {
  margin: 0.15rem 0 0.4rem 0.95rem;
  font-size: 0.85rem;
}

main { min-width: 0; }

h1 {
  font-size: 2.1rem;
  line-height: 1.2;
  margin: 0 0 1rem;
}

h2 {
  font-size: 1.45rem;
  margin: 2.6rem 0 0.9rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--rule);
}

h3 {
  font-size: 1.1rem;
  margin: 1.9rem 0 0.7rem;
  color: var(--faint);
}

h1:target, h2:target, h3:target { scroll-margin-top: 1.5rem; }

p { margin: 0 0 1rem; }

a { color: var(--accent); }

code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.9em;
  color: var(--code-ink);
  background: var(--panel);
  border: 1px solid var(--rule);
  border-radius: 0.25rem;
  padding: 0.05rem 0.3rem;
}

pre {
  background: var(--panel);
  border: 1px solid var(--rule);
  border-left: 3px solid var(--rule);
  border-radius: 0.4rem;
  padding: 0.85rem 1rem;
  margin: 0 0 1.15rem;
  overflow-x: auto;
}

pre.entry { border-left-color: var(--entry); }

pre code {
  background: none;
  border: 0;
  padding: 0;
  color: inherit;
  font-size: 0.875rem;
  line-height: 1.55;
}

.s-target { color: var(--target); }
.s-effect { color: var(--effect); font-weight: 600; }
.s-value { color: var(--value); }
.s-scene { color: var(--scene); font-weight: 600; }
.s-name { color: var(--ink); }
.s-punc { color: var(--faint); }
/* The colon is the one division the format has, so it carries weight the '=' does not */
.s-colon { color: var(--ink); font-weight: 700; }

.scroll { overflow-x: auto; margin: 0 0 1.3rem; }

table {
  border-collapse: collapse;
  width: 100%;
  font-size: 0.94rem;
}

th, td {
  text-align: left;
  vertical-align: top;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--rule);
}

th {
  font-size: 0.75rem;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--faint);
  border-bottom-width: 2px;
}

tbody tr:last-child td { border-bottom: 0; }
td:first-child { white-space: nowrap; }

footer {
  grid-column: 1 / -1;
  margin-top: 1rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--rule);
  font-size: 0.92rem;
  color: var(--faint);
}

footer h2 {
  font-size: 0.75rem;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--faint);
  margin: 0 0 0.5rem;
  padding: 0;
  border: 0;
}

main ul { margin: 0 0 1.2rem; padding-left: 1.2rem; }
main li { margin: 0.25rem 0; }

footer p { margin: 0; }
</style>
</head>
<body>
<div class="page">

<div class="sidebar">
<nav class="contents"><h2>Contents</h2><ul>
<li><a href="#getting-started">Getting started</a></li>
<li><a href="#writing-an-entry">Writing an entry</a></li>
<li><a href="#led-strips">LED strips</a></li>
<li><a href="#the-board-s-led">The board's LED</a></li>
<li><a href="#the-screen">The screen</a></li>
<li><a href="#scenes">Scenes</a></li>
<li><a href="#the-board">The board</a></li>
<li><a href="#when-something-is-wrong">When something is wrong</a></li>
</ul></nav>
</div>

<main>
<h1 id="plasma-2350">Plasma 2350</h1>
<p>Two LED terminals, a screen connector, and a text file that drives them. Edit <code>effects.txt</code> on this drive, eject it, and the board applies the change straight away. No code needed, though there is room for it when you want it.</p>
<h2 id="getting-started">Getting started</h2>
<p>Edit <code>effects.txt</code> to change what the lights do, then eject this drive and the board applies the change straight away.</p>
<p>In a hurry? Save the file and press <strong>Boot</strong> once. The drive disappears and comes straight back with the new effects running, so you can keep editing. Ejecting is the surer way, since a computer does not always write the file out until then. Press <strong>Boot</strong> twice to hide the drive, and twice again to bring it back.</p>
<p>Deleting <code>effects.txt</code> restores the default; emptying it leaves the board dark.</p>
<p><strong>Would you rather not write the file at all? <code>PICKER.html</code> on this drive writes it for you.</strong> Open it in Chrome or Edge, point it at this drive, and choose what each strip plays. <code>EDITOR.html</code> beside it is a place to write the file with the names offered as you type.</p>
<h2 id="writing-an-entry">Writing an entry</h2>
<p>Each line names what to light, a colon, and the effect to play on it:</p>
<pre class="entry"><code><span class="s-target">stripDat</span><span class="s-colon">:</span> <span class="s-effect">rainbow_wave</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.3</span> <span class="s-name">length</span><span class="s-punc">=</span><span class="s-value">30</span></code></pre>
<p>Settings follow the effect as <code>name=value</code>. A line starting <code>#</code> is a note and is ignored. The board reads the whole file each time the drive goes away, so a mistake on one line is reported in <code>errors.txt</code> and the rest still plays.</p>
<h2 id="led-strips">LED strips</h2>
<p>The two screw terminals are marked <strong>DAT</strong> and <strong>CLK</strong>. A WS2812 strip needs only a data line, so one can go on each terminal: <code>stripDat</code> and <code>stripClk</code>. An APA102 strip needs both, data and clock, so it is the one strip on the board, <code>stripApa</code>.</p>
<p>A strip's length is declared on the board line:</p>
<pre class="entry"><code><span class="s-target">board</span><span class="s-colon">:</span> <span class="s-name">stripDat</span><span class="s-punc">=</span><span class="s-value">60</span> <span class="s-name">stripClk</span><span class="s-punc">=</span><span class="s-value">30</span>
<span class="s-target">board</span><span class="s-colon">:</span> <span class="s-name">stripApa</span><span class="s-punc">=</span><span class="s-value">144</span></code></pre>
<p>A strip's LEDs are named like outputs, so <code>stripDat1-10</code> is the first ten and the bare name is the whole run:</p>
<pre class="entry"><code><span class="s-target">stripDat1-30</span><span class="s-colon">:</span> <span class="s-effect">pulse_wave</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.5</span>
<span class="s-target">stripDat31-60</span> <span class="s-name">colour</span><span class="s-punc">=</span><span class="s-value">ff5a00</span><span class="s-colon">:</span> <span class="s-effect">flicker_each</span></code></pre>
<p>Most WS2812 strips take their colours as green, red, then blue, and the board sends them that way. If yours shows another colour where you asked for red, it takes them in another order: write the letters <code>r</code>, <code>g</code> and <code>b</code> after its length in the order it wants them, such as <code>stripDat=60|rgb</code>.</p>
<p>An APA102 strip has a brightness of its own for the whole strip, at 50% unless the board line says otherwise, such as <code>stripApa=144|75%</code>. The effects' own levels apply on top of it.</p>
<p><code>stripApa</code> and the WS2812 strips cannot play at once, since they use the same terminals. A file naming both plays the WS2812 strips and says so in <code>errors.txt</code>.</p>
<h2 id="the-board-s-led">The board's LED</h2>
<p>The RGB LED on the board is <code>rgb</code>, and takes any colour effect:</p>
<pre class="entry"><code><span class="s-target">rgb</span><span class="s-colon">:</span> <span class="s-effect">rainbow</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.3</span></code></pre>
<p>It also reports: it flashes when a reload fails, and holds a dim white while a computer is copying to the drive.</p>
<h2 id="the-screen">The screen</h2>
<p>A screen on the SP/CE connector is <code>screen</code>, and needs its size on the board line, since a panel cannot say what size it is:</p>
<pre class="entry"><code><span class="s-target">board</span><span class="s-colon">:</span> <span class="s-name">screen</span><span class="s-punc">=</span><span class="s-value">2.8</span>
<span class="s-target">screen</span><span class="s-colon">:</span> <span class="s-effect">image</span> <span class="s-name">file</span><span class="s-punc">=</span><span class="s-value">"picture.png"</span></code></pre>
<p>The Plasma 2350 W has no SP/CE connector, so it takes no screen, and the picker offers none.</p>
<p>Pictures and animations go on this drive beside <code>effects.txt</code>. <code>gif</code> plays an animation, <code>image</code> shows a still, and <code>sequence</code> plays a folder of them in turn.</p>
<p>The panel is mounted upright, 240 wide by 320 tall, so a landscape picture is cropped at its sides unless the line turns it: <code>screen rotation=90: image file="picture.png"</code>.</p>
<p><strong>A limit for now.</strong> The board's memory is small, and what the last file showed can keep its room until a restart. Saving a change from one full-size picture to another is refused with a note in <code>errors.txt</code>; turn the board off and on with the new file saved and it plays. Animations under about 60KB of frames, small pictures, and drawings with <code>pixel_double=true</code> change over without a restart. The lights are never affected.</p>
<h2 id="scenes">Scenes</h2>
<p>A heading starts a scene, and scenes take turns for the time each names. Everything above the first heading stays on throughout:</p>
<pre class="entry"><code><span class="s-target">rgb</span><span class="s-colon">:</span> <span class="s-effect">static</span> <span class="s-name">colour</span><span class="s-punc">=</span><span class="s-value">white</span> <span class="s-name">brightness</span><span class="s-punc">=</span><span class="s-value">0.2</span>

## Daytime 30s
<span class="s-target">stripDat</span><span class="s-colon">:</span> <span class="s-effect">rainbow_wave</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.3</span>

## Night 2m
<span class="s-target">stripDat</span> <span class="s-name">colour</span><span class="s-punc">=</span><span class="s-value">ff5a00</span><span class="s-colon">:</span> <span class="s-effect">flicker_each</span></code></pre>
<h2 id="the-board">The board</h2>
<p>The board line holds what is the same in every scene: each strip's length, and its colour order or brightness, the screen's size, and how the drive behaves. <code>reload=auto</code> applies a saved file without an eject, and <code>drive=manual</code> keeps the drive hidden until <strong>Boot</strong> is pressed twice. <code>program=</code> runs a Python file from this drive in place of the effects.</p>
<h2 id="when-something-is-wrong">When something is wrong</h2>
<p>The board's LED says so, and the more flashes the worse it is: white once means the computer was still writing, so press again in a moment; blue twice means a line could not be read, and <code>errors.txt</code> says which; red three times means there was no room to write <code>errors.txt</code>, so free some space on the drive.</p>
</main>

<footer>
<p>This manual is rebuilt by the board, so edits to it will not stick.</p>
</footer>

</div>
</body>
</html>
"""
