# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# Generated from the manual's parts by tools/build_manual.py. Edit those and rebuild;
# edits here are lost.

MANUAL = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tiny FX</title>
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
<li><a href="#for-any-output">For any output</a></li>
<li><a href="#for-the-rgb-output-only-since-these-bring-their-own-colour">For the RGB output only, since these bring their own colour</a></li>
<li><a href="#which-ones-travel">Which ones travel</a></li>
<li><a href="#what-the-settings-mean">What the settings mean</a></li>
</ul></details></li>
<li><a href="#sound">Sound</a></li>
<li><a href="#scenes">Scenes</a></li>
<li><details><summary><a href="#the-board">The board</a></summary><ul>
<li><a href="#running-your-own-program">Running your own program</a></li>
<li><a href="#what-is-already-on-the-board">What is already on the board</a></li>
</ul></details></li>
<li><a href="#when-something-is-wrong">When something is wrong</a></li>
<li><a href="#more-from-pimoroni">More from Pimoroni</a></li>
</ul></nav>
</div>

<main>
<h1 id="tiny-fx">Tiny FX</h1>
<p>Six mono outputs, one RGB output, a speaker, and a text file that drives them. Edit <code>effects.txt</code> on this drive, eject it, and the board applies the change straight away. No code needed, though there is room for it when you want it.</p>
<h2 id="getting-started">Getting started</h2>
<p>Edit <code>effects.txt</code> to change what the lights do, then eject this drive and the board applies the change straight away.</p>
<p>In a hurry? Save the file and press <strong>Boot</strong> once. The drive disappears and comes straight back with the new effects running, so you can keep editing. Ejecting is the surer way, since a computer does not always write the file out until then. Press <strong>Boot</strong> twice to hide the drive, and twice again to bring it back. A dim light runs along the outputs each time, one way as the computer takes the drive and the other as the board takes it back, so a double press is never mistaken for a single one.</p>
<p>Deleting <code>effects.txt</code> restores the default; emptying it leaves the board dark.</p>
<p>While the computer is copying to this drive the effects stand aside for a dim light travelling along the outputs, and come back a moment after it finishes.</p>
<p><strong>Would you rather not write the file at all? <code>PICKER.html</code> on this drive writes it for you. See <a href="#the-picker">the picker</a>. <code>EDITOR.html</code> beside it is a place to write it with the names offered as you type.</strong></p>
<h2 id="the-picker">The picker</h2>
<p><code>PICKER.html</code> on this drive writes <code>effects.txt</code> for you. Open it in Chrome or Edge, press <strong>Open FX drive</strong> and choose this drive, and the page reads the file the board is playing, so you carry on from where it is. The file it will write is shown at the foot of the page, so nothing about it is hidden.</p>
<p>Pick a stretch of outputs, tap a look from the cards to play on it, and slide its settings until it suits. The outputs can be cut into stretches that each play a look of their own. <strong>Edit board</strong> sets the order the lights are wired in, and moving the RGB output across to the mono side breaks it into three plain lights. The sounds on this drive are offered on the Sound tab. Press the plus to split what you have into scenes that take turns.</p>
<p><strong>Save to board</strong> writes the file, and the board picks it up a few seconds later. <strong>Check board</strong> reads <code>errors.txt</code> back and shows what the board made of each line. The page reaches the drive only in Chrome, Edge or another browser built on Chromium; elsewhere it says so, and <code>effects.txt</code> can still be changed in any text editor.</p>
<h2 id="writing-an-entry">Writing an entry</h2>
<pre class="shape"><code><span class="s-target">&lt;outputs&gt;</span> <span class="s-name">&lt;their settings&gt;</span><span class="s-colon">:</span> <span class="s-effect">&lt;effect&gt;</span> <span class="s-name">&lt;its settings&gt;</span></code></pre>
<pre class="entry"><code><span class="s-target">out1-6</span><span class="s-colon">:</span> <span class="s-effect">pulse_wave</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.3</span>
<span class="s-target">rgb</span><span class="s-colon">:</span> <span class="s-effect">rainbow</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.5</span>
<span class="s-target">out3</span> <span class="s-name">level</span><span class="s-punc">=</span><span class="s-value">50%</span><span class="s-colon">:</span> <span class="s-effect">pulse</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.6</span></code></pre>
<p>There is one colon in an entry. Which outputs, and how bright or what colour they are, go before it. The effect and its own settings go after.</p>
<p>Settings you leave out take their usual value. A <code>#</code> starts a comment. An entry can run on over several lines so long as the colon is on the first; indenting changes nothing.</p>
<h2 id="outputs">Outputs</h2>
<h3 id="naming-outputs">Naming outputs</h3>
<div class="scroll"><table>
<thead><tr><th>Written</th><th>Means</th></tr></thead>
<tbody>
<tr><td><code>out1</code></td><td>one output</td></tr>
<tr><td><code>out1,3,5</code></td><td>three of them</td></tr>
<tr><td><code>out1-6</code></td><td>all six</td></tr>
<tr><td><code>out6-1</code></td><td>all six, the other way round</td></tr>
<tr><td><code>out2,1,5-6</code></td><td>mixed, and in the order you write them</td></tr>
<tr><td><code>rgb</code></td><td>the RGB output</td></tr>
</tbody></table></div>
<p>The RGB output shows colour. Its red, green and blue can be driven separately as three plain lights instead, and named alongside the others:</p>
<div class="scroll"><table>
<thead><tr><th>Written</th><th>Means</th></tr></thead>
<tbody>
<tr><td><code>rgb.r</code></td><td>just the red</td></tr>
<tr><td><code>rgb.*</code></td><td>all three of them, red, green then blue</td></tr>
<tr><td><code>out1-6,rgb.*</code></td><td>all nine plain lights</td></tr>
</tbody></table></div>
<p>Order matters for the effects that travel: they move in the order you write the outputs, so list them in the order they appear in your model, which need not be number order.</p>
<h3 id="setting-an-output">Setting an output</h3>
<p>Before the colon, and separate from the effect:</p>
<div class="scroll"><table>
<thead><tr><th>Setting</th><th>What it does</th><th>If omitted</th></tr></thead>
<tbody>
<tr><td><code>level</code></td><td>how bright, 0 to 1, such as 0.5 or 50%</td><td>1</td></tr>
<tr><td><code>colour</code></td><td>a name or six-digit hex, for the RGB output when its effect brings no colour</td><td>white</td></tr>
<tr><td><code>fade</code></td><td>seconds to follow the effect, at a steady rate</td><td>follows at once</td></tr>
<tr><td><code>ease</code></td><td>seconds to follow it, settling in as a bulb does</td><td>follows at once</td></tr>
</tbody></table></div>
<pre class="entry"><code><span class="s-target">out1-6</span> <span class="s-name">level</span><span class="s-punc">=</span><span class="s-value">50%</span><span class="s-colon">:</span> <span class="s-effect">pulse</span>
<span class="s-target">rgb</span> <span class="s-name">colour</span><span class="s-punc">=</span><span class="s-value">warm</span><span class="s-colon">:</span> <span class="s-effect">flicker</span>
<span class="s-target">out1-6</span> <span class="s-name">ease</span><span class="s-punc">=</span><span class="s-value">0.4</span><span class="s-colon">:</span> <span class="s-effect">blink</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.5</span></code></pre>
<p>Colours by name: red, orange, yellow, green, cyan, blue, purple, magenta, pink, warm, white, cool, black. Or the hex a colour picker gives you, with its <code>#</code> left off. A <code>#</code> always starts a comment, so one left on a colour hides the rest of the line.</p>
<h3 id="fade-and-ease">Fade and ease</h3>
<p><code>fade</code> and <code>ease</code> take the seconds a change takes to get there. <code>fade</code> crosses evenly, which is what a stage light does; <code>ease</code> goes quickly at first and slows as it arrives, which is how a bulb warms. Two numbers divided by <code>|</code> give the rise and the fall their own lengths:</p>
<pre class="entry"><code><span class="s-target">out1-3</span> <span class="s-name">ease</span><span class="s-punc">=</span><span class="s-value">0.05|1.2</span><span class="s-colon">:</span> <span class="s-effect">blink</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">1</span></code></pre>
<h2 id="effects">Effects</h2>
<p>Every setting can be left out, and the board fills in the value shown against it below.</p>
<h3 id="for-any-output">For any output</h3>
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
<tr><td><code>flicker_each</code></td><td>as <code>flicker</code></td></tr>
<tr><td><code>pulse</code></td><td><code>speed=1</code> <code>phase=0</code></td></tr>
<tr><td><code>pulse_wave</code></td><td><code>speed=1</code> <code>length=1</code> <code>phase=0</code></td></tr>
<tr><td><code>sweep</code></td><td><code>speed=1</code> <code>length=1</code> <code>extent=1</code> <code>hold=0</code></td></tr>
<tr><td><code>random</code></td><td><code>interval=0.05</code> <code>brightness_min=0</code> <code>brightness_max=1</code></td></tr>
<tr><td><code>random_each</code></td><td>as <code>random</code></td></tr>
<tr><td><code>binary_counter</code></td><td><code>interval=0.1</code> <code>count=0</code> <code>step=1</code></td></tr>
<tr><td><code>traffic_light</code></td><td><code>red_interval=10</code> <code>red_amber_interval=5</code> <code>green_interval=10</code> <code>amber_interval=5</code></td></tr>
<tr><td><code>pelican_crossing</code></td><td><code>red_interval=8</code> <code>flashing_interval=6</code> <code>green_interval=20</code> <code>amber_interval=3</code></td></tr>
</tbody></table></div>
<h3 id="for-the-rgb-output-only-since-these-bring-their-own-colour">For the RGB output only, since these bring their own colour</h3>
<div class="scroll"><table>
<thead><tr><th>Effect</th><th>Settings</th></tr></thead>
<tbody>
<tr><td><code>rgb</code></td><td><code>red=255</code> <code>green=255</code> <code>blue=255</code></td></tr>
<tr><td><code>hsv</code></td><td><code>hue=0</code> <code>sat=1</code> <code>val=1</code></td></tr>
<tr><td><code>rainbow</code></td><td><code>speed=1</code> <code>sat=1</code> <code>val=1</code></td></tr>
<tr><td><code>hue_step</code></td><td><code>interval=1</code> <code>hue=0</code> <code>sat=1</code> <code>val=1</code> <code>steps=6</code></td></tr>
<tr><td><code>rgb_blink</code></td><td><code>colour</code> <code>speed=1</code> <code>phase=0</code> <code>duty=0.5</code></td></tr>
</tbody></table></div>
<h3 id="which-ones-travel">Which ones travel</h3>
<p>The ones ending <code>_wave</code>, <code>_sequence</code> and <code>_counter</code>, and <code>sweep</code>, travel across the outputs you name; the rest do the same thing on every one. The ones ending <code>_each</code> give every output its own: <code>flicker_each</code> dips each at its own moments, as flames do.</p>
<p><code>traffic_light</code> wants three outputs, lit red, amber and green in that order, and <code>pelican_crossing</code> five, the same three then the stop and walk figures:</p>
<pre class="entry"><code><span class="s-target">out1-3</span> <span class="s-name">ease</span><span class="s-punc">=</span><span class="s-value">0.3</span><span class="s-colon">:</span> <span class="s-effect">traffic_light</span>
<span class="s-target">out1-5</span> <span class="s-name">ease</span><span class="s-punc">=</span><span class="s-value">0.3</span><span class="s-colon">:</span> <span class="s-effect">pelican_crossing</span></code></pre>
<p><code>sweep</code> is a light that crosses the outputs and turns back at each end. Its <code>extent</code> is how far it reaches from itself, in outputs, and <code>hold</code> waits at each end, in seconds:</p>
<pre class="entry"><code><span class="s-target">out1-6</span> <span class="s-name">ease</span><span class="s-punc">=</span><span class="s-value">0.4</span><span class="s-colon">:</span> <span class="s-effect">sweep</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">1</span> <span class="s-name">extent</span><span class="s-punc">=</span><span class="s-value">1</span> <span class="s-name">hold</span><span class="s-punc">=</span><span class="s-value">1</span></code></pre>
<p><code>rgb_blink</code> takes one colour, or several to blink through in turn, divided by <code>|</code>:</p>
<pre class="entry"><code><span class="s-target">rgb</span><span class="s-colon">:</span> <span class="s-effect">rgb_blink</span> <span class="s-name">colour</span><span class="s-punc">=</span><span class="s-value">red|warm|ff8040</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.5</span></code></pre>
<h3 id="what-the-settings-mean">What the settings mean</h3>
<p><code>speed</code> is cycles a second: 1 goes round once a second, 0.5 once every two. A negative speed runs the cycle backwards. <code>interval</code>, <code>hold</code> and the flicker and signal timings are seconds. <code>length</code>, <code>flashes</code>, <code>steps</code>, <code>count</code> and <code>step</code> are plain counts. The rest run from 0 to 1, written 0.5 or 50% as you prefer, and <code>hue</code> takes degrees as well, written 180deg.</p>
<h2 id="sound">Sound</h2>
<p>The board plays a WAV file through its speaker, alongside whatever the lights are doing:</p>
<pre class="entry"><code><span class="s-target">audio</span><span class="s-colon">:</span> <span class="s-effect">wav</span> <span class="s-name">file</span><span class="s-punc">=</span><span class="s-value">chimes.wav</span>
<span class="s-target">audio</span><span class="s-colon">:</span> <span class="s-effect">wav</span> <span class="s-name">file</span><span class="s-punc">=</span><span class="s-value">ambience.wav</span> <span class="s-name">loop</span><span class="s-punc">=</span><span class="s-value">yes</span></code></pre>
<p>The file plays once as the board starts, or over and over with <code>loop</code>. The board plays one sound at a time, so each scene takes one <code>audio</code> entry, and one more may sit before any heading. Put the file on this drive beside <code>effects.txt</code>.</p>
<p>A file is looked for on this drive first, then on the board itself. While the computer is copying to this drive the sound waits in silence with the effects.</p>
<p>An ordinary uncompressed WAV plays, mono or stereo; MP3 does not.</p>
<p>The drive is small, so a lower sample rate fits more: a minute of 22kHz mono takes about 2.6MB, which is more than the drive holds, and 8kHz mono takes under 1MB.</p>
<h2 id="scenes">Scenes</h2>
<p>A file can hold several sets of effects and show them one after another. A heading in square brackets begins one, and says how long it shows for:</p>
<pre class="entry"><code><span class="s-scene">[Evening: 30s]</span>
<span class="s-target">out1-6</span><span class="s-colon">:</span> <span class="s-effect">pulse_wave</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.3</span>
<span class="s-target">rgb</span><span class="s-colon">:</span> <span class="s-effect">rainbow</span> <span class="s-name">speed</span><span class="s-punc">=</span><span class="s-value">0.2</span>

<span class="s-scene">[Night: 10s]</span>
<span class="s-target">out1-6</span><span class="s-colon">:</span> <span class="s-effect">flicker_each</span>
<span class="s-target">rgb</span> <span class="s-name">colour</span><span class="s-punc">=</span><span class="s-value">warm</span><span class="s-colon">:</span> <span class="s-effect">pulse</span></code></pre>
<p>The time is in seconds, <code>30s</code>, or in minutes, <code>10m</code>. Scenes take turns in the order they are written, then start again. Entries before the first heading are always on, whatever is showing. Add <code>restart</code> to a heading and its effects begin again every time it comes round.</p>
<h2 id="the-board">The board</h2>
<p>One entry sets the board rather than the lights, and names no output:</p>
<pre class="entry"><code><span class="s-target">board</span><span class="s-colon">:</span> <span class="s-name">reload</span><span class="s-punc">=</span><span class="s-value">auto</span></code></pre>
<div class="scroll"><table>
<thead><tr><th>Setting</th><th>What it does</th><th>If omitted</th></tr></thead>
<tbody>
<tr><td><code>drive</code></td><td><code>manual</code> keeps the drive hidden until you ask for it</td><td>shown at boot</td></tr>
<tr><td><code>reload</code></td><td><code>auto</code> plays the file the moment it is saved</td><td>wait for an eject or <strong>Boot</strong></td></tr>
<tr><td><code>program</code></td><td>a Python file to run instead of the effects</td><td>the effects run</td></tr>
<tr><td><code>args</code></td><td>what to pass that program, divided by <code>|</code></td><td>it is given none</td></tr>
</tbody></table></div>
<p>With <code>reload=auto</code>, saving <code>effects.txt</code> is enough on its own: the board notices the save, takes the drive back for a moment, and plays the new effects, exactly as a single press of <strong>Boot</strong> would. Only a save to <code>effects.txt</code> counts, so copying sounds on never interrupts anything.</p>
<h3 id="running-your-own-program">Running your own program</h3>
<p>A program can sit on this drive or on the board's own filesystem, and its name may include folders: it is looked for here first, then on the board, so <code>program=examples/effects/mono/sweep_trail.py</code> reaches one of the examples the board ships with. Where the name is in both, this drive's copy runs. If it is missing, or stops with an error, the effects run instead and <code>errors.txt</code> says what happened.</p>
<p>Saving a file that names a program, while the effects play, restarts the board, which then runs the program as it would from power on.</p>
<p>The effects stop while a program runs, and <strong>Boot</strong> and ejecting do nothing. The drive is shown anyway, even with <code>drive</code> set to <code>manual</code>, so you can still edit <code>effects.txt</code>. With <code>reload=auto</code>, saving it restarts the board, which then plays whatever it now says; without, press <strong>Reset</strong> for the change to take.</p>
<h3 id="what-is-already-on-the-board">What is already on the board</h3>
<div class="scroll"><table>
<thead><tr><th>Folder</th><th>What is in it</th></tr></thead>
<tbody>
<tr><td><code>examples/effects/mono</code></td><td>one output at a time, and the effects that travel across several</td></tr>
<tr><td><code>examples/effects/colour</code></td><td>the RGB output</td></tr>
<tr><td><code>examples/function</code></td><td>the button, the sensor connector and the supply voltage</td></tr>
<tr><td><code>examples/infrared</code></td><td>effects chosen with an infrared remote</td></tr>
<tr><td><code>examples/qwst</code></td><td>light, tilt and weather from Qw/ST breakouts</td></tr>
<tr><td><code>examples/comms</code></td><td>several boards working together</td></tr>
<tr><td><code>examples/showcase</code></td><td>larger builds that put several of these together</td></tr>
</tbody></table></div>
<p>The audio examples' sounds are not on the board, to leave this drive its room.</p>
<h2 id="when-something-is-wrong">When something is wrong</h2>
<p>The lights say so, and the more flashes the worse it is. The RGB output shows the colour:</p>
<div class="scroll"><table>
<thead><tr><th>Flashes</th><th>What happened</th></tr></thead>
<tbody>
<tr><td>white, once</td><td>the computer was still writing, so the press did nothing; try again in a moment</td></tr>
<tr><td>blue, twice</td><td>something in <code>effects.txt</code> could not be read; <code>errors.txt</code> says which line</td></tr>
<tr><td>red, three times</td><td>there was no room to write <code>errors.txt</code>; this drive is full or damaged, so free some space or let a computer repair it</td></tr>
</tbody></table></div>
<h2 id="more-from-pimoroni">More from Pimoroni</h2>
<ul><li><a href="https://shop.pimoroni.com/products/tinyfx">TinyFX</a></li><li><a href="https://shop.pimoroni.com/products/tiny-fx-w">TinyFX W</a></li><li><a href="https://github.com/pimoroni/picofx">picofx on GitHub</a>, the library these effects come from</li></ul>
</main>

<footer>
<p>This manual is rebuilt by the board, so edits to it will not stick.</p>
</footer>

</div>
</body>
</html>
"""
