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
<title>MightyFX</title>
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
<li><a href="#the-picker">The picker</a></li>
<li><a href="#writing-an-entry">Writing an entry</a></li>
<li><details><summary><a href="#outputs">Outputs</a></summary><ul>
<li><a href="#naming-outputs">Naming outputs</a></li>
<li><a href="#setting-an-output">Setting an output</a></li>
<li><a href="#fade-and-ease">Fade and ease</a></li>
</ul></details></li>
<li><details><summary><a href="#effects">Effects</a></summary><ul>
<li><a href="#for-an-output-or-for-one-of-its-red-green-and-blue">For an output, or for one of its red, green and blue</a></li>
<li><a href="#for-an-output-only-since-these-bring-their-own-colour">For an output only, since these bring their own colour</a></li>
<li><a href="#which-ones-travel">Which ones travel</a></li>
<li><a href="#traffic-lights-and-crossings">Traffic lights and crossings</a></li>
<li><a href="#sweep">Sweep</a></li>
<li><a href="#blinking-through-colours">Blinking through colours</a></li>
<li><a href="#what-the-settings-mean">What the settings mean</a></li>
</ul></details></li>
<li><a href="#led-strips">LED strips</a></li>
<li><details><summary><a href="#screens">Screens</a></summary><ul>
<li><a href="#naming-screens">Naming screens</a></li>
<li><a href="#setting-a-screen">Setting a screen</a></li>
<li><a href="#pictures">Pictures</a></li>
</ul></details></li>
<li><a href="#sound">Sound</a></li>
<li><a href="#scenes">Scenes</a></li>
<li><details><summary><a href="#the-board">The board</a></summary><ul>
<li><a href="#running-your-own-program">Running your own program</a></li>
<li><a href="#what-is-already-on-the-board">What is already on the board</a></li>
</ul></details></li>
<li><a href="#when-something-is-wrong">When something is wrong</a></li>
<li><details><summary><a href="#more-from-pimoroni">More from Pimoroni</a></summary><ul>
<li><a href="#boards-and-accessories">Boards and accessories</a></li>
<li><a href="#going-further">Going further</a></li>
</ul></details></li>
</ul></nav>
</div>

<main>
<h1 id="mightyfx">MightyFX</h1>
<p>Seven outputs, two screen connectors, and a text file that drives them. Edit <code>effects.txt</code> on this drive, eject it, and the board applies the change straight away. No code needed, though there is room for it when you want it.</p>
<h2 id="getting-started">Getting started</h2>
<p>Edit <code>effects.txt</code> to change what the lights do, then eject this drive and the board applies the change straight away.</p>
<p>In a hurry? Save the file and press <strong>Boot</strong> once. The drive disappears and comes straight back with the new effects running, so you can keep editing. Ejecting is the surer way, since a computer does not always write the file out until then. Press <strong>Boot</strong> twice to hide the drive, and twice again to bring it back. A dim white light runs along the outputs each time, towards the USB connector as the computer takes the drive and away from it as the board takes it back, so a double press is never mistaken for a single one.</p>
<p>Deleting <code>effects.txt</code> restores the default; emptying it leaves the board dark.</p>
<p>While the computer is copying to this drive the effects stand aside for a dim white travelling along the outputs, and come back a moment after it finishes.</p>
<p><strong>Would you rather not write the file at all? <code>PICKER.html</code> on this drive writes it for you. See <a href="#the-picker">the picker</a>.</strong></p>
<p><strong>The board also carries programs that run as they are, from single effects to whole builds, and one line in <code>effects.txt</code> starts any of them. See <a href="#what-is-already-on-the-board">what is already on the board</a>.</strong></p>
<h2 id="the-picker">The picker</h2>
<p><code>PICKER.html</code> on this drive writes <code>effects.txt</code> for you. Open it in Chrome or Edge, pick a look, and slide until it suits. It shows the file it is writing as you go, so nothing about it is hidden.</p>
<p>Screens and strips are set up there too. Say how many LEDs a strip has and which size each screen is, pick a picture from this drive for a screen to show, and turn the board's own seven lights off where the screens are all you want.</p>
<p>"Put it on the board" writes the file. Eject this drive, or press <strong>Boot</strong> once, and the board plays it. "Did it work?" reads <code>errors.txt</code> back and shows what the board made of each line.</p>
<p>A page cannot write to a drive in Firefox or Safari, so the picker needs Chrome or Edge. What it writes is an ordinary <code>effects.txt</code>: anything it makes can be edited by hand afterwards, and it asks before replacing a file it did not write itself.</p>
<h2 id="writing-an-entry">Writing an entry</h2>
<pre class="shape"><code><span class="s-target">&lt;outputs&gt;</span> <span class="s-name">&lt;their settings&gt;</span><span class="s-colon">:</span> <span class="s-effect">&lt;effect&gt;</span> <span class="s-name">&lt;its settings&gt;</span></code></pre>
<pre class="entry"><code><span class="s-target">out1-7</span><span class="s-colon">:</span> <span class="s-effect">rainbow_wave</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.3</span>
<span class="s-target">out3</span> <span class="s-name">level</span><span class="s-punc">=</span><span class="s-value">50%</span><span class="s-colon">:</span> <span class="s-effect">pulse</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.6</span></code></pre>
<p>There is one colon in an entry. Which outputs, and how bright or what colour they are, go before it. The effect and its own settings go after.</p>
<p>Settings you leave out take their usual value. A <code>#</code> starts a comment. An entry can run on over several lines so long as the colon is on the first; indenting changes nothing.</p>
<p>A screen is named the same way and plays pictures instead of lighting up. See <a href="#screens">Screens</a>.</p>
<h2 id="outputs">Outputs</h2>
<h3 id="naming-outputs">Naming outputs</h3>
<div class="scroll"><table>
<thead><tr><th>Written</th><th>Means</th></tr></thead>
<tbody>
<tr><td><code>out1</code></td><td>one output</td></tr>
<tr><td><code>out1,3,5</code></td><td>three of them</td></tr>
<tr><td><code>out1-7</code></td><td>all seven</td></tr>
<tr><td><code>out7-1</code></td><td>all seven, the other way round</td></tr>
<tr><td><code>out2,1,5-7</code></td><td>mixed, and in the order you write them</td></tr>
</tbody></table></div>
<p>An output shows colour. Its red, green and blue can be driven separately as three plain lights instead:</p>
<div class="scroll"><table>
<thead><tr><th>Written</th><th>Means</th></tr></thead>
<tbody>
<tr><td><code>out3.r</code></td><td>just the red</td></tr>
<tr><td><code>out3.*</code></td><td>all three of them</td></tr>
<tr><td><code>out1-7.*</code></td><td>all 21</td></tr>
</tbody></table></div>
<p>Order matters for the effects that travel: they move in the order you write the outputs, so list them in the order they appear in your model, which need not be number order.</p>
<h3 id="setting-an-output">Setting an output</h3>
<p>Before the colon, and separate from the effect:</p>
<div class="scroll"><table>
<thead><tr><th>Setting</th><th>What it does</th><th>If omitted</th></tr></thead>
<tbody>
<tr><td><code>level</code></td><td>how bright, 0 to 1, such as 0.5 or 50%</td><td>1</td></tr>
<tr><td><code>colour</code></td><td>a name or six-digit hex, for effects that bring no colour</td><td>white</td></tr>
<tr><td><code>fade</code></td><td>seconds to follow the effect, at a steady rate</td><td>follows at once</td></tr>
<tr><td><code>ease</code></td><td>seconds to follow it, settling in as a bulb does</td><td>follows at once</td></tr>
</tbody></table></div>
<pre class="entry"><code><span class="s-target">out1-7</span> <span class="s-name">level</span><span class="s-punc">=</span><span class="s-value">50%</span><span class="s-colon">:</span> <span class="s-effect">pulse</span>
<span class="s-target">out1-3</span> <span class="s-name">colour</span><span class="s-punc">=</span><span class="s-value">warm</span><span class="s-colon">:</span> <span class="s-effect">flicker</span>
<span class="s-target">out4</span> <span class="s-name">colour</span><span class="s-punc">=</span><span class="s-value">ff8040</span><span class="s-colon">:</span> <span class="s-effect">static</span>
<span class="s-target">out1</span> <span class="s-name">level</span><span class="s-punc">=</span><span class="s-value">0.5</span>, <span class="s-target">2</span> <span class="s-name">level</span><span class="s-punc">=</span><span class="s-value">0.8</span>, <span class="s-target">3-7</span><span class="s-colon">:</span> <span class="s-effect">pulse_wave</span>
<span class="s-target">out1-7</span> <span class="s-name">ease</span><span class="s-punc">=</span><span class="s-value">0.4</span><span class="s-colon">:</span> <span class="s-effect">blink</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.5</span></code></pre>
<p>Colours by name: red, yellow, green, cyan, blue, magenta, warm, white, cool, black. Or the hex a colour picker gives you, with its <code>#</code> left off, as <code>out4</code> above uses for a soft orange. A <code>#</code> always starts a comment, so one left on a colour hides the rest of the line.</p>
<h3 id="fade-and-ease">Fade and ease</h3>
<p><code>fade</code> and <code>ease</code> take the seconds a change takes to get there. <code>fade</code> crosses evenly, which is what a stage light does; <code>ease</code> goes quickly at first and slows as it arrives, which is how a bulb warms and is the one that looks natural on a light switching on and off.</p>
<p>An output follows one way or the other, so a line takes one of them and not both. Two numbers divided by <code>|</code> give the rise and the fall their own lengths, a light that comes on quickly and fades out slowly being the usual reason:</p>
<pre class="entry"><code><span class="s-target">out1-7</span> <span class="s-name">fade</span><span class="s-punc">=</span><span class="s-value">0.8</span><span class="s-colon">:</span> <span class="s-effect">blink</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.5</span>
<span class="s-target">out1-3</span> <span class="s-name">ease</span><span class="s-punc">=</span><span class="s-value">0.05|1.2</span><span class="s-colon">:</span> <span class="s-effect">blink</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">1</span></code></pre>
<p>Softening belongs to the output, not to the effect, so it works on any effect.</p>
<h2 id="effects">Effects</h2>
<p>Every setting can be left out, and the board fills in the value shown against it below. The few with none shown have nothing to fall back on, and each is covered where its effect is.</p>
<h3 id="for-an-output-or-for-one-of-its-red-green-and-blue">For an output, or for one of its red, green and blue</h3>
<div class="scroll"><table>
<thead><tr><th>Effect</th><th>Settings</th></tr></thead>
<tbody>
<tr><td><code>none</code></td><td></td></tr>
<tr><td><code>static</code></td><td><code>brightness=1</code></td></tr>
<tr><td><code>blink</code></td><td><code>speed=1</code> <code>phase=0</code> <code>duty=0.5</code></td></tr>
<tr><td><code>blink_wave</code></td><td><code>speed=1</code> <code>length=1</code> <code>phase=0</code> <code>duty=0.5</code></td></tr>
<tr><td><code>flash</code></td><td><code>speed=1</code> <code>flashes=2</code> <code>window=0.5</code> <code>phase=0</code> <code>duty=0.5</code></td></tr>
<tr><td><code>flash_sequence</code></td><td><code>speed=1</code> <code>length=1</code> <code>flashes=1</code> <code>window=1</code> <code>phase=0</code> <code>duty=0.5</code></td></tr>
<tr><td><code>flicker</code></td><td><code>brightness=1</code> <code>dimness=0.5</code> <code>bright_min=0.05</code> <code>bright_max=0.1</code> <code>dim_min=0.02</code> <code>dim_max=0.04</code></td></tr>
<tr><td><code>pulse</code></td><td><code>speed=1</code> <code>phase=0</code></td></tr>
<tr><td><code>pulse_wave</code></td><td><code>speed=1</code> <code>length=1</code> <code>phase=0</code></td></tr>
<tr><td><code>sweep</code></td><td><code>speed=1</code> <code>length=1</code> <code>extent=1</code> <code>hold=0</code></td></tr>
<tr><td><code>random</code></td><td><code>interval=0.05</code> <code>brightness_min=0</code> <code>brightness_max=1</code></td></tr>
<tr><td><code>binary_counter</code></td><td><code>interval=0.1</code> <code>count=0</code> <code>step=1</code></td></tr>
<tr><td><code>traffic_light</code></td><td><code>red_interval=10</code> <code>red_amber_interval=5</code> <code>green_interval=10</code> <code>amber_interval=5</code></td></tr>
<tr><td><code>pelican_crossing</code></td><td><code>red_interval=8</code> <code>flashing_interval=6</code> <code>green_interval=20</code> <code>amber_interval=3</code></td></tr>
</tbody></table></div>
<h3 id="for-an-output-only-since-these-bring-their-own-colour">For an output only, since these bring their own colour</h3>
<div class="scroll"><table>
<thead><tr><th>Effect</th><th>Settings</th></tr></thead>
<tbody>
<tr><td><code>rgb</code></td><td><code>red=255</code> <code>green=255</code> <code>blue=255</code></td></tr>
<tr><td><code>hsv</code></td><td><code>hue=0</code> <code>sat=1</code> <code>val=1</code></td></tr>
<tr><td><code>rainbow</code></td><td><code>speed=1</code> <code>sat=1</code> <code>val=1</code></td></tr>
<tr><td><code>rainbow_wave</code></td><td><code>speed=1</code> <code>length=1</code> <code>sat=1</code> <code>val=1</code></td></tr>
<tr><td><code>hue_step</code></td><td><code>interval=1</code> <code>hue=0</code> <code>sat=1</code> <code>val=1</code> <code>steps=6</code></td></tr>
<tr><td><code>rgb_blink</code></td><td><code>colour</code> <code>speed=1</code> <code>phase=0</code> <code>duty=0.5</code></td></tr>
</tbody></table></div>
<h3 id="which-ones-travel">Which ones travel</h3>
<p>The ones ending <code>_wave</code>, <code>_sequence</code> and <code>_counter</code>, and <code>sweep</code>, travel across the outputs you name; the rest do the same thing on every one.</p>
<p>An effect that drives several outputs takes them in the order given in its own section below, so naming fewer than it drives lights the first of them and leaves the rest out. Naming more than it drives is a mistake, and <code>errors.txt</code> says so.</p>
<h3 id="traffic-lights-and-crossings">Traffic lights and crossings</h3>
<p><code>traffic_light</code> wants three outputs, and lights them red, amber and green in that order. It switches instantly, so add <code>ease</code> for the lamps of a real signal:</p>
<pre class="entry"><code><span class="s-target">out1-3</span> <span class="s-name">ease</span><span class="s-punc">=</span><span class="s-value">0.3</span><span class="s-colon">:</span> <span class="s-effect">traffic_light</span></code></pre>
<p><code>pelican_crossing</code> wants five outputs: the same three, then the two figures a pedestrian reads, stop and walk. In place of red and amber it flashes the amber and the walking figure together, as a pelican does while a crossing ends. It comes round on its own clock, there being no button to press:</p>
<pre class="entry"><code><span class="s-target">out1-5</span> <span class="s-name">ease</span><span class="s-punc">=</span><span class="s-value">0.3</span><span class="s-colon">:</span> <span class="s-effect">pelican_crossing</span> <span class="s-name">green_interval</span><span class="s-punc">=</span><span class="s-value">20</span> <span class="s-name">red_interval</span><span class="s-punc">=</span><span class="s-value">8</span></code></pre>
<p>Three outputs on <code>pelican_crossing</code> is its traffic lights on their own:</p>
<pre class="entry"><code><span class="s-target">out1-3</span><span class="s-colon">:</span> <span class="s-effect">pelican_crossing</span></code></pre>
<h3 id="sweep">Sweep</h3>
<p><code>sweep</code> is a light that crosses the outputs and turns back at each end, the back and forth a scanner does. Its <code>extent</code> is how far it reaches from itself, in outputs, and its <code>speed</code> counts one crossing as the travelling effects count one pass. Its <code>hold</code> waits at each end, in seconds, giving a trail time to clear before the light comes back over it:</p>
<pre class="entry"><code><span class="s-target">out1-7</span> <span class="s-name">ease</span><span class="s-punc">=</span><span class="s-value">0.4</span><span class="s-colon">:</span> <span class="s-effect">sweep</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">1</span> <span class="s-name">length</span><span class="s-punc">=</span><span class="s-value">7</span> <span class="s-name">extent</span><span class="s-punc">=</span><span class="s-value">1</span> <span class="s-name">hold</span><span class="s-punc">=</span><span class="s-value">1</span></code></pre>
<p>Give <code>extent</code> a whole number of outputs, such as 1 or 2. In between it dims as the light passes between two outputs and brightens as it lands on one, which reads as stepping. 1 is the tightest that travels smoothly.</p>
<h3 id="blinking-through-colours">Blinking through colours</h3>
<p><code>rgb_blink</code> takes one colour, or several to blink through in turn, divided by <code>|</code> since a comma would mean one colour for each output. It has no colour of its own, so give it at least one:</p>
<pre class="entry"><code><span class="s-target">out1</span><span class="s-colon">:</span> <span class="s-effect">rgb_blink</span> <span class="s-name">colour</span><span class="s-punc">=</span><span class="s-value">red|warm|ff8040</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.5</span></code></pre>
<h3 id="what-the-settings-mean">What the settings mean</h3>
<p><code>speed</code> is cycles a second: 1 goes round once a second, 0.5 once every two, 2 twice a second. A negative speed runs the cycle backwards.</p>
<p>The settings measured in seconds are <code>interval</code>, <code>hold</code>, flicker's <code>bright_min</code>, <code>bright_max</code>, <code>dim_min</code> and <code>dim_max</code>, and the four intervals <code>traffic_light</code> and <code>pelican_crossing</code> each take. <code>length</code>, <code>flashes</code>, <code>steps</code>, <code>count</code> and <code>step</code> are plain counts, and a negative <code>step</code> counts down.</p>
<p>The rest run from 0 to 1, written 0.5 or 50% as you prefer. <code>window</code> is one of them, being the share of a cycle the flashes happen in. <code>hue</code> takes degrees as well, written 180deg, which is what a colour picker gives you.</p>
<p><strong>If you write Python</strong>, an effect of your own can join this list and be written here like any other. The library reference on <a href="https://github.com/pimoroni/picofx/blob/main/picofx/README.md">GitHub</a> says how, under Effects System.</p>
<h2 id="led-strips">LED strips</h2>
<p>A strip of WS2812 LEDs plugs into the connector marked <strong>L</strong> or <strong>R</strong>, and its LEDs take the same effects, colours and levels the outputs do. Tell the board how long it is first, since that is the one thing it cannot work out for itself:</p>
<pre class="entry"><code><span class="s-target">board</span><span class="s-colon">:</span> <span class="s-name">stripL</span><span class="s-punc">=</span><span class="s-value">60</span>
<span class="s-target">stripL</span><span class="s-colon">:</span> <span class="s-effect">rainbow_wave</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.3</span></code></pre>
<div class="scroll"><table>
<thead><tr><th>Written</th><th>Means</th></tr></thead>
<tbody>
<tr><td><code>stripL</code></td><td>every LED on the strip</td></tr>
<tr><td><code>stripL5</code></td><td>one of them</td></tr>
<tr><td><code>stripL1-10</code></td><td>the first ten</td></tr>
<tr><td><code>stripL60-1</code></td><td>all sixty, the other way round, for a strip mounted backwards</td></tr>
</tbody></table></div>
<p><code>stripR</code> is the same for the other connector. Both share one power supply, so a strip on either lights the small LED between them, and anything plugged into the one you are not using is powered too.</p>
<p>Each LED shows a colour of its own, so <code>stripL5.r</code> is not a thing to write; set <code>colour</code> on the LEDs instead, as an output takes it.</p>
<h2 id="screens">Screens</h2>
<h3 id="naming-screens">Naming screens</h3>
<p>A screen on either SP/CE connector is named <code>screenA</code> or <code>screenB</code>. A screen cannot say what size it is, so tell the board:</p>
<pre class="entry"><code><span class="s-target">board</span><span class="s-colon">:</span> <span class="s-name">screenA</span><span class="s-punc">=</span><span class="s-value">1.54</span></code></pre>
<p>That is a board entry, which sets the board rather than the lights and is one of a handful covered under <a href="#the-board">The board</a>.</p>
<p>The sizes are 2.8 and 1.54, and 2.8 is used if you say nothing. Changing it needs the board turned off and on again before the new size takes.</p>
<h3 id="setting-a-screen">Setting a screen</h3>
<p>Before the colon, and separate from what it plays:</p>
<div class="scroll"><table>
<thead><tr><th>Setting</th><th>What it does</th><th>If omitted</th></tr></thead>
<tbody>
<tr><td><code>rotation</code></td><td>0, 90, 180 or 270, for how the screen is mounted</td><td>0</td></tr>
<tr><td><code>backlight</code></td><td>how brightly it is lit, 0 to 1, such as 0.5 or 50%</td><td>1</td></tr>
<tr><td><code>mirror</code></td><td>true to flip the picture left to right</td><td>no</td></tr>
<tr><td><code>offset</code></td><td>where to put the picture, as <code>x|y</code></td><td>centred</td></tr>
<tr><td><code>background</code></td><td>the colour around it, or <code>bg</code> for short</td><td>black</td></tr>
<tr><td><code>pixel_double</code></td><td>true to draw each pixel twice as wide and tall, so a half size picture fills the screen</td><td>no</td></tr>
<tr><td><code>tile</code></td><td><code>repeat</code> or <code>mirror</code> to fill the screen with copies of the picture, as <code>across|down</code></td><td>off</td></tr>
</tbody></table></div>
<pre class="entry"><code><span class="s-target">screenA</span> <span class="s-name">rotation</span><span class="s-punc">=</span><span class="s-value">90</span><span class="s-colon">:</span> <span class="s-effect">gif</span> <span class="s-name">file</span><span class="s-punc">=</span><span class="s-value">"clock.gif"</span>
<span class="s-target">screenA</span> <span class="s-name">offset</span><span class="s-punc">=</span><span class="s-value">*|20</span> <span class="s-name">bg</span><span class="s-punc">=</span><span class="s-value">black</span><span class="s-colon">:</span> <span class="s-effect">image</span> <span class="s-name">file</span><span class="s-punc">=</span><span class="s-value">logo.png</span>
<span class="s-target">screenA</span> <span class="s-name">tile</span><span class="s-punc">=</span><span class="s-value">repeat</span><span class="s-colon">:</span> <span class="s-effect">image</span> <span class="s-name">file</span><span class="s-punc">=</span><span class="s-value">bricks.png</span></code></pre>
<p>A picture is centred unless <code>offset</code> puts it somewhere, and a <code>*</code> in place of either number centres that side.</p>
<p><code>tile</code> fills the screen with a small picture instead of leaving a background around it. <code>repeat</code> lays copies side by side, so a picture drawn to join up at its edges makes a pattern with no seam in it, and <code>mirror</code> turns every other copy round, which joins any picture up whether it was drawn to or not. One value covers both directions and two set them apart, <code>tile=mirror|off</code> spreading a picture across the screen and leaving its height alone.</p>
<h3 id="pictures">Pictures</h3>
<div class="scroll"><table>
<thead><tr><th>Plays</th><th>Settings</th></tr></thead>
<tbody>
<tr><td><code>gif</code></td><td><code>file</code> <code>fps</code> <code>interval</code> <code>loop=yes</code> <code>ping_pong=no</code> <code>first_as_last=no</code> <code>hold=0</code></td></tr>
<tr><td><code>image</code></td><td><code>file</code></td></tr>
<tr><td><code>sequence</code></td><td><code>folder</code> <code>fps</code> <code>interval</code> <code>loop=yes</code> <code>ping_pong=no</code> <code>first_as_last=no</code> <code>hold=0</code></td></tr>
</tbody></table></div>
<pre class="entry"><code><span class="s-target">screenA</span><span class="s-colon">:</span> <span class="s-effect">gif</span> <span class="s-name">file</span><span class="s-punc">=</span><span class="s-value">"clock.gif"</span>
<span class="s-target">screenA</span><span class="s-colon">:</span> <span class="s-effect">image</span> <span class="s-name">file</span><span class="s-punc">=</span><span class="s-value">logo.png</span>
<span class="s-target">screenA</span><span class="s-colon">:</span> <span class="s-effect">sequence</span> <span class="s-name">folder</span><span class="s-punc">=</span><span class="s-value">photos</span> <span class="s-name">interval</span><span class="s-punc">=</span><span class="s-value">30</span></code></pre>
<p><code>gif</code> plays an animated GIF at the delays it was saved with, <code>image</code> holds one picture, and <code>sequence</code> plays a folder of them in the order their names number them. Pictures can be PNG, JPEG or GIF. There is nothing to play without <code>file</code> or <code>folder</code>, so those two always have to be given.</p>
<p><code>fps</code> is frames a second and <code>interval</code> is the seconds between them, so use whichever suits: <code>fps=12</code> for an animation, <code>interval=30</code> for a slideshow. Either one replaces the delays the file was saved with, and leaving out both keeps them. <code>loop</code> is true unless you set it false, which stops on the last frame. <code>ping_pong</code> plays back and forth instead of starting over, which suits an animation with two ends, such as an arm flexing.</p>
<p>An animation drawn to loop has no such ends, its last frame leading back into its first. Add <code>first_as_last=yes</code> for one of those and the whole loop is played in each direction, so a spinning coin winds all the way round and back:</p>
<pre class="entry"><code><span class="s-target">screenA</span><span class="s-colon">:</span> <span class="s-effect">gif</span> <span class="s-name">file</span><span class="s-punc">=</span><span class="s-value">"coin.gif"</span> <span class="s-name">ping_pong</span><span class="s-punc">=</span><span class="s-value">yes</span> <span class="s-name">first_as_last</span><span class="s-punc">=</span><span class="s-value">yes</span></code></pre>
<p><code>hold</code> is the seconds to wait where it turns around, so a ping-pong pauses at each end instead of bouncing straight off. One value serves both ends, or write each with a <code>|</code>:</p>
<pre class="entry"><code><span class="s-target">screenA</span><span class="s-colon">:</span> <span class="s-effect">gif</span> <span class="s-name">file</span><span class="s-punc">=</span><span class="s-value">"wave.gif"</span> <span class="s-name">ping_pong</span><span class="s-punc">=</span><span class="s-value">yes</span> <span class="s-name">hold</span><span class="s-punc">=</span><span class="s-value">1</span>
<span class="s-target">screenA</span><span class="s-colon">:</span> <span class="s-effect">gif</span> <span class="s-name">file</span><span class="s-punc">=</span><span class="s-value">"wave.gif"</span> <span class="s-name">ping_pong</span><span class="s-punc">=</span><span class="s-value">yes</span> <span class="s-name">hold</span><span class="s-punc">=</span><span class="s-value">1.5|0.5</span></code></pre>
<p>A file is looked for on this drive first, then on the board itself, and the name may include folders. There is little room here, so pictures usually live on the board.</p>
<p>A screen draws about twenty frames a second at best, and effects on the outputs take time from it, so a file asking for more keeps its timing by dropping frames. Ask for twenty or fewer and it plays every one.</p>
<h2 id="sound">Sound</h2>
<p>The board plays a WAV file through its onboard amplifier, alongside whatever the lights and screens are doing:</p>
<pre class="entry"><code><span class="s-target">audio</span><span class="s-colon">:</span> <span class="s-effect">wav</span> <span class="s-name">file</span><span class="s-punc">=</span><span class="s-value">chimes.wav</span>
<span class="s-target">audio</span><span class="s-colon">:</span> <span class="s-effect">wav</span> <span class="s-name">file</span><span class="s-punc">=</span><span class="s-value">ambience.wav</span> <span class="s-name">loop</span><span class="s-punc">=</span><span class="s-value">yes</span></code></pre>
<div class="scroll"><table>
<thead><tr><th>Plays</th><th>Settings</th></tr></thead>
<tbody>
<tr><td><code>wav</code></td><td><code>file</code> <code>loop=no</code></td></tr>
</tbody></table></div>
<p>The file plays once as the board starts, or over and over with <code>loop</code>. The board plays one sound at a time, so it takes the first <code>audio</code> entry and notes the rest in <code>errors.txt</code>.</p>
<p>A file is looked for on this drive first, then on the board itself, as a picture is. The board opens it before this drive is shown, so a computer taking the drive does not stop the sound. While the computer is copying to this drive the sound waits in silence with the effects, and a file replaced under a playing sound ends it quietly.</p>
<p>An ordinary uncompressed WAV plays, mono or stereo; MP3 does not. An <code>audio</code> entry sits before any scene heading, since sound does not follow scenes yet.</p>
<h2 id="scenes">Scenes</h2>
<p>A file can hold several sets of effects and show them one after another. A heading in square brackets begins one, and says how long it shows for:</p>
<pre class="entry"><code><span class="s-scene">[Evening: 30s]</span>
<span class="s-target">out1-7</span><span class="s-colon">:</span> <span class="s-effect">rainbow_wave</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.3</span>

<span class="s-scene">[Night: 10s]</span>
<span class="s-target">out1-7</span> <span class="s-name">colour</span><span class="s-punc">=</span><span class="s-value">warm</span><span class="s-colon">:</span> <span class="s-effect">pulse</span></code></pre>
<p>The name is everything before the <code>:</code> and may be anything you like, spaces included. Scenes take turns in the order they are written, then start again.</p>
<p>Entries before the first heading are always on, whatever is showing, so anything that should never change goes there:</p>
<pre class="entry"><code><span class="s-target">out1</span><span class="s-colon">:</span> <span class="s-effect">static</span> <span class="s-name">brightness</span><span class="s-punc">=</span><span class="s-value">0.2</span></code></pre>
<p>While a scene shows, an output it does not name goes dark if any other scene uses it, and is left alone if none of them do. A scene may name an output that is always on, and takes it over for as long as it shows.</p>
<p>A screen behaves the same way: its picture stays put but the light goes out while another scene has the board, and comes back when its own returns.</p>
<p>Add <code>restart</code> to a heading and its effects begin again every time it comes round, instead of carrying on from where they were left:</p>
<pre class="entry"><code><span class="s-scene">[Beacon: 5s restart]</span>
<span class="s-target">out1-3</span><span class="s-colon">:</span> <span class="s-effect">flash_sequence</span> <span class="s-name">flashes</span><span class="s-punc">=</span><span class="s-value">3</span></code></pre>
<p>The board entry belongs outside every scene. A single scene with no time simply shows for ever, and ejecting this drive always starts again at the first scene.</p>
<h2 id="the-board">The board</h2>
<p>One entry sets the board rather than the lights, and names no output:</p>
<pre class="entry"><code><span class="s-target">board</span><span class="s-colon">:</span> <span class="s-name">drive</span><span class="s-punc">=</span><span class="s-value">manual</span> <span class="s-name">program</span><span class="s-punc">=</span><span class="s-value">fireplace.py</span></code></pre>
<div class="scroll"><table>
<thead><tr><th>Setting</th><th>What it does</th><th>If omitted</th></tr></thead>
<tbody>
<tr><td><code>drive</code></td><td><code>manual</code> keeps the drive hidden until you ask for it</td><td>shown at boot</td></tr>
<tr><td><code>program</code></td><td>a Python file to run instead of the effects</td><td>the effects run</td></tr>
<tr><td><code>args</code></td><td>what to pass that program, divided by <code>|</code></td><td>it is given none</td></tr>
<tr><td><code>screenA</code></td><td>what size of screen is on SP/CE A, if you have one</td><td>2.8</td></tr>
<tr><td><code>screenB</code></td><td>the same for SP/CE B</td><td>2.8</td></tr>
<tr><td><code>stripL</code></td><td>how many LEDs are on a strip plugged into <strong>L</strong></td><td>no strip</td></tr>
<tr><td><code>stripR</code></td><td>the same for <strong>R</strong></td><td>no strip</td></tr>
</tbody></table></div>
<h3 id="running-your-own-program">Running your own program</h3>
<p>A program can sit on this drive or on the board's own filesystem, and its name may include folders: it is looked for here first, then on the board, so <code>program=examples/effects/colour/rainbow_wave.py</code> reaches one of the examples the board ships with. Where the name is in both, this drive's copy runs.</p>
<p>If it is missing, or stops with an error, the effects run instead and <code>errors.txt</code> says what happened, so a mistyped name never leaves you with a board that does nothing.</p>
<p>The effects stop while a program runs, and the board is busy with it, so <strong>Boot</strong> and ejecting do nothing. The drive is shown anyway, even with <code>drive</code> set to <code>manual</code>, so you can still edit <code>effects.txt</code>; unplug and plug back in for the change to take. A program cannot read files from this drive while it runs, so put anything it needs on the board's own filesystem.</p>
<p><code>screenA</code> and <code>screenB</code> describe the screens this file's own entries play on, so a program never sees them: it sets its own up. Pass it the size in <code>args</code> if it needs telling.</p>
<p><code>args</code> passes a program whatever it needs to know, so one program can do different things without being edited. Several are divided by <code>|</code>, and anything with a space or a colon in it goes in quotes:</p>
<pre class="entry"><code><span class="s-target">board</span><span class="s-colon">:</span> <span class="s-name">program</span><span class="s-punc">=</span><span class="s-value">slideshow.py</span> <span class="s-name">args</span><span class="s-punc">=</span><span class="s-value">posters|3</span>
<span class="s-target">board</span><span class="s-colon">:</span> <span class="s-name">program</span><span class="s-punc">=</span><span class="s-value">clock.py</span> <span class="s-name">args</span><span class="s-punc">=</span><span class="s-value">"07:30"</span></code></pre>
<p><strong>If you are writing the program</strong>, it reads them from <code>sys.argv</code>, the way any Python program does, with the first being <code>sys.argv[1]</code>. Thonny passes none when you run the same file from there, so give each one a value to fall back on and the file works either way:</p>
<pre class="python"><code>args = sys.argv[1:]
FOLDER = args[0] if args else "posters"</code></pre>
<h3 id="what-is-already-on-the-board">What is already on the board</h3>
<p>These come with the board, so <code>program=</code> reaches any of them with nothing to download:</p>
<div class="scroll"><table>
<thead><tr><th>Folder</th><th>What is in it</th></tr></thead>
<tbody>
<tr><td><code>examples/effects</code></td><td>changing from one set of effects to another as time passes</td></tr>
<tr><td><code>examples/effects/mono</code></td><td>one output at a time, and the effects that travel across several</td></tr>
<tr><td><code>examples/effects/colour</code></td><td>the same in colour, with traffic lights and crossings</td></tr>
<tr><td><code>examples/screens/single</code></td><td>one screen, its backlight, and finding what is attached</td></tr>
<tr><td><code>examples/screens/playback</code></td><td>animated GIFs and slideshows</td></tr>
<tr><td><code>examples/screens/graphics</code></td><td>drawing from code: text, colour wheels, a starfield</td></tr>
<tr><td><code>examples/screens/images</code></td><td>still pictures</td></tr>
<tr><td><code>examples/screens/layout</code></td><td>placing a picture on the screen</td></tr>
<tr><td><code>examples/screens/pair</code></td><td>two screens working together</td></tr>
<tr><td><code>examples/screens/hub</code></td><td>more than two, through a hub</td></tr>
<tr><td><code>examples/audio</code></td><td>playing a wav file</td></tr>
<tr><td><code>examples/motors</code></td><td>driving a pair of motors</td></tr>
<tr><td><code>examples/servos</code></td><td>sweeping a servo on the L connector</td></tr>
<tr><td><code>examples/strips</code></td><td>a rainbow along an LED strip</td></tr>
<tr><td><code>examples/gpio</code></td><td>using SP/CE pins as plain inputs and outputs</td></tr>
<tr><td><code>examples/showcase</code></td><td>larger builds that put several of these together</td></tr>
</tbody></table></div>
<p>Three to start with:</p>
<pre class="entry"><code><span class="s-target">board</span><span class="s-colon">:</span> <span class="s-name">program</span><span class="s-punc">=</span><span class="s-value">examples/effects/colour/sweep_trail.py</span>
<span class="s-target">board</span><span class="s-colon">:</span> <span class="s-name">program</span><span class="s-punc">=</span><span class="s-value">examples/screens/playback/animated_gif.py</span>
<span class="s-target">board</span><span class="s-colon">:</span> <span class="s-name">program</span><span class="s-punc">=</span><span class="s-value">examples/showcase/flip_dot_sign.py</span></code></pre>
<p>Anything under <code>screens</code>, <code>audio</code>, <code>motors</code>, <code>servos</code> or <code>strips</code> needs that hardware attached, and some of the showcase ones want pictures or a network of their own. The full set, with what each one does, is on <a href="https://github.com/pimoroni/picofx">GitHub</a>.</p>
<h2 id="when-something-is-wrong">When something is wrong</h2>
<p>The lights say so, and the more flashes the worse it is:</p>
<div class="scroll"><table>
<thead><tr><th>Flashes</th><th>What happened</th></tr></thead>
<tbody>
<tr><td>white, once</td><td>the computer was still writing, so the press did nothing; try again in a moment</td></tr>
<tr><td>blue, twice</td><td>something in <code>effects.txt</code> could not be read; <code>errors.txt</code> says which line</td></tr>
<tr><td>red, three times</td><td>there was no room to write <code>errors.txt</code>; this drive is full or damaged, so free some space or let a computer repair it</td></tr>
</tbody></table></div>
<p>A setting whose value is not what it takes is ignored, with a note in <code>errors.txt</code>, and the effect runs on its usual value for it.</p>
<h2 id="more-from-pimoroni">More from Pimoroni</h2>
<h3 id="boards-and-accessories">Boards and accessories</h3>
<ul><li><a href="https://shop.pimoroni.com/products/mightyfx">MightyFX</a></li><li><a href="https://shop.pimoroni.com/products/tinyfx">TinyFX</a></li><li><a href="https://shop.pimoroni.com/products/tiny-fx-w">TinyFX W</a></li><li><a href="https://shop.pimoroni.com/collections/tiny-fx">Everything in the range</a></li></ul>
<h3 id="going-further">Going further</h3>
<ul><li><a href="https://github.com/pimoroni/picofx">picofx on GitHub</a>, the library these effects come from</li><li><a href="https://badgewa.re/docs">The PicoVector drawing API</a>, for programs that draw on a screen</li></ul>
</main>

<footer>
<p>This manual is rebuilt by the board, so edits to it will not stick.</p>
</footer>

</div>
</body>
</html>
"""
