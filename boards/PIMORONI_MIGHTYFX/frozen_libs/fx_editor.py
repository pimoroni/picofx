# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# Generated from editor/*.html and the autofx tables by tools/build_editor.py.
# Edit those and rebuild; edits here are lost.


PICKER = """\
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>FX Picker</title>
<script src="catalogue.js"></script>
<style>
:root{
 --bg:#f5f3ef; --panel:#fff; --ink:#26221e; --dim:#8a8378; --line:#e2ddd4;
 --accent:#00857d; --accent-ink:#fff; --warn:#b33; --warn-bg:#fbeaea;
 --stripL:#c2570f; --stripR:#8a1f6d;
}
*{box-sizing:border-box}
body{font:16px/1.5 system-ui,sans-serif;margin:0;background:var(--bg);color:var(--ink)}
header{display:flex;align-items:center;gap:.8rem;padding:.8rem 1.4rem;background:var(--panel);
 border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
header h1{font-size:1.1rem;margin:0 auto 0 0}
button{font:inherit;padding:.5rem 1rem;border:1px solid var(--line);border-radius:8px;
 background:var(--panel);cursor:pointer}
button.primary{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);font-weight:600}
button:disabled{opacity:.4;cursor:default}
main{max-width:52rem;margin:1.5rem auto;padding:0 1.4rem}
#status{font-size:.85rem;color:var(--dim)}
.banner{padding:.8rem 1.1rem;border-radius:10px;margin:1rem 0;background:#e7f2f1}
.banner.warn{background:var(--warn-bg);color:var(--warn)}
.banner.hold{background:#fdf3e0;color:#8a6415}
.banner pre{margin:.4rem 0 0;white-space:pre-wrap;font-size:.85rem}
.note{background:#e7f2f1;border-radius:10px;padding:.7rem 1.1rem;margin:0 0 1.2rem;font-size:.9rem}
.tag{display:inline-block;font-size:.75rem;background:#fdf3e0;color:#8a6415;border-radius:99px;
 padding:.1rem .55rem;margin-left:.4rem}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;
 padding:1.1rem 1.4rem;margin:1.2rem 0}
.panel h2{font-size:1rem;margin:0 0 .6rem;display:flex;align-items:baseline;gap:.6rem}
.says{font-weight:400;font-size:.85rem;color:var(--dim)}
.panel h2 .says{margin-left:0}
#outputs .says{margin-left:auto}
.side-head{display:flex;align-items:center;gap:.7rem;margin:1rem 0 .5rem;font-size:.92rem}
.side-head:first-child{margin-top:0}
.side-head .chain{margin-left:.3rem;flex-grow:1}
.side-head .chain svg{height:auto}
.side-head .says{flex-shrink:1}

/* The outputs are the one drawing you can act on, so they are buttons: a socket
   each, a ring where the pointer is, and a hole where one has been left out */
.lamps{display:flex;gap:.4rem;flex-shrink:0}
.lamp{padding:.3rem .3rem .15rem;border:1px solid var(--line);border-radius:8px;
 background:var(--panel);line-height:1;cursor:pointer}
.lamp:hover:enabled{border-color:var(--dim)}
.lamp:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.lamp:disabled{cursor:default}
.lamp i{display:block;width:1.5rem;height:1.5rem;border-radius:5px;
 box-shadow:inset 0 0 0 1px rgba(0,0,0,.14)}
.lamp.off i{background:repeating-linear-gradient(45deg,#f0eeea,#f0eeea 4px,
 #e0dbd2 4px,#e0dbd2 8px)}
.lamp b{display:block;font:400 .68rem/1.6 system-ui,sans-serif;color:var(--dim);
 text-align:center}
.lamp.off b{color:#c3bdb3}
.lamp.carried{opacity:.35}
.lamp.landing{border-color:var(--accent);box-shadow:-2px 0 0 var(--accent)}
.lamp.landing.after{box-shadow:2px 0 0 var(--accent)}

/* Putting the outputs back the way the board has them */
.putback{align-self:center;margin-left:.2rem;padding:.25rem .55rem;
 border:1px solid var(--line);border-radius:7px;background:var(--panel);
 font:400 .74rem system-ui,sans-serif;color:var(--dim);cursor:pointer}
.putback:hover{border-color:var(--dim);color:var(--ink)}

/* Which way a run travels, shown rather than described */
.way{padding:.25rem .4rem;line-height:0;color:var(--ink);border-radius:6px}
.way:hover{border-color:var(--dim)}

/* A strip's side and its length are facts about the board, as a screen's size is,
   so they sit together in the side's own colour and everything the scene chooses
   follows to the right of it */
.strip-tag{display:flex;align-items:center;gap:.45rem;padding:.32rem .55rem;
 border-radius:9px;color:#fff;font:600 .85rem system-ui,sans-serif}
.strip-tag.l{background:var(--stripL)}
.strip-tag.r{background:var(--stripR)}
.strip-tag input[type=number]{width:4.4rem;padding:.12rem .3rem;text-align:center;
 border:1px solid rgba(255,255,255,.55);border-radius:6px;
 background:rgba(255,255,255,.16);color:#fff;font:inherit;font-weight:400}
.strip-tag small{font-weight:400;opacity:.85}

.opt{display:flex;align-items:center;gap:.35rem;font-size:.85rem;color:var(--dim);cursor:pointer}
.opt input[type=number]{font:inherit;font-size:.85rem;width:4rem;padding:.2rem .3rem;
 border:1px solid var(--line);border-radius:6px}

/* The hero: the same gallery a first-timer meets, three clicks to a lit board */
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(11rem,1fr));gap:1rem;margin:1rem 0}
.card{background:var(--panel);border:2px solid var(--line);border-radius:14px;padding:0;
 overflow:hidden;cursor:pointer;text-align:left;transition:transform .1s}
.card:hover{transform:translateY(-2px)}
.card.picked{border-color:var(--accent)}
.card .bar{height:3rem;display:flex}
.card .bar span{flex:1}
.card .name{padding:.55rem .9rem .7rem;font-weight:600;display:flex;
 align-items:center;gap:.5rem}
/* Which strips play this look, in the corner the way a picture says its screen */
.card .who{margin-left:auto;display:flex;gap:.25rem}
.card .who span{width:1.35rem;height:1.35rem;border-radius:6px;border:1px solid var(--line);
 font-size:.72rem;font-weight:700;color:var(--dim);display:flex;align-items:center;
 justify-content:center;background:var(--panel)}
.card .who span.lit{color:#fff;border-color:transparent}
.card .who span.lit.l{background:var(--stripL)}
.card .who span.lit.r{background:var(--stripR)}
.card .who span.off{background:#efece6;border-color:transparent;color:#c3bdb3;
 cursor:default}
.card.nothing .bar{background:repeating-linear-gradient(45deg,#f0eeea,#f0eeea 7px,#e4e0d9 7px,#e4e0d9 14px)}

/* What this scene chose, and the settings that shape it, kept together: the name
   on the left and the sliders taking the rest */
.tuned{display:flex;align-items:center;gap:.9rem;margin:.45rem 0 0;padding:.45rem .7rem;
 border:1px solid var(--line);border-radius:10px;background:#fff}
.tuned .who{flex:0 0 auto;min-width:6.5rem;font-size:.8rem;color:var(--dim);
 line-height:1.25}
.tuned .who b{display:block;font-size:.92rem;color:var(--ink)}
.tuned .tuning{flex:1;grid-template-columns:auto 1fr;gap:.35rem .7rem}
.tuned .tuning label{white-space:nowrap}
.tuning{display:grid;grid-template-columns:7rem 1fr;align-items:center;gap:.6rem 1rem}
.tuning input{width:100%;accent-color:var(--accent)}
.tuning label{font-size:.9rem}

/* One set of pictures, each able to go to A, to B, or to both */
.assets{display:grid;grid-template-columns:repeat(auto-fill,minmax(6.2rem,1fr));gap:.7rem}
.asset{position:relative;border:2px solid var(--line);border-radius:10px;overflow:hidden;
 background:var(--panel);padding:0}
.asset.onA{border-color:#1f6feb}
.asset.onB{border-color:#a44ad0}
.asset.onAB{border-color:var(--accent)}
.asset .face{position:relative;height:3.6rem;display:flex;align-items:center;
 justify-content:center;overflow:hidden;
 font-size:.7rem;color:var(--dim);background:linear-gradient(135deg,#efece6,#e3dfd6)}
.asset .face img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.asset .kind{position:absolute;top:2px;left:2px;font-size:.6rem;
 background:rgba(20,20,22,.7);color:#fff;border-radius:4px;padding:0 .3rem;z-index:1}
/* The file name is only wanted when you go looking for it, so it lies over the
   picture on hover or on keyboard focus rather than taking a row of its own */
.asset .label{position:absolute;left:0;right:0;bottom:0;font-size:.7rem;
 padding:.25rem .4rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
 background:rgba(20,20,22,.82);color:#fff;opacity:0;transition:opacity .12s;
 pointer-events:none;z-index:1}
.asset:hover .label,.asset:focus-within .label{opacity:1}
.asset .pick{display:flex;border-top:1px solid var(--line)}
.asset .pick button{flex:1;border:0;border-radius:0;padding:.2rem;font-size:.75rem;
 font-weight:700;color:var(--dim);background:var(--panel)}
.asset .pick button:first-child{border-right:1px solid var(--line)}
.asset .pick button.lit{background:#1f6feb;color:#fff}
.asset .pick button.lit.b{background:#a44ad0}
/* Files come to the drive without leaving the page: a dashed tile at the end of
   each collection, in the plus's own manner */
.adder{border:1px dashed rgba(15,138,114,.5);border-radius:10px;background:rgba(15,138,114,.06);
 color:var(--accent);cursor:pointer;display:flex;flex-direction:column;
 align-items:center;justify-content:center;gap:.25rem;
 font:600 .74rem system-ui,sans-serif;min-height:5.2rem}
.adder:hover{background:rgba(15,138,114,.14);border-color:var(--accent)}
.adder svg{display:block}
.sounds .adder{width:8.4rem}

/* Deleting is offered where the file is, quiet until the pointer arrives */
.bin{position:absolute;top:2px;right:2px;z-index:2;width:1.2rem;height:1.2rem;
 border-radius:5px;background:rgba(20,20,22,.7);color:#fff;line-height:1.2rem;
 text-align:center;font-size:.8rem;cursor:pointer;opacity:0;transition:opacity .12s}
.asset:hover .bin,.asset:focus-within .bin,.sound:hover .bin{opacity:1}
.bin:hover{background:#b4443a}
.sound{position:relative}

.screens-head{display:grid;grid-template-columns:1fr 1fr;gap:1.2rem;margin-bottom:1rem}
.screen-box{border:2px solid var(--line);border-radius:10px;overflow:hidden}
.screen-box.a{border-color:#1f6feb}
.screen-box.b{border-color:#a44ad0}
.screen-box h3{font-size:.9rem;margin:0;padding:.4rem .9rem;color:#fff;background:var(--dim);
 display:flex;align-items:center;gap:.4rem}
/* The panel's size is a fact about the board, not about a scene, so it rides in
   the coloured band with the port's name instead of among the settings */
.screen-box h3 select.inband{margin-left:.4rem;border:1px solid rgba(255,255,255,.55);
 border-radius:6px;background:rgba(255,255,255,.15);color:#fff;font:inherit;
 font-size:.78rem;padding:.1rem .25rem}
.screen-box h3 select.inband option{color:var(--ink)}
.screen-box h3 .drop{margin-left:auto;background:transparent;border:0;color:#fff;font-size:1.1rem;
 line-height:1;padding:0 .2rem;opacity:.8}
.screen-box h3 .drop:hover{opacity:1}
.screen-box .body.adding{justify-content:center;padding:1.4rem .9rem}
.keep{display:flex;align-items:baseline;gap:.5rem;flex-wrap:wrap;
 width:calc(100% - 1.8rem);margin:0 .9rem .8rem;text-align:left;padding:.35rem .55rem;
 border:2px solid var(--line);border-radius:8px;background:var(--panel);font-size:.78rem}
.keep.picked{border-color:var(--accent)}
.keep b{flex-shrink:0}
/* The entry says itself in full: a truncated one is the half a reader cannot check */
.keep code{color:var(--dim);font-size:.72rem;line-height:1.45;word-break:break-word;
 flex:1 1 100%}
.screen-box.a h3{background:#1f6feb}
.screen-box.b h3{background:#a44ad0}
.screen-box .body{padding:.7rem .9rem;display:flex;flex-direction:column;gap:.7rem;
 align-items:center}
.screen-box .settings{width:100%;display:grid;grid-template-columns:1fr 1fr;
 gap:.4rem .8rem;align-items:center}
.screen-box .settings .showing{margin:0}
.screen-box .row{display:flex;gap:.4rem;align-items:center;flex-wrap:wrap}
.holder{flex-shrink:0;line-height:0}
select{font:inherit;font-size:.85rem;padding:.25rem .3rem;border:1px solid var(--line);border-radius:6px}
.showing{font-size:.85rem;color:var(--dim);margin-top:.4rem}
.showing b{color:var(--ink)}
pre.file{font:.85rem/1.5 ui-monospace,Consolas,monospace;background:var(--panel);
 border:1px solid var(--line);border-radius:10px;padding:1rem;white-space:pre-wrap}
/* The editor's own palette, so the two pages say the same thing the same way */
.s-target{color:#1f6feb}
.s-effect{color:#0a7f78;font-weight:600}
.s-value{color:#a8500a}
.s-scene{color:#7b3fb8;font-weight:600}
.s-name{color:var(--ink)}
.s-punc{color:#5d656e}
.s-colon{color:var(--ink);font-weight:700}
.s-comment{color:#8a8378;font-style:italic}
details{margin:1.2rem 0}
summary{cursor:pointer;color:var(--dim);font-size:.9rem}
footer{max-width:52rem;margin:0 auto 2rem;padding:0 1.4rem;font-size:.8rem;color:var(--dim)}

/* One sound plays at a time, so these behave as a gallery of one choice, each
   showing its shape and how long it runs */
.sounds{display:flex;flex-wrap:wrap;gap:.7rem}
.sound{width:8.4rem;padding:.45rem .5rem .4rem;border:2px solid var(--line);
 border-radius:10px;background:var(--panel);text-align:left;cursor:pointer}
.sound:hover{border-color:var(--dim)}
.sound.picked{border-color:var(--accent)}
.sound svg{display:block;width:100%;height:1.8rem}
.sound b{display:block;font:600 .74rem/1.5 system-ui,sans-serif;color:var(--ink);
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sound small{color:var(--dim);font-size:.68rem}
.sound.quiet svg{opacity:.6}

/* Whether it starts again as it ends */
.again{align-self:center;padding:.3rem .6rem;border:1px solid var(--line);
 border-radius:7px;background:var(--panel);font:400 .78rem system-ui,sans-serif;
 color:var(--dim);cursor:pointer}
.again:hover:enabled{border-color:var(--dim);color:var(--ink)}
.again:disabled{opacity:.45;cursor:default}
.again.on{border-color:var(--accent);color:var(--accent);font-weight:600}

/* Scenes take turns, so they are tabs: the bar is only drawn once there is more
   than the one everything starts in, and the plus is always there */
.tabbar{display:flex;flex-wrap:wrap;align-items:stretch;gap:.45rem;margin:.4rem 0 0}
.tab{flex:0 0 auto;display:flex;flex-direction:column;justify-content:center;
 gap:.3rem;width:8.2rem;padding:.4rem .55rem;border:1px solid var(--line);
 border-radius:9px 9px 0 0;border-bottom-color:var(--line);background:#f1efeb;
 cursor:pointer;text-align:left;margin-bottom:-1px;min-height:3.4rem;overflow:hidden}
.tab b,.tab small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tab:hover{border-color:var(--dim)}
/* The one being edited joins the area below it, as a browser tab joins its page */
.tab.on{background:var(--panel);border-color:var(--line);border-bottom-color:var(--panel);
 box-shadow:inset 0 3px 0 var(--accent)}
.tab.on b{color:var(--ink)}
.tabbar.wrapped{display:grid;gap:.45rem;margin-bottom:.5rem;
 grid-template-columns:repeat(auto-fill,minmax(8.4rem,1fr))}
.tabbar.wrapped .tab{width:auto;border-radius:9px;margin-bottom:0}
.tabbar.wrapped .plus{margin:0;width:100%;min-height:3.4rem;justify-content:center;
 border-style:dashed}
.tabbar.wrapped .tab.on{border-color:var(--accent);border-bottom-color:var(--accent)}
.scenebody.framed.loose{border-radius:12px}
.tab .look{display:flex;width:100%;height:.32rem;border-radius:2px;overflow:hidden;
 background:repeating-linear-gradient(45deg,#f0eeea,#f0eeea 3px,#e0dbd2 3px,#e0dbd2 6px)}
.tab .look span{flex:1}
.tab b{font:600 .78rem/1.3 system-ui,sans-serif;color:var(--ink)}
.tab small{font-size:.68rem;color:var(--dim)}
.tab .shut{float:right;border:0;background:none;color:var(--dim);cursor:pointer;
 font-size:.85rem;line-height:1;padding:0 0 0 .3rem}
.tab .shut:hover{color:#b4443a}
.tab.carried{opacity:.4}
.tab.landing{box-shadow:-2px 0 0 var(--accent)}
.plus{margin-left:auto;align-self:center;display:flex;align-items:center;gap:.35rem;
 padding:.42rem .7rem;border:1px solid rgba(15,138,114,.4);border-radius:9px;
 background:rgba(15,138,114,.08);color:var(--accent);cursor:pointer;
 font:600 .78rem system-ui,sans-serif}
.plus:hover{background:rgba(15,138,114,.16);border-color:var(--accent)}
.plus svg{display:block}

/* Everything inside the frame belongs to the tab above it */
.scenebody{border:1px solid transparent;border-radius:0 12px 12px 12px;padding:0}
.scenebody.framed{border-color:var(--line);background:var(--panel);
 padding:.9rem 1rem 1.1rem;margin-bottom:1rem}
.scenebody.framed .panel{background:#faf9f7}

/* What one scene is called, and how long it holds */
.sceneset{display:flex;align-items:center;flex-wrap:wrap;gap:.5rem;
 margin:0 0 .9rem;font-size:.82rem;color:var(--dim)}
.sceneset input{border:1px solid var(--line);border-radius:7px;background:#fff;
 padding:.32rem .5rem;font:inherit;color:var(--ink)}
.sceneset input:focus{outline:2px solid rgba(15,138,114,.35);outline-offset:1px;
 border-color:var(--accent)}
.sceneset input[type=text]{width:10rem;font-weight:600}
.sceneset input[type=number]{width:4.2rem;text-align:center}
.sceneset label{display:flex;align-items:center;gap:.35rem;cursor:pointer;
 padding:.3rem .55rem;border:1px solid var(--line);border-radius:7px;
 background:var(--panel)}
.sceneset label:hover{border-color:var(--dim)}

/* Lines the file already had that no control stands for, carried word for word */
.keptlines{border:1px dashed var(--line);border-radius:10px;padding:.6rem .9rem;
 margin:1.2rem 0;font-size:.82rem;color:var(--dim)}
.keptlines .row{display:flex;align-items:center;gap:.5rem;margin:.2rem 0}
.keptlines code{flex:1;font-size:.75rem;color:var(--ink);word-break:break-word}
.keptlines .drop{border:none;background:none;color:var(--dim);font-size:1rem;
 line-height:1;padding:0 .3rem;cursor:pointer}
.keptlines .drop:hover{color:var(--warn)}
</style>
</head>
<body>
<header>
 <h1>Make some lights</h1>
 <span id="status"></span>
 <button id="open" class="primary">Open the FX drive</button>
 <button id="openOther" hidden>Open another drive</button>
 <button id="save" disabled>Put it on the board</button>
 <button id="check" disabled>Did it work?</button>
</header>
<main>
<div id="banner"></div>
<div class="note" id="recognised" hidden></div>

<div class="tabbar" id="tabs"></div>
<div class="scenebody" id="sceneBody">
<div id="sceneSettings"></div>

<p style="margin:.2rem 0 0">Pick a look for your seven lights. Slide until it feels right.
 Put it on the board.</p>
<div class="gallery" id="gallery"></div>

<div class="panel">
 <h2>Outputs<span class="says">tap one to leave it out, drag to match
  your build</span></h2>
 <div id="outputs"></div>
</div>

<div class="panel">
 <h2>Strips<span class="says">how long each one is, and the look it plays</span></h2>
 <div id="strips"></div>
</div>

<div class="panel">
 <h2>Screens<span class="says" id="screensSays">one set of pictures, each able to go to A,
  to B, or to both</span></h2>
 <div class="screens-head" id="screensHead"></div>
 <div class="assets" id="assets"></div>
</div>

<div class="keptlines" id="kept" hidden></div>
</div>

<div class="panel">
 <h2>Sound<span class="says" id="soundSays">one wav, playing on while the lights run</span></h2>
 <div id="sound"></div>
</div>

<label class="opt" style="margin:1.2rem 0"
 title="The board plays the file as soon as it is saved, with no eject">
 <input type="checkbox" id="straight" checked> play it as soon as I save</label>

<details>
 <summary>The file this writes (effects.txt, editable by hand too)</summary>
 <pre class="file" id="preview"></pre>
</details>
</main>
<footer>
Each choice on this page writes plain lines into effects.txt, which stays a file
anyone can open and edit by hand. MANUAL.html on the drive explains every line.
</footer>

<script>
"use strict";

// The catalogue is generated beside this page; without it the screen and strip
// names cannot be known, so say so instead of failing silently
if (typeof CATALOGUE === "undefined") {
  window.CATALOGUE = {board_settings: {screena: ["2.8", "1.54"], screenb: ["2.8", "1.54"]},
                      screen_ports: ["screena", "screenb"], strips: ["stripl", "stripr"]};
  document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("banner").innerHTML =
      "<div class='banner warn'>catalogue.js is missing from this folder, so the " +
      "board's ports are assumed. Run tools/build_editor.py to write it.</div>";
  });
}

var SCREENS = CATALOGUE.screen_ports.map(function (name) {
  return name.slice(-1).toUpperCase();
});
var STRIP_IDS = CATALOGUE.strips.map(function (name) {
  return "strip" + name.slice(-1).toUpperCase();
});

var HEADER = "# Written by the FX picker. Everything here can be edited by hand;\\n" +
             "# MANUAL.html on this drive explains every line.\\n";

// ---- helpers -------------------------------------------------------------------

function r2(n) { return Math.round(n * 100) / 100; }
function lerp(a, b, t) { return r2(a + (b - a) * t); }
function unlerp(v, a, b) {
  var t = (v - a) / (b - a);
  return Math.max(0, Math.min(1, t));
}

// Each look picks from a palette of its own, so the middle of the slider is the
// colour its card shows and moving it stays within what suits that look
function tone(palette, t) {
  return palette[Math.min(palette.length - 1, Math.floor(t * palette.length))];
}
function toneBack(palette, colour) {
  var at = palette.indexOf(colour);
  return at < 0 ? null : (at + 0.5) / palette.length;
}

// A travelling effect's length scales with the run so the wave keeps its
// proportion whatever the light count
function span(count, mood) {
  return Math.max(2, Math.round(count * lerp(2, 0.6, mood)));
}

function quoted(name) {
  return name.indexOf(" ") >= 0 ? '"' + name + '"' : name;
}

// A run of numbers as the file writes them: climbing or falling by one closes up
// into a range, a pair stays a pair, and anything else is listed
function rangify(list) {
  var parts = [];
  var i = 0;
  while (i < list.length) {
    var j = i;
    if (j + 1 < list.length && list[j + 1] === list[j] + 1) {
      while (j + 1 < list.length && list[j + 1] === list[j] + 1) j++;
    } else if (j + 1 < list.length && list[j + 1] === list[j] - 1) {
      while (j + 1 < list.length && list[j + 1] === list[j] - 1) j++;
    }
    var count = j - i + 1;
    if (count === 1) parts.push(String(list[i]));
    else if (count === 2) parts.push(list[i] + "," + list[j]);
    else parts.push(list[i] + "-" + list[j]);
    i = j + 1;
  }
  return parts.join(",");
}

// The numbers a selector names, in the order it names them, or null where a part
// does not read as numbers at all
function expandNumbers(text) {
  var out = [];
  var parts = text.split(",");
  for (var i = 0; i < parts.length; i++) {
    var one = parts[i].match(/^(\\d+)(?:-(\\d+))?$/);
    if (!one) return null;
    var from = Number(one[1]);
    var to = one[2] === undefined ? from : Number(one[2]);
    var step = to >= from ? 1 : -1;
    for (var n = from; n !== to + step; n += step) out.push(n);
  }
  return out;
}

// The playing outputs split round-robin into up to three groups, which is how a
// three-colour look lands one colour per light in turn
function roundRobin(playing, ways) {
  var groups = [];
  playing.forEach(function (which, i) {
    var at = i % ways;
    (groups[at] = groups[at] || []).push(which);
  });
  return groups;
}

// A strip cut into up to three contiguous runs, as selectors, low end first or
// high end first to match how the strip is wired
function stripThirds(name, count, reversed, ways) {
  var edges = [];
  for (var i = 0; i <= ways; i++) edges.push(Math.round(count * i / ways));
  var parts = [];
  for (var g = 0; g < ways; g++) {
    var from = edges[g] + 1;
    var to = edges[g + 1];
    if (to < from) continue;
    parts.push(reversed ? name + (count - from + 1) + "-" + (count - to + 1)
                        : name + from + "-" + to);
  }
  return parts;
}

// ---- the looks -----------------------------------------------------------------
// Each look writes real entries for whatever target it is handed: the board's
// outputs in the order they are to play, or a strip of any length. entries()
// returns the lines; reads() inverts a parsed line back into slider positions,
// and the parser only trusts it where regenerating reproduces the file exactly.

var BREATHE_TONES = ["blue", "cool", "cyan", "green", "warm"];
var SPARKLE_TONES = ["cyan", "cool", "white", "warm", "yellow"];
var SCANNER_TONES = ["magenta", "blue", "red", "yellow", "white"];
var CHASE_TONES = ["magenta", "white", "yellow", "cyan", "green"];
var COUNTER_TONES = ["white", "cyan", "green", "yellow", "red"];
var PARTY_FIRST = ["red", "blue", "magenta", "cyan", "white"];
var PARTY_SECOND = ["green", "white", "yellow", "warm", "red"];
var PARTY_THIRD = ["blue", "green", "cyan", "white", "magenta"];

var LOOKS = [
  {
    name: "Rainbow", mood: "Colour spread", spans: true,
    strip: ["#e33", "#e73", "#ea3", "#3a5", "#36c", "#63c", "#a3c"],
    entries: function (target, pace, mood) {
      return [target.selector + ": rainbow_wave speed=" + lerp(0.05, 0.8, pace) +
              " length=" + span(target.count, mood)];
    },
    reads: function (ch, fx, target) {
      if (fx.speed === undefined || fx.length === undefined) return null;
      return {pace: unlerp(Number(fx.speed), 0.05, 0.8),
              mood: unlerp(Number(fx.length) / target.count, 2, 0.6)};
    },
    effect: "rainbow_wave"
  },
  {
    name: "Campfire", mood: "Embers to blaze", spans: true,
    strip: ["#812200", "#c43a00", "#ff5a00", "#ff8c1a", "#ff5a00", "#c43a00", "#812200"],
    entries: function (target, pace, mood) {
      return [target.selector + " colour=ff5a00: flicker brightness=" + lerp(0.5, 1, mood) +
              " dimness=" + lerp(0.7, 0.35, mood) +
              " bright_min=" + lerp(0.1, 0.02, pace) + " bright_max=" + lerp(0.4, 0.1, pace) +
              " dim_min=" + lerp(0.08, 0.02, pace) + " dim_max=" + lerp(0.3, 0.08, pace)];
    },
    reads: function (ch, fx) {
      if (fx.bright_min === undefined || fx.brightness === undefined) return null;
      return {pace: unlerp(Number(fx.bright_min), 0.1, 0.02),
              mood: unlerp(Number(fx.brightness), 0.5, 1)};
    },
    effect: "flicker"
  },
  {
    name: "Breathe", mood: "Colour", spans: true,
    strip: ["#2b7f8f", "#37a0b4", "#43c1d9", "#56d8f0", "#43c1d9", "#37a0b4", "#2b7f8f"],
    entries: function (target, pace, mood) {
      return [target.selector + " colour=" + tone(BREATHE_TONES, mood) +
              " ease=" + lerp(0.8, 0.2, pace) + ": pulse speed=" + lerp(0.08, 0.5, pace)];
    },
    reads: function (ch, fx) {
      var mood = toneBack(BREATHE_TONES, ch.colour);
      if (fx.speed === undefined || mood === null) return null;
      return {pace: unlerp(Number(fx.speed), 0.08, 0.5), mood: mood};
    },
    effect: "pulse"
  },
  {
    name: "Wave", mood: "Wave length", spans: true,
    strip: ["#122438", "#2a4a6a", "#4a7fb5", "#7fb5e6", "#4a7fb5", "#2a4a6a", "#122438"],
    entries: function (target, pace, mood) {
      return [target.selector + " colour=cool: pulse_wave speed=" + lerp(0.1, 1, pace) +
              " length=" + span(target.count, mood)];
    },
    reads: function (ch, fx, target) {
      if (fx.speed === undefined || fx.length === undefined) return null;
      return {pace: unlerp(Number(fx.speed), 0.1, 1),
              mood: unlerp(Number(fx.length) / target.count, 2, 0.6)};
    },
    effect: "pulse_wave"
  },
  {
    name: "Sparkle", mood: "Colour", spans: true,
    strip: ["#ffffff", "#999999", "#ffffff", "#cccccc", "#eeeeee", "#888888", "#ffffff"],
    entries: function (target, pace, mood) {
      return [target.selector + " colour=" + tone(SPARKLE_TONES, mood) +
              ": random interval=" + lerp(0.25, 0.03, pace) +
              " brightness_min=0 brightness_max=1"];
    },
    reads: function (ch, fx) {
      var mood = toneBack(SPARKLE_TONES, ch.colour);
      if (fx.interval === undefined || mood === null) return null;
      return {pace: unlerp(Number(fx.interval), 0.25, 0.03), mood: mood};
    },
    effect: "random"
  },
  {
    name: "Scanner", mood: "Colour", spans: true,
    strip: ["#330000", "#660000", "#cc0000", "#ff3333", "#cc0000", "#660000", "#330000"],
    entries: function (target, pace, mood) {
      return [target.selector + " colour=" + tone(SCANNER_TONES, mood) +
              " fade=" + lerp(0.5, 0.15, pace) + ": sweep speed=" + lerp(0.3, 2, pace) +
              " length=" + target.count +
              " extent=" + Math.max(1, Math.round(target.count / 8))];
    },
    reads: function (ch, fx) {
      var mood = toneBack(SCANNER_TONES, ch.colour);
      if (fx.speed === undefined || mood === null) return null;
      return {pace: unlerp(Number(fx.speed), 0.3, 2), mood: mood};
    },
    effect: "sweep"
  },
  {
    name: "Chase", mood: "Colour", spans: true,
    strip: ["#111111", "#111111", "#ffff00", "#ffd24a", "#111111", "#111111", "#111111"],
    entries: function (target, pace, mood) {
      return [target.selector + " colour=" + tone(CHASE_TONES, mood) +
              " fade=" + lerp(0.4, 0.1, pace) + ": flash_sequence speed=" + lerp(0.3, 2, pace) +
              " length=" + target.count + " flashes=1 window=0.4"];
    },
    reads: function (ch, fx) {
      var mood = toneBack(CHASE_TONES, ch.colour);
      if (fx.speed === undefined || mood === null) return null;
      return {pace: unlerp(Number(fx.speed), 0.3, 2), mood: mood};
    },
    effect: "flash_sequence"
  },
  {
    name: "Counter", mood: "Colour", spans: true,
    strip: ["#00ff00", "#111111", "#00ff00", "#00ff00", "#111111", "#00ff00", "#111111"],
    entries: function (target, pace, mood) {
      return [target.selector + " colour=" + tone(COUNTER_TONES, mood) +
              ": binary_counter interval=" + lerp(1, 0.08, pace)];
    },
    reads: function (ch, fx) {
      var mood = toneBack(COUNTER_TONES, ch.colour);
      if (fx.interval === undefined || mood === null) return null;
      return {pace: unlerp(Number(fx.interval), 1, 0.08), mood: mood};
    },
    effect: "binary_counter"
  },
  {
    // Two banks flashing against each other with a quiet gap between, landed on
    // the playing outputs in their order, so a lightbar of any width works.
    // spans false keeps it off the strips, whose one run has no banks
    name: "Emergency", mood: "Red and blue to amber", spans: false,
    strip: ["#dd2222", "#2222dd", "#dd2222", "#111111", "#2222dd", "#dd2222", "#2222dd"],
    entries: function (target, pace, mood) {
      var speed = lerp(0.6, 2.5, pace);
      var amber = mood > 0.75;
      var playing = target.playing;
      var half = playing.length === 1 ? 1 : Math.floor(playing.length / 2);
      var left = playing.slice(0, half);
      var right = playing.slice(playing.length - half);
      var gap = playing.slice(half, playing.length - half);
      var lines = ["out" + rangify(left) + " colour=" + (amber ? "yellow" : "red") +
                   ": flash speed=" + speed + " flashes=3 window=0.5"];
      if (right.length && playing.length > 1)
        lines.push("out" + rangify(right) + " colour=" + (amber ? "yellow" : "blue") +
                   ": flash speed=" + speed + " flashes=3 window=0.5 phase=0.5");
      if (gap.length && playing.length > 1)
        lines.push("out" + rangify(gap) + ": none");
      return lines;
    },
    reads: function (ch, fx) {
      if (fx.speed === undefined || fx.flashes !== "3") return null;
      return {pace: unlerp(Number(fx.speed), 0.6, 2.5),
              mood: ch.colour === "yellow" ? 0.9 : 0.4};
    },
    effect: "flash"
  },
  {
    // Five lamps in the crossing's own colours, landed on the first five playing
    // outputs; any beyond them are told to stay dark, and fewer take fewer lamps
    name: "Pelican crossing", mood: "Lamp softness", spans: false,
    strip: ["#ff0000", "#ff7800", "#00d28c", "#ff0000", "#00d28c", "#111111", "#111111"],
    entries: function (target, pace, mood) {
      var scale = lerp(2, 0.4, pace);
      var playing = target.playing;
      var lamps = playing.slice(0, 5);
      var rest = playing.slice(5);
      var colours = ["red", "ff7800", "00d28c", "red", "00d28c"].slice(0, lamps.length);
      var lines = ["out" + rangify(lamps) + " colour=" + colours.join(",") +
                   " ease=" + lerp(0.05, 0.6, mood) +
                   ": pelican_crossing red_interval=" + r2(8 * scale) +
                   " flashing_interval=" + r2(6 * scale) +
                   " green_interval=" + r2(20 * scale) +
                   " amber_interval=" + r2(3 * scale)];
      if (rest.length) lines.push("out" + rangify(rest) + ": none");
      return lines;
    },
    reads: function (ch, fx) {
      if (fx.red_interval === undefined || ch.ease === undefined) return null;
      return {pace: unlerp(Number(fx.red_interval) / 8, 2, 0.4),
              mood: unlerp(Number(ch.ease), 0.05, 0.6)};
    },
    effect: "pelican_crossing"
  },
  {
    // Three colours chase each other across whatever plays it: the lights split
    // into three sets, each flashing in its own colour a third of a beat apart
    name: "Party", mood: "Colour", spans: true,
    strip: ["#ff00ff", "#ffff00", "#00ffff", "#ff00ff", "#ffff00", "#00ffff", "#ff00ff"],
    entries: function (target, pace, mood) {
      var speed = lerp(1, 4, pace);
      var colours = [tone(PARTY_FIRST, mood), tone(PARTY_SECOND, mood),
                     tone(PARTY_THIRD, mood)];
      var groups;
      if (target.kind === "outputs") {
        groups = roundRobin(target.playing, Math.min(3, target.playing.length))
                 .map(function (group) { return "out" + rangify(group); });
      } else {
        groups = stripThirds(target.name, target.count, target.reversed,
                             Math.min(3, target.count));
      }
      return groups.map(function (selector, i) {
        return selector + " colour=" + colours[i] + ": flash speed=" + speed +
               " flashes=1 window=0.5" + (i ? " phase=" + [0, 0.33, 0.67][i] : "");
      });
    },
    reads: function (ch, fx) {
      var mood = toneBack(PARTY_FIRST, ch.colour);
      if (fx.speed === undefined || fx.flashes !== "1" || mood === null) return null;
      return {pace: unlerp(Number(fx.speed), 1, 4), mood: mood};
    },
    effect: "flash"
  },
];

function lookNamed(name) {
  return LOOKS.filter(function (l) { return l.name === name; })[0] || null;
}

// A flash entry is Emergency where it flashes in threes and Party where it
// flashes singly; the other effects each belong to one look
function lookForEntry(effect, fx) {
  if (effect === "flash") return fx.flashes === "3" ? lookNamed("Emergency")
                               : fx.flashes === "1" ? lookNamed("Party") : null;
  var found = LOOKS.filter(function (l) { return l.effect === effect; });
  return found[0] || null;
}

// ---- what a look looks like on the lights that play it --------------------------

// A look's colour at one place in a run: the ends of the run are the ends of the
// look, so however many lights are playing, the first and the last are the palette's
// own first and last rather than stopping short of it
function spreadColour(look, at, many) {
  if (!look) return "#e4e0d9";
  if (many < 2) return look.strip[0];
  var last = look.strip.length - 1;
  return look.strip[Math.round(at * last / (many - 1))];
}

// A strip's run in the look's colours, drawn on its own wire so its height stays
// put whether there are six LEDs or a hundred
function lampsPreview(look, count, reversed) {
  // A light is one size, always. A run too long for one row turns back on itself,
  // the way a strip is laid in a case: every other row fills backwards, so the
  // lights stay in the order the chain runs. Three rows, an odd number, so a run
  // that carries on ends at the right and reads straight into what is said there
  var SIZE = 11;
  var GAP = 2.5;
  var PER_ROW = 25;
  var ROWS = 3;
  var EDGE = 10;           // room at each side for the turns, the tails and the beads
  var TAIL = 6;            // how far a tail runs past the last light
  var SAID = 5;            // lights the last row gives up so 'and more' has its room
  // A run that carries on stops short on its last row rather than running to the
  // edge, so the words sit inside the same width and nothing shrinks as a strip
  // passes the length that can be drawn
  var most = count > PER_ROW * ROWS ? PER_ROW * ROWS - SAID : PER_ROW * ROWS;
  var many = Math.min(count, most);
  var rows = Math.ceil(many / PER_ROW);
  var across = Math.min(many, PER_ROW);
  var wide = across * SIZE + (across - 1) * GAP;
  var pitch = SIZE + GAP * 2;
  var high = rows * pitch - GAP * 2 + 2;

  function place(i) {
    var row = Math.floor(i / PER_ROW);
    var col = i % PER_ROW;
    if (row % 2) col = PER_ROW - 1 - col;
    return {x: EDGE + col * (SIZE + GAP), y: row * pitch + 1, row: row};
  }
  function middleOf(row) { return row * pitch + 1 + SIZE / 2; }

  var cells = [];

  // Where the run doubles back, drawn as the loop of wire it is
  for (var r = 0; r < rows - 1; r++) {
    var atRight = r % 2 === 0;
    var x = atRight ? EDGE + wide : EDGE;
    var bulge = atRight ? x + EDGE : x - EDGE;
    cells.push("<path d='M" + x + " " + middleOf(r) + " C" + bulge + " " + middleOf(r) +
               " " + bulge + " " + middleOf(r + 1) + " " + x + " " + middleOf(r + 1) +
               "' fill='none' stroke='#c9c3b9' stroke-width='1.8'/>");
  }

  // Where it begins: a lead in, with a bead on the end of it
  var first = place(0);
  cells.push("<path d='M0 " + middleOf(0) + " L" + first.x + " " + middleOf(0) +
             "' stroke='#c9c3b9' stroke-width='1.8' fill='none'/>");
  cells.push("<rect x='0' y='" + (middleOf(0) - 3.4) + "' width='4.6' height='6.8' " +
             "rx='1.4' fill='#8f8a81'/>");

  for (var i = 0; i < many; i++) {
    var at = reversed ? many - 1 - i : i;
    var colour = spreadColour(look, at, many);
    var spot = place(i);
    cells.push("<rect x='" + spot.x + "' y='" + spot.y + "' width='" + SIZE +
               "' height='" + SIZE + "' rx='2.4' fill='" + colour +
               "' stroke='rgba(0,0,0,.12)' stroke-width='0.6'/>");
  }

  var full = EDGE * 2 + wide;
  // Where it ends: carrying on towards what is said about the rest, or stopping
  // in a bead of its own where the whole run is drawn
  var last = place(many - 1);
  var lastY = middleOf(last.row);
  var goingRight = last.row % 2 === 0;
  var from = goingRight ? last.x + SIZE : last.x;
  var to = from + (goingRight ? TAIL : -TAIL);
  cells.push("<path d='M" + from + " " + lastY + " L" + to + " " + lastY +
             "' stroke='#c9c3b9' stroke-width='1.8' fill='none'/>");
  if (count <= most) {
    cells.push("<circle cx='" + to + "' cy='" + lastY + "' r='2.4' fill='#fff' " +
               "stroke='#a9a49b' stroke-width='1.6'/>");
  } else {
    var ended = place(many - 1);
    cells.push("<text x='" + (ended.x + SIZE + TAIL + 4) + "' y='" +
               (middleOf(rows - 1) + 3.5) + "' font-size='10' font-family='system-ui' " +
               "fill='#8a8378'>and " + (count - most) + " more</text>");
  }

  var box = document.createElement("div");
  box.style.lineHeight = "0";
  // The drawing grows into whatever the row has spare, up to a point: a run of six
  // blown up to the width of a run of a hundred would say the wrong thing about it
  box.style.flex = "1 1 " + full + "px";
  box.style.maxWidth = Math.round(full * 1.8) + "px";
  box.innerHTML = "<svg width='100%' height='" + high + "' viewBox='0 0 " +
                  full + " " + high + "' preserveAspectRatio='xMinYMid meet'>" +
                  cells.join("") + "</svg>";
  return box;
}

// The board's own outputs: only seven, so they are drawn large enough to be lamps
// rather than beads, and numbered as the board numbers them, which is what an entry
// in the file names
function outputsPreview(look, reversed) {
  // The effect is handed to the outputs the file names, one colour each in the order
  // it names them, so an output left out gives its place up and one dragged along
  // takes a different colour without any of them moving on the board
  var playing = state.lampOrder.filter(function (n) {
    return state.lampsOff.indexOf(n) < 0;
  });
  var box = document.createElement("div");
  box.className = "lamps";

  state.lampOrder.forEach(function (which, i) {
    var off = state.lampsOff.indexOf(which) >= 0;
    var slot = playing.indexOf(which);
    var at = reversed ? playing.length - 1 - slot : slot;
    var colour = look && slot >= 0 ? look.strip[at % look.strip.length] : "#e4e0d9";

    var lamp = document.createElement("button");
    lamp.className = "lamp" + (off ? " off" : "");
    lamp.draggable = true;
    lamp.title = (off ? "out" + which + " is left out; tap to play it again"
                      : "tap to leave out" + which + " out") +
                 ", or drag it to where it sits in your build";
    var face = document.createElement("i");
    if (!off) face.style.background = colour;
    lamp.appendChild(face);
    var name = document.createElement("b");
    name.textContent = which;
    lamp.appendChild(name);

    {
      lamp.onclick = function () {
        var was = state.lampsOff.indexOf(which);
        if (was >= 0) state.lampsOff.splice(was, 1);
        else state.lampsOff.push(which);
        draw();
      };
      lamp.ondragstart = function (e) {
        carrying = i;
        lamp.classList.add("carried");
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", String(which));
      };
      lamp.ondragend = function () { carrying = null; draw(); };
      lamp.ondragover = function (e) {
        if (carrying === null || carrying === i) return;
        e.preventDefault();
        var mid = lamp.getBoundingClientRect();
        lamp.classList.add("landing");
        lamp.classList.toggle("after", e.clientX > mid.left + mid.width / 2);
      };
      lamp.ondragleave = function () { lamp.classList.remove("landing", "after"); };
      lamp.ondrop = function (e) {
        e.preventDefault();
        if (carrying === null || carrying === i) return;
        var mid = lamp.getBoundingClientRect();
        var to = i + (e.clientX > mid.left + mid.width / 2 ? 1 : 0);
        var moved = state.lampOrder.splice(carrying, 1)[0];
        state.lampOrder.splice(to > carrying ? to - 1 : to, 0, moved);
        carrying = null;
        draw();
      };
    }

    box.appendChild(lamp);
  });

  // Only worth offering once something has actually been moved or left out
  if (!asTheBoardHasThem()) {
    var back = document.createElement("button");
    back.className = "putback";
    back.textContent = "put them back";
    back.title = "one to seven, in the board's own order, none left out";
    back.onclick = function () {
      state.lampOrder = [1, 2, 3, 4, 5, 6, 7];
      state.lampsOff = [];
      draw();
    };
    box.appendChild(back);
  }
  return box;
}

var carrying = null;

function asTheBoardHasThem() {
  if (state.lampsOff.length) return false;
  return state.lampOrder.every(function (which, i) { return which === i + 1; });
}

// The outputs still playing, in the order they are to play: starting from the far
// end writes the same run backwards, which the board walks in the written order
function playingOutputs(body) {
  var on = body.lampOrder.filter(function (n) {
    return body.lampsOff.indexOf(n) < 0;
  });
  return body.reversed ? on.slice().reverse() : on;
}

// Which end a run starts from, drawn rather than worded: a light at the near end,
// and an arrow off it saying which way the effect travels
function directionToggle(holder, onChange) {
  var button = document.createElement("button");
  button.className = "way";
  button.title = holder.reversed ? "starting from the far end, running back"
                                 : "starting from the near end, running on";
  var arrow = holder.reversed
    ? "<rect x='19' y='2.5' width='8' height='8' rx='2' fill='currentColor'/>" +
      "<path d='M17 6.5 L11.5 6.5 M14 3.5 L11 6.5 L14 9.5' fill='none' " +
      "stroke='currentColor' stroke-width='1.8' stroke-linecap='round' " +
      "stroke-linejoin='round'/>"
    : "<rect x='1' y='2.5' width='8' height='8' rx='2' fill='currentColor'/>" +
      "<path d='M11 6.5 L16.5 6.5 M14 3.5 L17 6.5 L14 9.5' fill='none' " +
      "stroke='currentColor' stroke-width='1.8' stroke-linecap='round' " +
      "stroke-linejoin='round'/>";
  button.innerHTML = "<svg width='28' height='13' viewBox='0 0 28 13'>" + arrow + "</svg>";
  button.onclick = function () {
    holder.reversed = !holder.reversed;
    onChange();
  };
  return button;
}

// ---- the screen modules, drawn from the sizing drawings -------------------------

// The part is black on black, so the panel's machined edge and the driver's navy do
// the separating. An unlit screen sits at the grey a backlight leaves; around a
// picture it is the near-black a lit panel shows when told black, which a background
// setting would one day replace
var BOARD_INK = "#0a0a0a";
var PANEL_INK = "#000000";
var EMPTY_INK = "#2a2f33";
var GROUND_INK = "#0f1113";
var FRAME_INK = "#3d464c";
var FRAME_WIDE = 0.3;
var CHIN_INK = "#131f33";
var HOLE_INK = "#efece6";
var HOLE_EDGE = "#6d7379";
var NAME_INK = "#e8eef2";

// Both products in millimetres, from the sizing drawings. The panel corners are the
// alignment marks the panels are placed against, so they are the source of truth;
// the lit area is drawn equidistant from the board's exact middle, which is what the
// mounting is designed around. The holes are symmetric, so the chin and the printed
// name are what say which way up a module is
var MODULE = {
  "2.8": {board: [48, 88], body: [9.6, 75.2], tab: [4, 44, 88], tabRadius: 4,
          panel: [0.5, 9.4, 47.5, 74.54], lit: [43.2, 57.6]},
  "1.54": {board: [32, 56], body: [9.6, 43.2], tab: [4, 28, 56], tabRadius: 4,
           panel: [0.24, 9.615, 31.76, 43.335], lit: [27.7, 27.7]}
};

// The printed names, lifted from the supplied artwork, in their own units
var PER_MM = 2.835;
var PRINTED = {
  "2.8": {d: 'M72.585,28.824v1.577h-5.307v-1.398l1.25-.952c.793-.605,2.093-1.567,2.093-2.439,0-.388-.258-.665-.635-.665s-.754.277-.754.853h-1.835c.04-1.497,1.131-2.439,2.628-2.439,1.429,0,2.47.883,2.47,2.152,0,1.438-1.428,2.42-2.241,2.976l-.496.337h2.827Z M75.929,29.32c0,.685-.525,1.181-1.259,1.181s-1.26-.496-1.26-1.181.525-1.181,1.26-1.181,1.259.496,1.259,1.181Z M82.506,28.387c0,1.23-1.121,2.113-2.877,2.113s-2.876-.883-2.876-2.113c0-.783.446-1.339,1.22-1.646-.595-.308-.932-.812-.932-1.478,0-1.131,1.001-1.904,2.588-1.904s2.589.773,2.589,1.904c0,.675-.337,1.181-.942,1.478.784.308,1.23.863,1.23,1.646ZM80.561,28.209c0-.506-.367-.822-.933-.822s-.932.316-.932.822c0,.517.367.844.932.844s.933-.327.933-.844ZM78.767,25.502c0,.456.337.754.862.754s.863-.298.863-.754c0-.477-.337-.773-.863-.773s-.862.297-.862.773Z M85.682,23.459l-1.062,2.886h-1.438l.437-2.886h2.063ZM88.369,23.459l-1.062,2.886h-1.438l.437-2.886h2.062Z M97.318,28.616v1.785h-4.761v-6.942h2.023v5.157h2.737Z M101.258,30.501c-2.133,0-3.67-1.498-3.67-3.571s1.537-3.57,3.67-3.57c1.934,0,3.392,1.229,3.61,3.016h-2.073c-.179-.675-.754-1.161-1.537-1.161-.942,0-1.607.715-1.607,1.706,0,1.002.665,1.726,1.607,1.726.773,0,1.349-.485,1.537-1.16h2.073c-.219,1.775-1.677,3.016-3.61,3.016Z M112.091,26.929c0,2.014-1.498,3.472-3.57,3.472h-2.768v-6.942h2.768c2.072,0,3.57,1.458,3.57,3.471ZM110.027,26.92c0-.972-.645-1.676-1.527-1.676h-.724v3.372h.724c.883,0,1.527-.714,1.527-1.696Z', x: 21.614, y: 249.80300000000003},
  "1.54": {d: 'M44.498,23.459v6.942h-1.904v-5.366h-1.319v-1.576h3.224Z M48.109,29.32c0,.685-.525,1.181-1.259,1.181s-1.26-.496-1.26-1.181.526-1.181,1.26-1.181,1.259.496,1.259,1.181Z M54.24,28.06c0,1.418-1.15,2.44-2.737,2.44-1.448,0-2.559-.942-2.648-2.252h1.904c.089.348.377.605.744.605.426,0,.793-.357.793-.923,0-.525-.328-.883-.793-.883-.327,0-.585.179-.724.546h-1.795l.595-4.136h4.324v1.576h-3.025l-.159,1.27c.327-.356.813-.564,1.438-.564,1.319,0,2.083.972,2.083,2.32Z M60.947,29.053h-1.051v1.349h-1.904v-1.349h-2.985v-1.389l2.608-4.205h2.281v4.017h1.051v1.577ZM56.801,27.475h1.19l.01-1.944-1.2,1.944Z M64.073,23.459l-1.061,2.886h-1.438l.437-2.886h2.063ZM66.761,23.459l-1.062,2.886h-1.438l.437-2.886h2.063Z M75.71,28.616v1.785h-4.761v-6.942h2.023v5.157h2.738Z M79.649,30.501c-2.132,0-3.67-1.498-3.67-3.571s1.538-3.57,3.67-3.57c1.934,0,3.392,1.229,3.61,3.016h-2.073c-.178-.675-.753-1.161-1.537-1.161-.942,0-1.607.715-1.607,1.706,0,1.002.665,1.726,1.607,1.726.773,0,1.349-.485,1.537-1.16h2.073c-.218,1.775-1.676,3.016-3.61,3.016Z M90.482,26.929c0,2.014-1.498,3.472-3.57,3.472h-2.767v-6.942h2.767c2.073,0,3.57,1.458,3.57,3.471ZM88.419,26.92c0-.972-.645-1.676-1.527-1.676h-.724v3.372h.724c.883,0,1.527-.714,1.527-1.696Z', x: 20.48, y: 159.09400000000002}
};

// What each size measures in pixels, which is what a picture is sized against:
// the board draws a picture at its own size, centred, and never scales it
var PANEL_PX = {"2.8": [240, 320], "1.54": [240, 240]};

var DRAWN = 210;

function svgTag(name, attrs, inner) {
  var out = "<" + name;
  Object.keys(attrs).forEach(function (key) { out += " " + key + "='" + attrs[key] + "'"; });
  return inner === undefined ? out + "/>" : out + ">" + inner + "</" + name + ">";
}

// A tab is rounded where it sticks out and square where it meets the body
function tabPath(x0, x1, near, far, radius) {
  var edge = far < near ? far + radius : far - radius;
  return "M" + x0 + " " + near +
         " L" + x0 + " " + edge +
         " Q" + x0 + " " + far + " " + (x0 + radius) + " " + far +
         " L" + (x1 - radius) + " " + far +
         " Q" + x1 + " " + far + " " + x1 + " " + edge +
         " L" + x1 + " " + near + " Z";
}

// The module as it is mounted. A turn turns the whole thing and the picture is put
// back upright inside it, which is what a reader sees looking at a mounted screen
function panelPreview(screen) {
  var made = MODULE[screen.size] || MODULE["2.8"];
  var turn = Number(screen.turn || 0);
  var quarter = turn % 180 === 90;

  var boardW = made.board[0];
  var boardH = made.board[1];
  var extent = Math.max(boardW, boardH);
  var left = (extent - boardW) / 2;
  var bottom = (extent - boardH) / 2;
  function up(y) { return extent - bottom - y; }

  var parts = [];

  parts.push(svgTag("rect", {x: left, y: up(made.body[1]), width: boardW,
                             height: made.body[1] - made.body[0], fill: BOARD_INK}));
  parts.push(svgTag("path", {d: tabPath(left + made.tab[0], left + made.tab[1],
                                        up(made.body[1]), up(made.tab[2]), made.tabRadius),
                             fill: BOARD_INK}));
  parts.push(svgTag("path", {d: tabPath(left + made.tab[0], left + made.tab[1],
                                        up(made.body[0]), up(boardH - made.tab[2]),
                                        made.tabRadius), fill: BOARD_INK}));

  [[8, 5], [16, 3.2], [24, 5], [32, 3.2], [40, 5]].forEach(function (hole) {
    if (hole[0] > boardW - 4) return;      // the small panel has three, not five
    [4, boardH - 4].forEach(function (y) {
      parts.push(svgTag("circle", {cx: left + hole[0], cy: up(y), r: hole[1] / 2,
                                   fill: HOLE_INK, stroke: HOLE_EDGE,
                                   "stroke-width": 0.3}));
    });
  });

  parts.push(svgTag("rect", {x: left + made.panel[0], y: up(made.panel[3]),
                             width: made.panel[2] - made.panel[0],
                             height: made.panel[3] - made.panel[1], fill: PANEL_INK,
                             stroke: FRAME_INK, "stroke-width": FRAME_WIDE}));

  var litW = made.lit[0];
  var litH = made.lit[1];
  var litX = left + boardW / 2 - litW / 2;
  var litY = up(boardH / 2) - litH / 2;
  var art = screen.shows && screen.shows !== "keep" ? mediaArt(screen.shows) : null;

  parts.push(svgTag("rect", {x: litX, y: litY, width: litW, height: litH,
                             fill: art ? GROUND_INK : EMPTY_INK}));
  parts.push(svgTag("rect", {x: litX - 0.4, y: litY + litH, width: litW + 0.8,
                             height: Math.max(0, up(made.panel[1]) - (litY + litH) - 0.4),
                             fill: CHIN_INK}));

  if (screen.shows === "keep") {
    parts.push(svgTag("text", {x: litX + litW / 2, y: litY + litH / 2 + 1.4,
                               "text-anchor": "middle", fill: "#8b959b",
                               "font-size": 4, "font-family": "system-ui"}, "as it is"));
  } else if (art) {
    // Drawn over the module as a plain img, since the browser plays every kind of
    // gif properly there where an image inside svg drops delta frames
  } else if (screen.shows) {
    parts.push(svgTag("text", {x: litX + litW / 2, y: litY + litH / 2 + 1.4,
                               "text-anchor": "middle", fill: "#8b959b",
                               "font-size": 4, "font-family": "system-ui"},
                      "on the board"));
  } else {
    parts.push(svgTag("text", {x: litX + litW / 2, y: litY + litH / 2 + 1.4,
                               "text-anchor": "middle", fill: "#8b959b",
                               "font-size": 4, "font-family": "system-ui"}, "no picture"));
  }

  var name = PRINTED[screen.size] || PRINTED["2.8"];
  parts.push("<g transform='translate(" + (left - name.x / PER_MM) + " " +
             (extent - bottom - name.y / PER_MM) + ") scale(" + (1 / PER_MM) + ")' " +
             "fill='" + NAME_INK + "'>" + svgTag("path", {d: name.d}) + "</g>");

  var holder = document.createElement("div");
  holder.className = "holder";
  holder.innerHTML =
    "<svg width='" + DRAWN + "' height='" + DRAWN + "' viewBox='0 0 " + extent + " " + extent +
    "'><g transform='rotate(" + turn + " " + (extent / 2) + " " + (extent / 2) + ")'>" +
    parts.join("") + "</g></svg>";

  // The picture as the board will draw it: its own pixels, centred, cropped by the
  // lit window, black around it. The window sits on the drawing's exact centre, so
  // a turned module swaps its width and height and nothing else moves; the picture
  // itself stays upright, which is what a viewer of a mounted screen sees
  if (art) {
    var px = PANEL_PX[screen.size] || PANEL_PX["2.8"];
    var scale = (DRAWN / extent) * (litW / px[0]);
    var windowW = (quarter ? litH : litW) * (DRAWN / extent);
    var windowH = (quarter ? litW : litH) * (DRAWN / extent);
    var pane = document.createElement("div");
    pane.style.cssText = "position:absolute;overflow:hidden;" +
      "left:" + ((DRAWN - windowW) / 2) + "px;top:" + ((DRAWN - windowH) / 2) + "px;" +
      "width:" + windowW + "px;height:" + windowH + "px;" +
      "display:flex;align-items:center;justify-content:center";
    var img = document.createElement("img");
    img.src = art.url;
    img.style.cssText = "flex:none;width:" + (art.w * scale) + "px;height:" +
                        (art.h * scale) + "px";
    pane.appendChild(img);
    holder.style.position = "relative";
    holder.appendChild(pane);
  }
  return holder;
}

// ---- state ----------------------------------------------------------------------

var state = {
  // The drive
  dirHandle: null, fileHandle: null,
  media: [],            // {name, kind: "gif"|"image"|"folder", handle, thumbHandle}
  sounds: [],           // wav names on the drive
  soundInfo: {},        // name -> {seconds, bars} read from the file, or null
  art: {},              // name -> {url, ratio} for drawing on the panels
  // The board, true whatever the scene
  straight: true,       // the board plays a save at once (reload=auto)
  boardResidue: [],     // board settings this page does not manage, kept as written
  screens: {},          // letter -> {there, size, turn, carried, pingpong, hold, fps,
                        //            shows, kept} with shows and kept per scene
  strips: {},           // id -> {leds, reversed, look, pace, mood} with the look,
                        //       pace and mood per scene
  sound: null, soundLoop: false, soundKept: null,
  stripsAtStart: [],
  // The scene being edited: its fields live at the top level while it is current
  look: null, pace: 0.5, mood: 0.5, reversed: false,
  lampsOff: [], lampOrder: [1, 2, 3, 4, 5, 6, 7],
  kept: [],             // this scene's lines no control stands for, written verbatim
  at: -1, always: {body: null}, scenes: [],
  recognised: {look: null, exact: true, any: false},
  scanned: false,
};

SCREENS.forEach(function (letter) {
  state.screens[letter] = {there: false, size: "2.8", turn: 0, carried: "",
                           pingpong: false, hold: "", fps: 5, shows: null, kept: null};
});
STRIP_IDS.forEach(function (id) {
  state.strips[id] = {leds: null, reversed: false, look: null, pace: 0.5, mood: 0.5};
});

// A scene holds only what can differ between them: the look on the outputs, what
// each strip plays, and what each screen shows. Lengths, sizes, turns and the sound
// are facts about the board, so they sit outside the tabs and are not captured here
function capture() {
  var body = {
    look: state.look, pace: state.pace, mood: state.mood, reversed: state.reversed,
    lampsOff: state.lampsOff.slice(), lampOrder: state.lampOrder.slice(),
    kept: state.kept.slice(), strips: {}, screens: {}
  };
  STRIP_IDS.forEach(function (id) {
    var strip = state.strips[id];
    body.strips[id] = {look: strip.look, pace: strip.pace, mood: strip.mood};
  });
  SCREENS.forEach(function (letter) {
    var screen = state.screens[letter];
    body.screens[letter] = {shows: screen.shows, kept: screen.kept};
  });
  return body;
}

function apply(body) {
  state.look = body.look;
  state.pace = body.pace;
  state.mood = body.mood;
  state.reversed = body.reversed;
  state.lampsOff = body.lampsOff.slice();
  state.lampOrder = body.lampOrder.slice();
  state.kept = body.kept.slice();
  STRIP_IDS.forEach(function (id) {
    var strip = state.strips[id];
    var was = body.strips[id];
    strip.look = was.look;
    strip.pace = was.pace;
    strip.mood = was.mood;
  });
  SCREENS.forEach(function (letter) {
    var screen = state.screens[letter];
    var was = body.screens[letter];
    screen.shows = was.shows;
    screen.kept = was.kept;
  });
}

function copyBody(body) { return JSON.parse(JSON.stringify(body)); }

// A scene with nothing in it yet, which is what the always-on tab is left holding
// once its content has been carried into the first scene
function blankBody() {
  var body = {look: null, pace: 0.5, mood: 0.5, reversed: false, lampsOff: [],
              lampOrder: [1, 2, 3, 4, 5, 6, 7], kept: [], strips: {}, screens: {}};
  STRIP_IDS.forEach(function (id) {
    body.strips[id] = {look: null, pace: 0.5, mood: 0.5};
  });
  SCREENS.forEach(function (letter) {
    body.screens[letter] = {shows: null, kept: null};
  });
  return body;
}

state.always.body = blankBody();

// -1 is the tab everything starts in: the entries above every heading, which play
// all the way through
function slotAt(which) { return which < 0 ? state.always : state.scenes[which]; }

function store() { slotAt(state.at).body = capture(); }

function switchTo(which) {
  store();
  state.at = which;
  apply(slotAt(which).body);
  draw();
}

// The first scene carries the board as it stands, since someone pressing plus wants
// a sequence rather than a backdrop, and losing their work to get one is no answer.
// Every later scene copies the one before it, so a small change is a small edit
function addScene() {
  store();
  var made;
  if (!state.scenes.length) {
    made = {name: "Scene 1", seconds: 10, restart: false, body: capture()};
    state.always.body = blankBody();
  } else {
    var before = state.scenes[state.scenes.length - 1];
    made = {name: "Scene " + (state.scenes.length + 1), seconds: before.seconds,
            restart: before.restart, body: copyBody(before.body)};
  }
  state.scenes.push(made);
  state.at = state.scenes.length - 1;
  apply(made.body);
  draw();
}

function removeScene(which) {
  store();
  var gone = state.scenes.splice(which, 1)[0];
  // Taking the last scene away leaves nothing playing, so its content comes back to
  // the tab that plays all the way through, which is where the page started
  if (!state.scenes.length && !hasContent(state.always.body))
    state.always.body = gone.body;
  state.at = state.scenes.length ? Math.min(which, state.scenes.length - 1) : -1;
  apply(slotAt(state.at).body);
  draw();
}

function hasContent(body) {
  if (body.look || body.kept.length) return true;
  var found = false;
  STRIP_IDS.forEach(function (id) { if (body.strips[id].look) found = true; });
  SCREENS.forEach(function (l) { if (body.screens[l].shows) found = true; });
  return found;
}

// ---- writing the file ------------------------------------------------------------

function boardLine() {
  var tokens = state.boardResidue.slice();
  if (state.straight) tokens.push("reload=auto");
  var bodies = allBodies();
  SCREENS.forEach(function (letter) {
    var screen = state.screens[letter];
    var used = screen.there && bodies.some(function (b) { return b.screens[letter].shows; });
    if (used && screen.size) tokens.push("screen" + letter.toLowerCase() + "=" + screen.size);
  });
  STRIP_IDS.forEach(function (id) {
    if (state.strips[id].leds) tokens.push(id.toLowerCase() + "=" + state.strips[id].leds);
  });
  return tokens.length ? "board: " + tokens.join(" ") : "";
}

function allBodies() {
  return [state.always.body].concat(state.scenes.map(function (s) { return s.body; }));
}

function soundLine() {
  if (state.sound)
    return "audio: wav file=" + quoted(state.sound) +
           (state.soundLoop ? " loop=true" : "");
  return state.soundKept;
}

function screenEntry(letter, body) {
  var screen = state.screens[letter];
  var shows = body.screens[letter].shows;
  if (!screen.there || !shows) return null;
  if (shows === "keep") return body.screens[letter].kept;
  var media = mediaNamed(shows);
  var kind = media ? media.kind
           : /\\.gif$/i.test(shows) ? "gif"
           : /\\.(png|jpe?g)$/i.test(shows) ? "image" : "folder";
  var selector = "screen" + letter;
  if (screen.carried) selector += " " + screen.carried;
  if (Number(screen.turn)) selector += " rotation=" + screen.turn;
  var extras = "";
  if (kind !== "image") {
    if (screen.pingpong) extras += " ping_pong=true";
    if (screen.hold) extras += " hold=" + screen.hold;
  }
  if (kind === "folder")
    return selector + ": sequence folder=" + quoted(shows) + " fps=" + screen.fps + extras;
  if (kind === "gif")
    return selector + ": gif file=" + quoted(shows) + extras;
  return selector + ": image file=" + quoted(shows);
}

// What one scene writes: its screens, its outputs, its strips, then whatever it
// carries word for word, in that order
function entriesFrom(body) {
  var lines = [];
  SCREENS.forEach(function (letter) {
    var line = screenEntry(letter, body);
    if (line) lines.push(line);
  });

  var look = lookNamed(body.look);
  if (look) {
    var playing = playingOutputs(body);
    if (playing.length) {
      var target = {kind: "outputs", selector: "out" + rangify(playing),
                    count: playing.length, playing: playing};
      lines = lines.concat(look.entries(target, body.pace, body.mood));
    }
  }

  STRIP_IDS.forEach(function (id) {
    var strip = state.strips[id];
    var chosen = lookNamed(body.strips[id].look);
    if (!strip.leds || !chosen || !chosen.spans) return;
    var target = {kind: "strip", name: id,
                  selector: strip.reversed ? id + strip.leds + "-1" : id,
                  count: strip.leds, reversed: strip.reversed};
    lines = lines.concat(chosen.entries(target, body.strips[id].pace,
                                        body.strips[id].mood));
  });

  return lines.concat(body.kept);
}

function currentText() {
  store();
  var lines = [];
  var board = boardLine();
  if (board) lines.push(board);
  var sound = soundLine();
  if (sound) lines.push(sound);

  var always = entriesFrom(state.always.body);
  if (always.length) {
    if (lines.length) lines.push("");
    lines = lines.concat(always);
  }

  state.scenes.forEach(function (scene) {
    lines.push("");
    lines.push("[" + (scene.name.trim() || "Scene") + ": " + scene.seconds + "s" +
               (scene.restart ? " restart" : "") + "]");
    lines = lines.concat(entriesFrom(scene.body));
  });

  return HEADER + lines.join("\\n") + "\\n";
}

// ---- reading a file back ---------------------------------------------------------
// Every recogniser proves itself: it turns a line back into slider positions, then
// regenerates and only adopts the reading where the file comes out identical. A
// line that fails is kept word for word, so nothing a hand wrote is redrawn.

// One entry line taken apart: the selector word, the settings either side of the
// colon as maps, and the channel settings' original text for carrying
function parseEntry(line) {
  var at = line.indexOf(":");
  if (at < 0) return null;
  var left = line.slice(0, at).match(/"[^"]*"|\\S+/g) || [];
  var right = line.slice(at + 1).match(/"[^"]*"|\\S+/g) || [];
  if (!left.length || !right.length) return null;
  var ch = {};
  var chText = [];
  for (var i = 1; i < left.length; i++) {
    var pair = left[i].split("=");
    if (pair.length !== 2) return null;
    ch[pair[0].toLowerCase()] = pair[1].replace(/^"|"$/g, "");
    chText.push(left[i]);
  }
  var fx = {};
  for (var j = 1; j < right.length; j++) {
    var set = right[j].split("=");
    if (set.length !== 2) return null;
    fx[set[0].toLowerCase()] = set[1].replace(/^"|"$/g, "");
  }
  return {selector: left[0], ch: ch, chText: chText,
          effect: right[0].toLowerCase(), fx: fx};
}

// The outputs an out selector names, read into the model's terms: the listed order
// is the play order, a wholly descending list is the reversed toggle, and whatever
// is not listed is left out
function outputsTarget(selector) {
  var digits = selector.slice(3);
  var listed = digits === "" ? null : expandNumbers(digits);
  if (!listed || !listed.length || listed.length > 7) return null;
  for (var i = 0; i < listed.length; i++) {
    if (listed[i] < 1 || listed[i] > 7 || listed.indexOf(listed[i]) !== i) return null;
  }
  var reversed = listed.length > 1 && listed.every(function (n, i) {
    return i === 0 || n === listed[i - 1] - 1;
  });
  var order = reversed ? listed.slice().reverse() : listed.slice();
  for (var n = 1; n <= 7; n++) if (order.indexOf(n) < 0) order.push(n);
  var off = order.filter(function (n) { return listed.indexOf(n) < 0; });
  return {order: order, off: off, reversed: reversed, playing: listed.slice(),
          count: listed.length};
}

// Tries the looks against a run of entry lines; on success the body takes the
// reading and the consumed count comes back, else zero and the line will be kept
function recogniseOutputs(parsedLines, start, body) {
  var head = parsedLines[start];
  if (!/^out[\\d,-]*$/.test(head.selector)) return 0;
  var look = lookForEntry(head.effect, head.fx);
  if (!look) return 0;

  var target;
  if (!look.spans) {
    // The banks and the quiet rest are the playing outputs dealt out in order,
    // so the order comes back by reading the lines in theirs
    var told = [];
    for (var f = start; f < parsedLines.length && f < start + 3; f++) {
      var row = parsedLines[f];
      if (!/^out[\\d,-]+$/.test(row.selector)) break;
      var fits = f === start || row.effect === "none" ||
                 (look.name === "Emergency" && row.effect === head.effect);
      if (!fits) break;
      var found = expandNumbers(row.selector.slice(3));
      if (!found) break;
      told = told.concat(found);
      if (row.effect === "none") break;
    }
    if (!told.length || told.length > 7) return 0;
    target = {kind: "outputs", playing: told, count: told.length};
  } else if (look.name === "Party") {
    // Party writes up to three groups, one colour each in turn, so the play order
    // comes back by interleaving the groups the way they were dealt out
    var groups = [];
    for (var g = start; g < parsedLines.length && groups.length < 3; g++) {
      var one = parsedLines[g];
      if (one.effect !== "flash" || !/^out[\\d,-]+$/.test(one.selector)) break;
      var numbers = expandNumbers(one.selector.slice(3));
      if (!numbers) break;
      groups.push(numbers);
    }
    var playing = [];
    for (var slot = 0; groups.some(function (grp) { return slot < grp.length; }); slot++) {
      groups.forEach(function (grp) { if (slot < grp.length) playing.push(grp[slot]); });
    }
    if (!playing.length || playing.length > 7) return 0;
    target = {kind: "outputs", playing: playing, count: playing.length};
  } else if (look.spans) {
    var read = outputsTarget(head.selector);
    if (!read) return 0;
    target = {kind: "outputs", selector: "out" + rangify(read.playing),
              count: read.count, playing: read.playing};
  } else {
    target = {kind: "outputs"};
  }

  var pm = look.reads(head.ch, head.fx, target);
  if (!pm) return 0;
  var regen = look.entries(target, pm.pace, pm.mood);
  for (var i = 0; i < regen.length; i++) {
    var against = parsedLines[start + i];
    if (!against || against.line !== regen[i]) return 0;
  }

  body.look = look.name;
  body.pace = pm.pace;
  body.mood = pm.mood;
  var model = outputsTarget("out" + rangify(target.playing));
  body.reversed = model.reversed;
  body.lampOrder = model.order;
  body.lampsOff = model.off;
  return regen.length;
}

function recogniseStrip(parsedLines, start, body) {
  var head = parsedLines[start];
  var named = head.selector.match(/^(strip[lr])([\\d-]*)$/i);
  if (!named) return 0;
  var id = "strip" + named[1].slice(-1).toUpperCase();
  if (STRIP_IDS.indexOf(id) < 0 || body.strips[id].look) return 0;
  var count = Number(state.strips[id].leds);
  if (!count) return 0;

  // The bare name is the whole run; its full range written high end first is the
  // wiring direction; anything else is a sub-range this page does not manage
  var reversed;
  if (named[2] === "") reversed = false;
  else if (named[2] === count + "-1") reversed = true;
  else if (head.effect === "flash") reversed = null;   // Party writes thirds
  else return 0;

  var look = lookForEntry(head.effect, head.fx);
  if (!look || !look.spans) return 0;

  var tries = reversed === null ? [false, true] : [reversed];
  for (var t = 0; t < tries.length; t++) {
    var target = {kind: "strip", name: id,
                  selector: tries[t] ? id + count + "-1" : id,
                  count: count, reversed: tries[t]};
    var pm = look.reads(head.ch, head.fx, target);
    if (!pm) continue;
    var regen = look.entries(target, pm.pace, pm.mood);
    var matched = true;
    for (var i = 0; i < regen.length; i++) {
      var against = parsedLines[start + i];
      if (!against || against.line !== regen[i]) { matched = false; break; }
    }
    if (!matched) continue;
    state.strips[id].reversed = tries[t];
    body.strips[id] = {look: look.name, pace: pm.pace, mood: pm.mood};
    return regen.length;
  }
  return 0;
}

function recogniseScreen(parsed, body) {
  var named = parsed.selector.match(/^screen([ab])$/i);
  if (!named) return false;
  var letter = named[1].toUpperCase();
  if (SCREENS.indexOf(letter) < 0 || body.screens[letter].shows) return false;
  var screen = state.screens[letter];
  screen.there = true;

  var turn = 0;
  var carried = [];
  parsed.chText.forEach(function (token) {
    var spin = token.match(/^rotation=(\\d+)$/i);
    if (spin) turn = Number(spin[1]);
    else carried.push(token);
  });

  var name = null;
  var kind = null;
  if (parsed.effect === "gif" && parsed.fx.file) { name = parsed.fx.file; kind = "gif"; }
  else if (parsed.effect === "image" && parsed.fx.file) { name = parsed.fx.file; kind = "image"; }
  else if (parsed.effect === "sequence" && parsed.fx.folder) {
    name = parsed.fx.folder;
    kind = "folder";
  }
  if (name === null) return false;

  var was = {turn: screen.turn, carried: screen.carried, pingpong: screen.pingpong,
             hold: screen.hold, fps: screen.fps};
  screen.turn = turn;
  screen.carried = carried.join(" ");
  screen.pingpong = parsed.fx.ping_pong === "true";
  screen.hold = parsed.fx.hold || "";
  if (kind === "folder") screen.fps = Number(parsed.fx.fps) || 5;

  body.screens[letter].shows = name;
  if (screenEntry(letter, body) === parsed.line) return true;

  // The reading did not reproduce the line, so the line is kept and the screen's
  // settings go back to whatever an earlier entry established
  body.screens[letter].shows = null;
  screen.turn = was.turn;
  screen.carried = was.carried;
  screen.pingpong = was.pingpong;
  screen.hold = was.hold;
  screen.fps = was.fps;
  return false;
}

// One scene's raw entry lines into its body: recognised runs are adopted, a screen
// line that resists becomes that screen's keep choice, and the rest ride verbatim
function absorbEntries(rawLines, body) {
  var parsedLines = rawLines.map(function (line) {
    var parsed = parseEntry(line.trim());
    if (parsed) parsed.line = line.trim();
    return parsed || {line: line.trim(), selector: "", effect: "", ch: {}, fx: {},
                      chText: []};
  });
  var at = 0;
  while (at < parsedLines.length) {
    var taken = 0;
    if (!body.look) taken = recogniseOutputs(parsedLines, at, body);
    if (!taken) taken = recogniseStrip(parsedLines, at, body);
    if (!taken && recogniseScreen(parsedLines[at], body)) taken = 1;
    if (!taken) {
      var screenish = parsedLines[at].selector.match(/^screen([ab])\\b/i);
      var letter = screenish ? screenish[1].toUpperCase() : null;
      if (letter && SCREENS.indexOf(letter) >= 0 && !body.screens[letter].shows) {
        state.screens[letter].there = true;
        body.screens[letter].kept = parsedLines[at].line;
        body.screens[letter].shows = "keep";
      } else {
        body.kept.push(parsedLines[at].line);
      }
      taken = 1;
    }
    at += taken;
  }
}

function absorbText(text) {
  state.straight = true;
  state.boardResidue = [];
  state.sound = null;
  state.soundLoop = false;
  state.soundKept = null;
  SCREENS.forEach(function (letter) {
    state.screens[letter] = {there: false, size: "2.8", turn: 0, carried: "",
                             pingpong: false, hold: "", fps: 5, shows: null, kept: null};
  });
  STRIP_IDS.forEach(function (id) {
    state.strips[id] = {leds: null, reversed: false, look: null, pace: 0.5, mood: 0.5};
  });
  state.always = {body: blankBody()};
  state.scenes = [];
  state.at = -1;

  // First pass sorts the lines into buckets, since the board line has to land
  // before the entries can be read against declared lengths
  var buckets = [{scene: null, lines: []}];
  var sawStraight = false;
  text.split("\\n").forEach(function (raw) {
    var line = raw.split("#")[0].trim();
    if (line === "") return;

    var heading = line.match(/^\\[\\s*([^:\\]]*?)\\s*(?::([^\\]]*))?\\]$/);
    if (heading) {
      var seconds = 10;
      var restart = false;
      (heading[2] || "").split(/\\s+/).forEach(function (word) {
        var time = word.match(/^(\\d+(?:\\.\\d+)?)s$/i);
        if (time) seconds = Number(time[1]);
        else if (word.toLowerCase() === "restart") restart = true;
      });
      buckets.push({scene: {name: heading[1], seconds: seconds, restart: restart},
                    lines: []});
      return;
    }

    var board = line.match(/^board\\s*:\\s*(.*)$/i);
    if (board) {
      board[1].split(/\\s+/).forEach(function (token) {
        if (token === "") return;
        var reload = token.match(/^reload=(.+)$/i);
        var size = token.match(/^screen([ab])=(.+)$/i);
        var count = token.match(/^strip([lr])=(\\d+)$/i);
        if (reload) {
          state.straight = reload[1].toLowerCase() === "auto";
          sawStraight = true;
        } else if (size && SCREENS.indexOf(size[1].toUpperCase()) >= 0) {
          var screen = state.screens[size[1].toUpperCase()];
          screen.there = true;
          screen.size = size[2];
        } else if (count && STRIP_IDS.indexOf("strip" + count[1].toUpperCase()) >= 0) {
          state.strips["strip" + count[1].toUpperCase()].leds = Number(count[2]);
        } else {
          state.boardResidue.push(token);
        }
      });
      return;
    }

    var sound = line.match(/^audio\\b[^:]*:/i);
    if (sound && buckets.length === 1) {
      var parsed = parseEntry(line);
      if (parsed && parsed.effect === "wav" && parsed.fx.file &&
          !Object.keys(parsed.ch).length) {
        state.sound = parsed.fx.file;
        state.soundLoop = parsed.fx.loop === "true";
        if (soundLine() === line) return;
        state.sound = null;
        state.soundLoop = false;
      }
      state.soundKept = line;
      return;
    }

    buckets[buckets.length - 1].lines.push(line);
  });

  // A file that never says reload= leaves the board on manual, so a fresh save
  // should not quietly change that
  if (!sawStraight) state.straight = text.trim() === "";

  absorbEntries(buckets[0].lines, state.always.body);
  buckets.slice(1).forEach(function (bucket) {
    var body = blankBody();
    absorbEntries(bucket.lines, body);
    state.scenes.push({name: bucket.scene.name, seconds: bucket.scene.seconds,
                       restart: bucket.scene.restart, body: body});
  });

  state.stripsAtStart = STRIP_IDS.filter(function (id) {
    return state.strips[id].leds;
  });
  state.at = -1;
  apply(state.always.body);
  document.getElementById("straight").checked = state.straight;

  // What was made of the file, said once at the top: the look found, whether the
  // file is exactly what this page would write, and whether anything was readable
  var bodies = allBodies();
  var found = null;
  var any = false;
  bodies.forEach(function (body) {
    if (!found && body.look) found = body.look;
    if (hasContent(body)) any = true;
  });
  var keptCount = bodies.reduce(function (sum, body) {
    var here = body.kept.length;
    SCREENS.forEach(function (l) { if (body.screens[l].kept) here++; });
    return sum + here;
  }, 0);
  var exact = currentText().replace(/\\s+$/, "") === text.replace(/\\s+$/, "");
  state.recognised = {look: found, exact: exact, any: any, kept: keptCount,
                      empty: text.trim() === ""};
}

// ---- rendering -------------------------------------------------------------------

function bar(colours, className) {
  var strip = document.createElement("div");
  strip.className = className;
  colours.forEach(function (c) {
    var cell = document.createElement("span");
    cell.style.background = c;
    strip.appendChild(cell);
  });
  return strip;
}

function renderRecognised() {
  var box = document.getElementById("recognised");
  var found = state.recognised;
  if (!state.fileHandle || found.empty) {
    box.hidden = true;
    return;
  }
  box.hidden = false;
  if (found.look) {
    box.innerHTML = "The board is playing <b>" + found.look + "</b>" +
      (found.exact ? "" : "<span class='tag'>edited since</span>");
  } else if (found.kept) {
    box.innerHTML = "This drive's <b>effects.txt</b> was written some other way. " +
      "Its entries are kept as written; anything chosen here is added around them.";
  } else {
    box.innerHTML = "This drive's <b>effects.txt</b> plays nothing yet. " +
      "Pick a look below.";
  }
}

function renderScenes() {
  var box = document.getElementById("tabs");
  box.textContent = "";

  // One scene is what a file has before anyone asks for more, and a bar of one tab
  // says nothing, so it is not drawn until there is a choice to make
  if (state.scenes.length) {
    box.appendChild(sceneTab(-1, state.always, "Always on", "under every scene"));
    state.scenes.forEach(function (scene, i) {
      box.appendChild(sceneTab(i, scene, scene.name, scene.seconds + "s" +
                               (scene.restart ? ", from the start" : "")));
    });
  }

  var plus = document.createElement("button");
  plus.className = "plus";
  plus.innerHTML = "<svg width='11' height='11' viewBox='0 0 11 11'><path d='M5.5 1 " +
                   "L5.5 10 M1 5.5 L10 5.5' stroke='currentColor' stroke-width='1.8' " +
                   "stroke-linecap='round'/></svg>" +
                   (state.scenes.length ? "another scene" : "split into scenes");
  plus.title = state.scenes.length ? "Add another scene"
                                   : "Split this into scenes that take turns";
  plus.onclick = addScene;
  box.appendChild(plus);

  // The frame is what says these belong to the tab, so it appears with the tabs
  var frame = document.getElementById("sceneBody");
  frame.className = "scenebody" + (state.scenes.length ? " framed" : "");

  // Whether the tabs still sit on one row decides whether one of them can join the
  // frame below, so it is measured rather than guessed
  var tabs = box.querySelectorAll(".tab");
  var plusTop = box.querySelector(".plus").offsetTop;
  var wrapped = tabs.length > 1 &&
                (tabs[tabs.length - 1].offsetTop > tabs[0].offsetTop ||
                 plusTop > tabs[0].offsetTop);
  box.classList.toggle("wrapped", wrapped);
  if (wrapped && state.scenes.length) frame.classList.add("loose");
}

function sceneTab(which, slot, name, says) {
  var here = state.at === which;
  var body = here ? capture() : slot.body;
  var tab = document.createElement("button");
  tab.className = "tab" + (here ? " on" : "");
  tab.draggable = which >= 0;

  var swatch = document.createElement("div");
  swatch.className = "look";
  var look = lookNamed(body.look);
  if (look) look.strip.forEach(function (colour) {
    var cell = document.createElement("span");
    cell.style.background = colour;
    swatch.appendChild(cell);
  });
  tab.appendChild(swatch);

  var title = document.createElement("b");
  title.textContent = name;
  if (which >= 0) {
    var shut = document.createElement("span");
    shut.className = "shut";
    shut.textContent = "\\u00d7";
    shut.title = "Take this scene out";
    shut.onclick = function (e) { e.stopPropagation(); removeScene(which); };
    title.appendChild(shut);
  }
  tab.appendChild(title);

  var under = document.createElement("small");
  under.textContent = says;
  tab.appendChild(under);

  tab.onclick = function () { if (state.at !== which) switchTo(which); };

  if (which >= 0) {
    tab.ondragstart = function (e) {
      carriedTab = which;
      tab.classList.add("carried");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", String(which));
    };
    tab.ondragend = function () { carriedTab = null; draw(); };
    tab.ondragover = function (e) {
      if (carriedTab === null || carriedTab === which) return;
      e.preventDefault();
      tab.classList.add("landing");
    };
    tab.ondragleave = function () { tab.classList.remove("landing"); };
    tab.ondrop = function (e) {
      e.preventDefault();
      if (carriedTab === null || carriedTab === which) return;
      store();
      // The scene being edited is followed by identity, since moving any tab shifts
      // the numbers of the ones it passes
      var editing = state.at >= 0 ? state.scenes[state.at] : null;
      var moved = state.scenes.splice(carriedTab, 1)[0];
      state.scenes.splice(which, 0, moved);
      state.at = editing ? state.scenes.indexOf(editing) : -1;
      carriedTab = null;
      draw();
    };
  }
  return tab;
}

var carriedTab = null;

function renderSceneSettings() {
  var box = document.getElementById("sceneSettings");
  box.textContent = "";
  if (state.at < 0) return;
  var scene = state.scenes[state.at];

  var row = document.createElement("div");
  row.className = "sceneset";

  var name = document.createElement("input");
  name.type = "text";
  name.value = scene.name;
  name.title = "What this scene is called, which is its heading in the file";
  name.dataset.focus = "scene-name";
  name.oninput = function () {
    // The brackets and the colon are the heading's own punctuation
    scene.name = name.value.replace(/[\\[\\]:]/g, "");
    if (name.value !== scene.name) name.value = scene.name;
    renderScenes();
    renderPreview();
  };
  row.appendChild(name);

  var shows = document.createElement("span");
  shows.textContent = "shows for";
  row.appendChild(shows);

  var seconds = document.createElement("input");
  seconds.type = "number";
  seconds.min = 1;
  seconds.value = scene.seconds;
  seconds.dataset.focus = "scene-seconds";
  seconds.onchange = function () {
    scene.seconds = Math.max(1, Number(seconds.value) || 1);
    draw();
  };
  row.appendChild(seconds);

  var unit = document.createElement("span");
  unit.textContent = "seconds";
  row.appendChild(unit);

  var again = document.createElement("label");
  var tick = document.createElement("input");
  tick.type = "checkbox";
  tick.checked = scene.restart;
  tick.onchange = function () { scene.restart = tick.checked; draw(); };
  again.appendChild(tick);
  again.appendChild(document.createTextNode("from the start each turn"));
  again.title = "Its effects begin again every time the scene comes round";
  row.appendChild(again);

  box.appendChild(row);
}

// A look's name beside the settings it takes, which is what a scene chose as
// opposed to what is wired to the board
function tunedBlock(said, holder) {
  var wrap = document.createElement("div");
  wrap.className = "tuned";
  var who = document.createElement("div");
  who.className = "who";
  who.innerHTML = said;
  wrap.appendChild(who);
  wrap.appendChild(tuningFor(holder));
  return wrap;
}

function tuningFor(holder) {
  var look = lookNamed(holder.look);
  var box = document.createElement("div");
  box.className = "tuning";
  box.innerHTML =
    "<label>Pace</label><input type='range' min='0' max='1' step='0.01' value='" + holder.pace + "'>" +
    "<label>" + look.mood + "</label><input type='range' min='0' max='1' step='0.01' value='" + holder.mood + "'>";
  var inputs = box.querySelectorAll("input");
  // Only the file depends on a slider's value, so nothing is rebuilt under the
  // pointer and the drag keeps its grip
  inputs[0].oninput = function () { holder.pace = Number(inputs[0].value); renderPreview(); };
  inputs[1].oninput = function () { holder.mood = Number(inputs[1].value); renderPreview(); };
  return box;
}

function renderGallery() {
  var box = document.getElementById("gallery");
  box.textContent = "";
  // Nothing is a choice like any other, and belongs at the end where a reader has
  // seen what there is before being offered none of it
  LOOKS.concat([{name: null}]).forEach(function (look) {
    var card = document.createElement("div");
    var onOut = state.look === look.name;
    // The border says what the outputs play, and nothing else: the marks say the
    // strips for themselves
    card.className = "card" + (onOut ? " picked" : "") + (look.name ? "" : " nothing");
    card.appendChild(look.name ? bar(look.strip, "bar") : (function () {
      var blank = document.createElement("div");
      blank.className = "bar";
      return blank;
    })());

    var name = document.createElement("div");
    name.className = "name";
    name.appendChild(document.createTextNode(look.name || "Nothing"));

    var who = document.createElement("div");
    who.className = "who";
    STRIP_IDS.forEach(function (id) {
      var letter = id.slice(-1).toLowerCase();
      var strip = state.strips[id];
      var lit = strip.look === look.name && strip.leds && look.name;
      var mark = document.createElement("span");
      mark.textContent = letter.toUpperCase();
      var canPlay = strip.leds && (look.name === null || look.spans);
      mark.className = (lit ? "lit " + letter : "") + (canPlay ? "" : " off");
      mark.title = !strip.leds ? "say how many LEDs this strip has first"
                 : (look.name && !look.spans) ? "this look is shaped to the seven lamps"
                 : "play this on strip " + letter.toUpperCase();
      mark.onclick = function (event) {
        event.stopPropagation();
        if (!canPlay) return;
        strip.look = strip.look === look.name ? null : look.name;
        draw();
      };
      who.appendChild(mark);
    });
    name.appendChild(who);
    card.appendChild(name);

    card.onclick = function () { state.look = look.name; draw(); };
    box.appendChild(card);
  });
}

function renderOutputs() {
  var box = document.getElementById("outputs");
  box.textContent = "";
  var look = lookNamed(state.look);

  var head = document.createElement("div");
  head.className = "side-head";
  head.appendChild(directionToggle(state, draw));
  head.appendChild(outputsPreview(look, state.reversed));
  var out = state.lampsOff.length;
  if (!look || out === 7) {
    var says = document.createElement("span");
    says.className = "says";
    says.textContent = look ? "every one left out"
                            : "playing nothing, so they stay dark";
    head.appendChild(says);
  }
  box.appendChild(head);

  if (look && out < 7)
    box.appendChild(tunedBlock("playing <b>" + look.name + "</b>" +
                               (out ? out + " left out" : ""), state));
}

function renderStrips() {
  var box = document.getElementById("strips");
  box.textContent = "";
  STRIP_IDS.forEach(function (id) {
    var strip = state.strips[id];
    var letter = id.slice(-1);
    var look = lookNamed(strip.look);

    var head = document.createElement("div");
    head.className = "side-head";

    var tag = document.createElement("div");
    tag.className = "strip-tag " + letter.toLowerCase();
    tag.appendChild(document.createTextNode(letter === "L" ? "Left" : "Right"));
    head.appendChild(tag);

    var count = document.createElement("input");
    count.type = "number";
    count.min = 0;
    // The chip already says LEDs, so an empty box is simply none counted
    if (strip.leds) count.value = strip.leds;
    count.onchange = function () {
      // Nothing typed and none counted mean the same thing here
      strip.leds = Number(count.value) > 0 ? Number(count.value) : null;
      if (!strip.leds) strip.look = null;
      draw();
    };
    count.title = "How many LEDs are on this strip, which is the same for every scene";
    count.dataset.focus = "leds-" + id;
    tag.appendChild(count);
    var unit = document.createElement("small");
    unit.textContent = "LEDs";
    tag.appendChild(unit);

    if (strip.leds) head.appendChild(directionToggle(strip, draw));

    if (strip.leds) {
      var chain = lampsPreview(look, strip.leds, strip.reversed);
      chain.classList.add("chain");
      head.appendChild(chain);
    }

    if (!strip.leds || !look) {
      var says = document.createElement("span");
      says.className = "says";
      says.textContent = strip.leds ? "tap " + letter + " on a look above"
                                    : "say how many LEDs it has";
      head.appendChild(says);
    }
    box.appendChild(head);

    if (strip.leds && look)
      box.appendChild(tunedBlock("playing <b>" + look.name + "</b>",
                                 state.strips[id]));
  });
}

function renderScreensHead() {
  var box = document.getElementById("screensHead");
  box.textContent = "";
  SCREENS.forEach(function (letter) {
    var screen = state.screens[letter];
    var side = document.createElement("div");
    side.className = "screen-box " + letter.toLowerCase();
    var head = document.createElement("h3");
    head.appendChild(document.createTextNode("Screen " + letter));
    side.appendChild(head);

    var body = document.createElement("div");
    body.className = "body";
    side.appendChild(body);

    if (!screen.there) {
      body.className = "body adding";
      var add = document.createElement("button");
      add.textContent = "add this screen";
      add.onclick = function () {
        screen.there = true;
        screen.shows = null;
        screen.kept = null;
        draw();
      };
      body.appendChild(add);
      box.appendChild(side);
      return;
    }

    // Taking the screen out is the only way to have none: a screen showing
    // nothing says the same thing twice
    var drop = document.createElement("button");
    drop.className = "drop";
    drop.textContent = "\\u00d7";
    drop.title = "Take this screen out of every scene";
    drop.onclick = function () {
      screen.there = false;
      // Every scene's choice for it goes too, since nothing is left to show them
      store();
      allBodies().forEach(function (held) {
        held.screens[letter].shows = null;
        held.screens[letter].kept = null;
      });
      apply(slotAt(state.at).body);
      draw();
    };
    head.appendChild(drop);

    var size = document.createElement("select");
    var offered = CATALOGUE.board_settings["screen" + letter.toLowerCase()] || ["2.8", "1.54"];
    if (!screen.size) {
      var quiet = document.createElement("option");
      quiet.value = "";
      quiet.textContent = "size as fitted";
      quiet.selected = true;
      size.appendChild(quiet);
    }
    offered.forEach(function (inches) {
      var option = document.createElement("option");
      option.value = inches;
      option.textContent = inches + " inch";
      if (screen.size === inches) option.selected = true;
      size.appendChild(option);
    });
    size.onchange = function () {
      if (size.value) screen.size = size.value;
      draw();
    };
    size.className = "inband";
    size.title = "Which panel is plugged in, which is the same for every scene";
    head.insertBefore(size, drop);

    body.appendChild(panelPreview(screen));

    var settings = document.createElement("div");
    settings.className = "settings";
    var row = document.createElement("div");
    row.className = "row";
    var turn = document.createElement("select");
    [[0, "not turned"], [90, "quarter"], [180, "half"], [270, "three quarters"]]
      .forEach(function (pair) {
        var option = document.createElement("option");
        option.value = pair[0];
        option.textContent = pair[1];
        if (Number(screen.turn || 0) === pair[0]) option.selected = true;
        turn.appendChild(option);
      });
    turn.onchange = function () { screen.turn = Number(turn.value); draw(); };
    row.appendChild(turn);
    settings.appendChild(row);

    // A moving picture can bounce instead of jumping at the loop, and wait where
    // it turns; a slideshow also says how fast it walks its folder
    var media = screen.shows && screen.shows !== "keep" ? mediaNamed(screen.shows) : null;
    if (media && media.kind !== "image") {
      var moving = document.createElement("div");
      moving.className = "row";
      var back = document.createElement("label");
      back.className = "opt";
      back.title = "Play it forwards then backwards, no jump at the loop";
      var tick = document.createElement("input");
      tick.type = "checkbox";
      tick.checked = screen.pingpong;
      tick.onchange = function () { screen.pingpong = tick.checked; draw(); };
      back.appendChild(tick);
      back.appendChild(document.createTextNode("back and forth"));
      moving.appendChild(back);

      var holdWrap = document.createElement("label");
      holdWrap.className = "opt";
      holdWrap.title = "Seconds to wait where it turns around";
      holdWrap.appendChild(document.createTextNode("hold"));
      var hold = document.createElement("input");
      hold.type = "number";
      hold.min = 0;
      hold.step = 0.5;
      hold.value = screen.hold || "";
      hold.placeholder = "0";
      hold.dataset.focus = "hold-" + letter;
      hold.onchange = function () {
        screen.hold = hold.value && Number(hold.value) > 0 ? hold.value : "";
        draw();
      };
      holdWrap.appendChild(hold);
      moving.appendChild(holdWrap);

      if (media.kind === "folder") {
        var fpsWrap = document.createElement("label");
        fpsWrap.className = "opt";
        fpsWrap.title = "Pictures shown per second";
        fpsWrap.appendChild(document.createTextNode("fps"));
        var fps = document.createElement("input");
        fps.type = "number";
        fps.min = 1;
        fps.value = screen.fps;
        fps.dataset.focus = "fps-" + letter;
        fps.onchange = function () {
          screen.fps = Math.max(1, Number(fps.value) || 5);
          draw();
        };
        fpsWrap.appendChild(fps);
        moving.appendChild(fpsWrap);
      }
      settings.appendChild(moving);
    }

    var showing = document.createElement("div");
    showing.className = "showing";
    showing.innerHTML = screen.shows === "keep"
      ? "left as the file has it"
      : screen.shows
        ? "showing <b>" + screen.shows + "</b>" +
          (mediaNamed(screen.shows) ? "" : " (not on the drive)")
        : state.fileHandle ? "tap " + letter + " under a picture below"
                           : "open the FX drive to see its pictures";
    settings.appendChild(showing);

    body.appendChild(settings);

    // What the file already says for this screen, where the picker did not write it
    // and no picture can stand for it. It is a line of its own under the settings
    if (screen.kept) {
      var keep = document.createElement("button");
      keep.className = "keep" + (screen.shows === "keep" ? " picked" : "");
      keep.title = screen.kept;
      keep.innerHTML = "<b>Leave it as it is</b><code>" + screen.kept + "</code>";
      keep.onclick = function () { screen.shows = "keep"; draw(); };
      side.appendChild(keep);
    }
    box.appendChild(side);
  });
}

function mediaNamed(name) {
  return state.media.filter(function (m) { return m.name === name; })[0] || null;
}

// A picture's drawing on the panel: its object URL and shape, loaded once per name
function mediaArt(name) {
  var held = state.art[name];
  if (held) return held.ratio ? held : null;
  var media = mediaNamed(name);
  var handle = media && (media.kind === "folder" ? media.thumbHandle : media.handle);
  if (!handle) return null;
  state.art[name] = {url: null, ratio: 0};
  handle.getFile().then(function (file) {
    var url = URL.createObjectURL(file);
    var probe = new Image();
    probe.onload = function () {
      state.art[name] = {url: url, w: probe.naturalWidth, h: probe.naturalHeight,
                         ratio: probe.naturalWidth / probe.naturalHeight};
      draw();
    };
    probe.src = url;
  }).catch(function () { delete state.art[name]; });
  return null;
}

function renderAssets() {
  var box = document.getElementById("assets");
  box.textContent = "";
  document.getElementById("screensSays").textContent = !state.fileHandle
    ? "open the FX drive to see the pictures on it"
    : !state.scanned
      ? "reading the drive..."
      : state.media.length
        ? "one set of pictures, each able to go to A, to B, or to both"
        : "no pictures on the drive yet; drop a gif, png or jpg onto it";
  state.media.forEach(function (media) {
    var name = media.name;
    var on = {};
    SCREENS.forEach(function (l) {
      on[l] = state.screens[l].there && state.screens[l].shows === name;
    });
    var cell = document.createElement("div");
    cell.className = "asset" + (on.A && on.B ? " onAB" : on.A ? " onA" : on.B ? " onB" : "");
    var face = document.createElement("div");
    face.className = "face";
    var art = mediaArt(name);
    if (art) {
      face.style.background =
        "repeating-conic-gradient(#e8e4dc 0% 25%, #cbc5bb 0% 50%) 0 0/12px 12px";
      var img = document.createElement("img");
      img.src = art.url;
      face.appendChild(img);
    } else {
      // The extension stands in only until the picture arrives
      face.textContent = name.split(".").pop();
    }
    if (media.kind !== "image") {
      var kind = document.createElement("span");
      kind.className = "kind";
      kind.textContent = media.kind === "folder" ? "slideshow" : "gif";
      face.appendChild(kind);
    }
    cell.appendChild(face);
    cell.title = name;
    var label = document.createElement("div");
    label.className = "label";
    label.textContent = name;
    face.appendChild(label);
    var pick = document.createElement("div");
    pick.className = "pick";
    SCREENS.forEach(function (letter) {
      var button = document.createElement("button");
      button.textContent = letter;
      var lit = on[letter];
      button.className = lit ? "lit" + (letter === "B" ? " b" : "") : "";
      button.disabled = !state.screens[letter].there;
      if (button.disabled) button.style.opacity = ".3";
      button.onclick = function () {
        // Tapping the lit one again goes back to what the file said, where there
        // is something to go back to. Where there is not, it would mean a screen
        // showing nothing, which the header's cross already says
        var screen = state.screens[letter];
        screen.shows = (screen.shows === name && screen.kept) ? "keep" : name;
        draw();
      };
      pick.appendChild(button);
    });
    cell.appendChild(pick);
    cell.appendChild(binButton(name, media.kind));
    box.appendChild(cell);
  });
  if (state.fileHandle)
    box.appendChild(adderTile("add pictures",
      {description: "Pictures the board plays",
       accept: {"image/png": [".gif", ".png", ".jpg", ".jpeg"]}},
      "pictures", /\\.(gif|png|jpe?g)$/i));
}

// Files picked in the dialog, written straight onto the drive: the same handle a
// save uses, so nothing leaves the page. What did not fit is said plainly
async function addFiles(kinds, what, takes) {
  var picked;
  try {
    picked = await window.showOpenFilePicker({multiple: true, types: [kinds],
                                              excludeAcceptAllOption: true});
  } catch (e) {
    return;                       // the dialog was dismissed
  }
  var landed = 0;
  var refused = [];
  for (var i = 0; i < picked.length; i++) {
    var file;
    try {
      // The dialog filters, and this holds where a platform's does not: a kind
      // the board cannot play never reaches the drive
      if (!takes.test(picked[i].name)) {
        refused.push(picked[i].name + " (not a kind the board plays)");
        continue;
      }
      file = await picked[i].getFile();
      var existing = null;
      try { existing = await state.dirHandle.getFileHandle(file.name); } catch (e) {}
      if (existing && !confirm(file.name + " is already on the drive. Replace it?"))
        continue;
      var handle = await state.dirHandle.getFileHandle(file.name, {create: true});
      var writable = await handle.createWritable();
      await writable.write(file);
      await writable.close();
      landed++;
    } catch (e) {
      refused.push(file ? file.name : "a file");
      if (e.name === "QuotaExceededError") {
        refused = refused.concat(picked.slice(i + 1).map(function (p) { return p.name; }));
        banner("The FX drive filled up: " + landed + " " + what + " copied, no room for " +
               refused.join(", ") + ". Delete something from it and try again.", true);
        break;
      }
    }
  }
  if (landed && !refused.length)
    banner(landed + " " + what + " copied to the drive.");
  else if (refused.length && landed)
    banner(landed + " copied; these did not arrive: " + refused.join(", "), true);
  else if (refused.length)
    banner("Nothing arrived: " + refused.join(", "), true);
  try { await scanMedia(state.dirHandle); } catch (e) {}
  draw();
}

// Takes one file off the drive, clearing whatever on the page was showing it
async function removeFromDrive(name, kind) {
  var said = kind === "folder"
    ? "Delete the folder " + name + " and every picture in it from the FX drive?"
    : "Delete " + name + " from the FX drive?";
  if (!confirm(said)) return;
  try {
    await state.dirHandle.removeEntry(name, {recursive: kind === "folder"});
  } catch (e) {
    banner("Could not delete " + name + ": " + e.name + ". Is the drive showing?", true);
    return;
  }
  store();
  allBodies().forEach(function (body) {
    SCREENS.forEach(function (letter) {
      if (body.screens[letter].shows === name) body.screens[letter].shows = null;
    });
  });
  apply(slotAt(state.at).body);
  if (state.sound === name) {
    state.sound = null;
    state.soundLoop = false;
  }
  delete state.soundInfo[name];
  delete state.art[name];
  try { await scanMedia(state.dirHandle); } catch (e) {}
  draw();
}

// The cross that offers it, quiet until the pointer is over the tile
function binButton(name, kind) {
  var bin = document.createElement("span");
  bin.className = "bin";
  bin.textContent = "\\u00d7";
  bin.title = "Delete " + name + " from the FX drive";
  bin.onclick = function (e) {
    e.stopPropagation();
    removeFromDrive(name, kind);
  };
  return bin;
}

function adderTile(label, kinds, what, takes) {
  var tile = document.createElement("button");
  tile.className = "adder";
  tile.innerHTML = "<svg width='13' height='13' viewBox='0 0 11 11'><path d='M5.5 1 " +
                   "L5.5 10 M1 5.5 L10 5.5' stroke='currentColor' stroke-width='1.8' " +
                   "stroke-linecap='round'/></svg>" + label;
  tile.title = "Copy files from this computer onto the FX drive";
  tile.onclick = function () { addFiles(kinds, what, takes); };
  return tile;
}

// Lines the file already had that no control on this page stands for: they are
// carried word for word, in this scene, and each can be dropped
function renderKept() {
  var box = document.getElementById("kept");
  box.hidden = !state.kept.length;
  box.textContent = "";
  if (!state.kept.length) return;
  var head = document.createElement("div");
  head.textContent = "Also " + (state.scenes.length ? "in this scene" : "in the file") +
                     ", kept as written:";
  box.appendChild(head);
  state.kept.forEach(function (line, i) {
    var row = document.createElement("div");
    row.className = "row";
    var code = document.createElement("code");
    code.textContent = line;
    row.appendChild(code);
    var drop = document.createElement("button");
    drop.className = "drop";
    drop.textContent = "\\u00d7";
    drop.title = "Take this line out of the file";
    drop.onclick = function () {
      state.kept.splice(i, 1);
      draw();
    };
    row.appendChild(drop);
    box.appendChild(row);
  });
}

function renderSound() {
  var box = document.getElementById("sound");
  box.textContent = "";
  document.getElementById("soundSays").textContent = !state.fileHandle
    ? "open the FX drive to see the sounds on it"
    : !state.scanned
      ? "reading the drive..."
    : state.sounds.length || state.sound || state.soundKept
      ? "one wav, playing on while the lights run"
      : "no sounds on the drive yet; drop a wav onto it";

  // How the sound is played rather than which one it is, so it sits above them,
  // where a screen keeps its settings
  var again = document.createElement("button");
  again.className = "again" + (state.soundLoop && state.sound ? " on" : "");
  again.textContent = "on repeat";
  again.disabled = !state.sound;
  again.title = state.sound
    ? "Start it again as it ends, instead of playing once as the board starts"
    : "Nothing is playing, so there is nothing to repeat";
  again.onclick = function () { state.soundLoop = !state.soundLoop; draw(); };
  var above = document.createElement("div");
  above.style.margin = "0 0 .7rem";
  above.appendChild(again);
  box.appendChild(above);

  var row = document.createElement("div");
  row.className = "sounds";
  // A sound the file names that the drive does not hold still gets its tile, since
  // the board may find it on its own storage
  var names = state.sounds.slice();
  if (state.sound && names.indexOf(state.sound) < 0) names.unshift(state.sound);
  if (state.soundKept) row.appendChild(soundKeptTile());
  names.forEach(function (name) { row.appendChild(soundTile(name)); });
  row.appendChild(soundTile(null));
  if (state.fileHandle)
    row.appendChild(adderTile("add sounds",
      {description: "Sounds the board plays", accept: {"audio/wav": [".wav"]}},
      "sounds", /\\.wav$/i));
  box.appendChild(row);
}

// The audio line the file already had, which no tile of a name can stand for
function soundKeptTile() {
  var tile = document.createElement("button");
  tile.className = "sound" + (state.sound ? "" : " picked");
  tile.title = state.soundKept;
  tile.innerHTML = "<svg viewBox='0 0 104 30' preserveAspectRatio='none'><rect x='0' " +
                   "y='14' width='104' height='2' rx='1' fill='#c9c3b9'/></svg>";
  var title = document.createElement("b");
  title.textContent = "As it is";
  tile.appendChild(title);
  var says = document.createElement("small");
  says.textContent = state.soundKept.slice(0, 40);
  tile.appendChild(says);
  tile.onclick = function () {
    state.sound = null;
    state.soundLoop = false;
    draw();
  };
  return tile;
}

// A sound to choose, or the silence at the end of the row, which is simply no entry
function soundTile(name) {
  var picked = name === null ? !state.sound && !state.soundKept : state.sound === name;
  var info = name ? state.soundInfo[name] : null;
  var tile = document.createElement("button");
  tile.className = "sound" + (picked ? " picked" : "") + (name ? "" : " quiet");
  var colour = picked ? "#0f8a72" : "#c9c3b9";
  if (name && info && info.bars) {
    var cells = [];
    info.bars.forEach(function (tall, i) {
      var high = Math.max(2, tall * 26);
      cells.push("<rect x='" + (i * 4) + "' y='" + ((30 - high) / 2) + "' width='2.6' " +
                 "height='" + high + "' rx='1.3' fill='" + colour + "'/>");
    });
    tile.innerHTML = "<svg viewBox='0 0 104 30' preserveAspectRatio='none'>" +
                     cells.join("") + "</svg>";
  } else {
    tile.innerHTML = "<svg viewBox='0 0 104 30' preserveAspectRatio='none'><rect x='0' " +
                     "y='14' width='104' height='2' rx='1' fill='" + colour + "'/></svg>";
  }
  var title = document.createElement("b");
  title.textContent = name || "Silence";
  tile.appendChild(title);
  var says = document.createElement("small");
  says.textContent = !name ? "nothing plays"
                   : info && info.seconds ? info.seconds + "s" +
                     (picked && state.soundLoop ? ", on repeat" : "")
                   : state.sounds.indexOf(name) < 0 ? "not on the drive" : "";
  tile.appendChild(says);
  tile.onclick = function () {
    state.sound = name;
    if (name) state.soundKept = null;
    if (!name) {
      state.soundLoop = false;
      state.soundKept = null;
    }
    draw();
  };
  if (name && state.sounds.indexOf(name) >= 0) tile.appendChild(binButton(name, "wav"));
  return tile;
}

function renderPreview() {
  var text = currentText();
  document.getElementById("preview").innerHTML =
    text.split("\\n").map(paintLine).join("\\n");
}

function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// The written file in the editor's colours: comments, headings, and entries as
// selector, settings and effect. Painting only what it wrote, it can stay far
// simpler than the editor's own highlighter
function paintLine(line) {
  var bare = escapeHtml(line);
  if (/^\\s*#/.test(line)) return "<span class='s-comment'>" + bare + "</span>";
  var heading = line.match(/^(\\s*\\[\\s*)([^:\\]]*)(.*)$/);
  if (heading)
    return "<span class='s-punc'>" + escapeHtml(heading[1]) + "</span>" +
           "<span class='s-scene'>" + escapeHtml(heading[2]) + "</span>" +
           "<span class='s-punc'>" + escapeHtml(heading[3]) + "</span>";
  var at = line.indexOf(":");
  if (at < 0) return bare;

  function settings(text) {
    return (text.match(/"[^"]*"|\\S+|\\s+/g) || []).map(function (token) {
      var pair = token.match(/^([^=\\s]+)(=)(.*)$/);
      if (!pair) return escapeHtml(token);
      return "<span class='s-name'>" + escapeHtml(pair[1]) + "</span>" +
             "<span class='s-punc'>=</span>" +
             "<span class='s-value'>" + escapeHtml(pair[3]) + "</span>";
    }).join("");
  }

  var left = line.slice(0, at);
  var right = line.slice(at + 1);
  var selector = left.match(/^(\\s*)(\\S+)(.*)$/);
  var head = selector
    ? escapeHtml(selector[1]) + "<span class='s-target'>" + escapeHtml(selector[2]) +
      "</span>" + settings(selector[3])
    : escapeHtml(left);
  var effect = right.match(/^(\\s*)(\\S+)(.*)$/);
  var tail = effect
    ? escapeHtml(effect[1]) + "<span class='s-effect'>" + escapeHtml(effect[2]) +
      "</span>" + settings(effect[3])
    : escapeHtml(right);
  return head + "<span class='s-colon'>:</span>" + tail;
}

function draw() {
  // A redraw replaces the control being used, so whoever had focus is found
  // again by name once the page is rebuilt: a stepper can be clicked repeatedly
  var held = document.activeElement && document.activeElement.dataset
           ? document.activeElement.dataset.focus : null;
  renderRecognised();
  renderScenes();
  renderSceneSettings();
  renderGallery();
  renderOutputs();
  renderStrips();
  renderScreensHead();
  renderAssets();
  renderKept();
  renderSound();
  renderPreview();
  if (held) {
    var again = document.querySelector('[data-focus="' + held + '"]');
    if (again) again.focus();
  }
}

function banner(text, warn, detail) {
  var box = document.getElementById("banner");
  box.textContent = "";
  if (!text) return;
  var note = document.createElement("div");
  // warn may also be "hold", the amber of a check still running
  note.className = warn === "hold" ? "banner hold" : warn ? "banner warn" : "banner";
  note.textContent = text;
  if (detail) {
    var pre = document.createElement("pre");
    pre.textContent = detail;
    note.appendChild(pre);
  }
  box.appendChild(note);
}

// ---- the drive -------------------------------------------------------------------

var scanBusy = false;

async function scanMedia(dir) {
  // What the drive holds that a screen can show: gifs and stills, PNG or JPEG,
  // and folders of them, which play as a slideshow. One walk at a time, built
  // aside and landed whole, so a redraw mid-scan never sees half a drive and two
  // walks can never lace their findings together
  if (scanBusy) return;
  scanBusy = true;
  var media = [];
  var sounds = [];
  try {
    for await (var pair of dir.entries()) {
      var name = pair[0], handle = pair[1];
      if (handle.kind === "file") {
        if (/\\.gif$/i.test(name)) media.push({ name: name, kind: "gif", handle: handle });
        else if (/\\.(png|jpe?g)$/i.test(name)) media.push({ name: name, kind: "image", handle: handle });
        else if (/\\.wav$/i.test(name)) {
          sounds.push(name);
          profileSound(name, handle);
        }
      } else if (name !== "System Volume Information") {
        for await (var inner of handle.entries()) {
          if (inner[1].kind === "file" && /\\.(gif|png|jpe?g)$/i.test(inner[0])) {
            media.push({ name: name, kind: "folder", thumbHandle: inner[1] });
            break;
          }
        }
      }
    }
  } finally {
    scanBusy = false;
  }
  sounds.sort();
  media.sort(function (a, b) { return a.name < b.name ? -1 : 1; });
  state.media = media;
  state.sounds = sounds;
  state.scanned = true;
}

// A wav's length and shape, read from the file itself: the header gives the
// byte rate and the data run, and a few small slices give the peaks. Anything
// unreadable simply draws flat
async function profileSound(name, handle) {
  if (state.soundInfo[name] !== undefined) return;
  state.soundInfo[name] = null;
  try {
    var file = await handle.getFile();
    var head = new DataView(await file.slice(0, 8192).arrayBuffer());
    if (head.getUint32(0) !== 0x52494646 || head.getUint32(8) !== 0x57415645)
      throw new Error("not a wav");
    var at = 12;
    var byteRate = 0;
    var bits = 16;
    var dataAt = 0;
    var dataSize = 0;
    while (at + 8 <= head.byteLength) {
      var id = head.getUint32(at);
      var size = head.getUint32(at + 4, true);
      if (id === 0x666d7420) {                       // "fmt "
        byteRate = head.getUint32(at + 16, true);
        bits = head.getUint16(at + 22, true);
      } else if (id === 0x64617461) {                // "data"
        dataAt = at + 8;
        dataSize = Math.min(size, file.size - dataAt);
        break;
      }
      at += 8 + size + (size % 2);
    }
    if (!byteRate || !dataSize) throw new Error("no sound in it");

    var bars = [];
    for (var b = 0; b < 26; b++) {
      var from = dataAt + Math.floor(dataSize * b / 26);
      var take = Math.min(2048, dataAt + dataSize - from);
      var slice = await file.slice(from, from + take).arrayBuffer();
      var peak = 0;
      if (bits === 16) {
        var wide = new Int16Array(slice, 0, Math.floor(slice.byteLength / 2));
        for (var i = 0; i < wide.length; i++) peak = Math.max(peak, Math.abs(wide[i]));
        peak /= 32768;
      } else {
        var thin = new Uint8Array(slice);
        for (var j = 0; j < thin.length; j++) peak = Math.max(peak, Math.abs(thin[j] - 128));
        peak /= 128;
      }
      bars.push(peak);
    }
    state.soundInfo[name] = {seconds: Math.max(1, Math.round(dataSize / byteRate)),
                             bars: bars};
    renderSound();
  } catch (e) {
    state.soundInfo[name] = null;
  }
}

// ---- remembering the drive -------------------------------------------------------

// The drive's handle survives in IndexedDB, so after the first visit it is reached
// with one click and a permission bubble instead of the file dialog every time. A
// page cannot go looking for the drive itself; remembering the answer is what there
// is. Anything failing in here falls back to the dialog
function rememberDrive(handle) {
  try {
    var open = indexedDB.open("fx-pages", 1);
    open.onupgradeneeded = function () { open.result.createObjectStore("handles"); };
    open.onsuccess = function () {
      try {
        open.result.transaction("handles", "readwrite")
            .objectStore("handles").put(handle, "drive");
      } catch (e) {}
    };
  } catch (e) {}
}

function rememberedDrive() {
  return new Promise(function (settle) {
    try {
      var open = indexedDB.open("fx-pages", 1);
      open.onupgradeneeded = function () { open.result.createObjectStore("handles"); };
      open.onerror = function () { settle(null); };
      open.onsuccess = function () {
        try {
          var ask = open.result.transaction("handles").objectStore("handles").get("drive");
          ask.onsuccess = function () { settle(ask.result || null); };
          ask.onerror = function () { settle(null); };
        } catch (e) { settle(null); }
      };
    } catch (e) { settle(null); }
  });
}

async function pickDrive(fresh) {
  var kept = await rememberedDrive();
  if (kept && !fresh) {
    try {
      if (await kept.requestPermission({mode: "readwrite"}) === "granted") {
        await kept.getFileHandle("effects.txt");
        return kept;
      }
    } catch (e) {}
  }
  var picked;
  try {
    picked = await window.showDirectoryPicker(
        kept ? {mode: "readwrite", startIn: kept} : {mode: "readwrite"});
  } catch (e) {
    if (e.name === "AbortError") throw e;
    picked = await window.showDirectoryPicker({mode: "readwrite"});
  }
  rememberDrive(picked);
  return picked;
}

async function connect(fresh) {
  var dir = await pickDrive(fresh);
  var file;
  try {
    file = await dir.getFileHandle("effects.txt");
  } catch (e) {
    // Every FX drive carries effects.txt, so a folder without one is simply not
    // an FX drive, and saying so beats a bare error name
    if (e.name === "NotFoundError") {
      var refused = new Error("no effects.txt");
      refused.name = "NotAnFxDrive";
      throw refused;
    }
    throw e;
  }
  state.dirHandle = dir;
  state.fileHandle = file;
  await scanMedia(dir);
  absorbText(await (await state.fileHandle.getFile()).text());
  document.getElementById("check").disabled = false;
  document.getElementById("status").textContent = "connected to the drive";
  // The next thing to do carries the colour: opening first, then saving. Once a
  // drive is open the only opening left is a different one, so one button remains
  // and it goes straight to the dialog
  var openButton = document.getElementById("open");
  openButton.className = "";
  openButton.textContent = "Open a different drive";
  openButton.onclick = openFresh;
  document.getElementById("openOther").hidden = true;
  var saveButton = document.getElementById("save");
  saveButton.className = "primary";
  saveButton.disabled = false;
  draw();
}

// ---- waiting for the board -------------------------------------------------------

// Only the board writes errors.txt, and only where it has re-read the file, so a
// change there is proof it acted. It answers a save in about four seconds.
//
// Never read effects.txt while waiting. A read of the file just saved holds off the
// write the computer still has in hand, and the board then waits half a minute to
// see it, measured 2026-08-22
var BOARD_SETTLE_MS = 6000;
var BOARD_WAIT_MS = 15000;
var BOARD_POLL_MS = 250;

function playsItself(text) {
  return /\\breload\\s*=\\s*auto\\b/i.test(text);
}

// Written into errors.txt before saving, so the board's answer is always a
// change: it deletes the file where the save reads clean and rewrites it where
// not, so this line vanishing is the answer either way. Self-describing, since a
// board that never reads the file leaves it to be found later
var CHECKING = "The board has not read the file yet.";

// Writes the marker; returns whether it took, a full drive being the reason not
async function markChecking() {
  try {
    var handle = await state.dirHandle.getFileHandle("errors.txt", {create: true});
    var writable = await handle.createWritable();
    await writable.write(CHECKING + "\\n");
    await writable.close();
    return true;
  } catch (e) {
    return false;
  }
}

// The text of errors.txt, null where there is none, and false where the drive is
// away mid-reload and the question cannot be answered yet
async function readErrors() {
  try {
    var handle = await state.dirHandle.getFileHandle("errors.txt");
    return (await (await handle.getFile()).text()).trim();
  } catch (e) {
    return e.name === "NotFoundError" ? null : false;
  }
}

// Polls until errors.txt differs from what it said before the save, calling
// nothingYet() once the settle time passes, saying the check is still running: an
// answer can arrive after the settle, so nothing is claimed until the wait is over.
// Seeing the drive away is proof the board acted, so an unchanged answer after that
// is a real answer rather than an early one
async function waitForBoard(before, nothingYet) {
  var deadline = Date.now() + BOARD_WAIT_MS;
  var settled = Date.now() + BOARD_SETTLE_MS;
  var wentAway = false;
  var told = false;
  while (Date.now() < deadline) {
    await new Promise(function (settle) { setTimeout(settle, BOARD_POLL_MS); });
    var now = await readErrors();
    if (now === false) {
      wentAway = true;
      continue;
    }
    if (now !== before) return now;
    if (wentAway) return now;
    if (!told && Date.now() > settled) {
      nothingYet();
      told = true;
    }
  }
  return before;
}

// What to say once the wait is over. Silence cannot be told from a board that has
// not got there yet, so it is reported as nothing said rather than as all well
function sayWhatHappened(said, also) {
  if (said === CHECKING)
    banner("The board did not pick the save up. Eject the FX drive, or press " +
           "the board's button once, and it plays.", true);
  else if (said)
    banner("The board wasn't happy with some of it:", true, said);
  else
    banner("Playing on the board. No problems reported." + (also || ""));
}

document.getElementById("save").onclick = async function () {
  try {
    if (!state.fileHandle) await connect();
    var onBoard = await (await state.fileHandle.getFile()).text();
    var lastWritten = null;
    try { lastWritten = localStorage.getItem("fx-picker-wrote"); } catch (e) {}
    if (onBoard.indexOf("Written by the FX picker") < 0 && onBoard !== lastWritten &&
        onBoard.trim() !== "") {
      if (!confirm("The file on the board was written some other way, maybe by hand. " +
                   "Its entries are kept, but its comments and layout will be redone. " +
                   "Save over it?"))
        return;
    }
    var text = currentText();
    // The board acts on a save only where the file it is already running asked it
    // to, so the first save that turns it on still needs an eject
    var errorsBefore = playsItself(onBoard) ? await readErrors() : undefined;
    // The marker makes the answer an edge even where nothing else changes
    if (errorsBefore !== undefined && await markChecking()) errorsBefore = CHECKING;
    var writable = await state.fileHandle.createWritable();
    await writable.write(text);
    await writable.close();
    var back = await (await state.fileHandle.getFile()).text();
    if (back !== text) throw new Error("the file read back differently");
    try { localStorage.setItem("fx-picker-wrote", text); } catch (e) {}
    state.recognised = {look: state.always.body.look ||
                        (state.scenes[0] ? state.scenes[0].body.look : null),
                        exact: true, any: true};
    var newStrips = STRIP_IDS.filter(function (id) {
      return state.strips[id].leds && state.stripsAtStart.indexOf(id) < 0;
    });
    var strips = newStrips.length
               ? " The strip you added only comes up when the board starts, so turn it off "
                 + "and on once you are done."
               : "";
    if (errorsBefore === undefined) {
      banner("On its way. " + (playsItself(text)
             ? "Eject the FX drive, or press the board's button once, to play this one. "
               + "From now on a save plays on its own."
             : "Eject the FX drive on this computer, and the board plays it. Double-press "
               + "the board's button to bring the drive back, then ask 'Did it work?'.")
             + strips);
      return;
    }
    banner("Saved. Waiting for the board to pick it up...", "hold");
    var was = errorsBefore === false ? null : errorsBefore;
    sayWhatHappened(await waitForBoard(was, function () {
      banner("Playing on the board. Checking for problems..." + strips, "hold");
    }), strips);
  } catch (e) {
    if (e.name === "AbortError") return;
    if (e.name === "QuotaExceededError") {
      // The drive is there, it is simply full: saving writes a temporary copy
      // first, so it needs the file's size free
      banner("The FX drive is full, so there was no room to save. Delete a " +
             "picture or sound from it and try again.", true);
      return;
    }
    state.fileHandle = null;
    state.dirHandle = null;
    banner("That didn't reach the board: " + e.name + ". Is the FX drive showing? " +
           "A double press of its button brings it back; then try again.", true);
  }
};

document.getElementById("check").onclick = async function () {
  // A blink before the answer, so asking again visibly did something even when
  // the answer reads the same
  banner("Asking the board...", "hold");
  await new Promise(function (settle) { setTimeout(settle, 350); });
  try {
    var handle = await state.dirHandle.getFileHandle("errors.txt");
    var text = await (await handle.getFile()).text();
    if (text.trim() === CHECKING) {
      banner("The board has not read the file yet. Eject the FX drive, or press " +
             "the board's button once.", "hold");
      return;
    }
    banner("The board wasn't happy with some of it:", true, text.trim());
  } catch (e) {
    if (e.name === "NotFoundError")
      banner("All good. The board read the file and found nothing wrong.");
    else
      banner("Couldn't look: " + e.name + ". Is the drive showing?", true);
  }
};

async function openDrive(fresh) {
  try {
    await connect(fresh);
    banner("");
  } catch (e) {
    if (e.name === "AbortError") return;
    if (e.name === "NotAnFxDrive") {
      banner("That folder has no effects.txt, so it does not look like an FX " +
             "drive. Pick the drive itself, the one named FX.", true);
      return;
    }
    banner("Could not open the drive: " + e.name + ". Is it showing? " +
           "A double press of the board's button brings it back.", true);
  }
}

function openFresh() { openDrive(true); }

document.getElementById("open").onclick = function () { openDrive(false); };
document.getElementById("openOther").onclick = openFresh;

// Where a visit before this one answered which drive, the choice is offered by
// name beside the way to a different one
rememberedDrive().then(function (kept) {
  if (!kept || state.fileHandle) return;
  // A drive root's name comes back as a bare slash, so only a real folder name
  // is worth showing
  var name = kept.name && kept.name.length > 1 ? " (" + kept.name + ")" : " again";
  document.getElementById("open").textContent = "Open the FX drive" + name;
  document.getElementById("openOther").hidden = false;
});

// What the drive holds changes as people copy files on, so it is looked at
// again every few seconds and the grid redrawn only where something changed.
// Directory reads never touch effects.txt, so the board's save watch is safe
async function rescanMedia() {
  if (!state.dirHandle || scanBusy) return;
  var was = JSON.stringify([state.media.map(function (m) { return m.name + m.kind; }),
                            state.sounds]);
  try {
    await scanMedia(state.dirHandle);
  } catch (e) {
    return;
  }
  var now = JSON.stringify([state.media.map(function (m) { return m.name + m.kind; }),
                            state.sounds]);
  if (now !== was) draw();
}
setInterval(rescanMedia, 5000);

document.getElementById("straight").onchange = function () {
  state.straight = document.getElementById("straight").checked;
  draw();
};

draw();
</script>
</body>
</html>
"""

EDITOR = """\
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>FX Editor</title>
<script src="catalogue.js"></script>
<style>
:root{
 --bg:#f5f3ef; --panel:#fff; --ink:#26221e; --dim:#8a8378; --line:#e2ddd4;
 --accent:#00857d; --accent-ink:#fff; --warn:#b33; --warn-bg:#fbeaea;
 --target:#1f6feb; --effect:#0a7f78; --value:#a8500a; --scene:#7b3fb8;
 --comment:#8a8378; --faint:#5d656e;
}
*{box-sizing:border-box}
body{font:16px/1.5 system-ui,sans-serif;margin:0;background:var(--bg);color:var(--ink)}
header{display:flex;align-items:center;gap:.8rem;padding:.8rem 1.4rem;background:var(--panel);
 border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
header h1{font-size:1.1rem;margin:0 auto 0 0}
button{font:inherit;padding:.5rem 1rem;border:1px solid var(--line);border-radius:8px;
 background:var(--panel);cursor:pointer}
button.primary{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);font-weight:600}
button:disabled{opacity:.4;cursor:default}
main{max-width:52rem;margin:1.5rem auto;padding:0 1.4rem}
#status{font-size:.85rem;color:var(--dim)}
.banner{padding:.8rem 1.1rem;border-radius:10px;margin:1rem 0;background:#e7f2f1}
.banner.warn{background:var(--warn-bg);color:var(--warn)}
.banner.hold{background:#fdf3e0;color:#8a6415}
.banner pre{margin:.4rem 0 0;white-space:pre-wrap;font-size:.85rem}

.editor{position:relative;background:var(--panel);border:1px solid var(--line);
 border-radius:14px;overflow:hidden;height:24rem}
.editor pre, .editor textarea{
 position:absolute;inset:0;margin:0;padding:1rem 1.2rem;border:0;
 font:14px/1.6 ui-monospace,Consolas,"Cascadia Mono",monospace;
 white-space:pre;overflow:auto;tab-size:4;
}
.editor pre{pointer-events:none;background:transparent;color:var(--ink);z-index:1;
 scrollbar-width:none}
.editor pre::-webkit-scrollbar{display:none}
.editor textarea{background:transparent;color:transparent;caret-color:var(--ink);
 resize:none;outline:none;z-index:2}
.editor textarea::selection{background:rgba(0,133,125,.18)}

.s-target{color:var(--target)}
.s-effect{color:var(--effect);font-weight:600}
.s-value{color:var(--value)}
.s-scene{color:var(--scene);font-weight:600}
.s-name{color:var(--ink)}
.s-punc{color:var(--faint)}
.s-colon{color:var(--ink);font-weight:700}
.s-comment{color:var(--comment);font-style:italic}
.s-bad{text-decoration:underline wavy var(--warn);text-decoration-skip-ink:none}

.suggest{position:fixed;z-index:6;background:var(--panel);border:1px solid var(--line);
 border-radius:10px;box-shadow:0 6px 18px rgba(0,0,0,.12);min-width:12rem;max-width:24rem;
 max-height:14rem;overflow:auto;display:none;font:13px/1.5 ui-monospace,Consolas,monospace}
.suggest.shown{display:block}
.suggest div{padding:.25rem .8rem;cursor:pointer;display:flex;gap:.8rem;align-items:baseline}
.suggest div small{color:var(--dim);font:12px/1.4 system-ui,sans-serif;margin-left:auto;
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.suggest div.lit{background:var(--accent);color:var(--accent-ink)}
.suggest div.lit small{color:var(--accent-ink)}
.suggest div.rule{border-top:1px solid var(--line);margin:.25rem 0;padding:0;cursor:default}

.hint{font-size:.85rem;color:var(--dim);margin:.6rem .2rem;min-height:1.3rem}
.foot{font-size:.85rem;color:var(--dim);margin:1.2rem .2rem}
.foot a{color:var(--accent)}
</style>
</head>
<body>
<header>
<h1>FX Editor</h1>
<span id="status">nothing open yet</span>
<button id="open" class="primary">Open the FX drive</button>
<button id="save" disabled>Put it on the board</button>
<button id="check" disabled>Did it work?</button>
</header>
<main>
<div id="banners"></div>
<div class="editor">
<pre id="paint"><code id="painted"></code></pre>
<textarea id="entry" spellcheck="false" autocapitalize="off" autocomplete="off" wrap="off"></textarea>
<div id="suggest" class="suggest"></div>
</div>
<div id="hint" class="hint"></div>
<p class="foot">One entry per line: which lights, a colon, then the effect.
The board checks the file when the drive ejects, and "Did it work?" reads what it made
of each line. Rather pick from cards? <a href="PICKER.html">PICKER.html</a> on this
drive writes the file for you.</p>
</main>
<script>
"use strict";

// The page still paints without the catalogue beside it; the hint line says why
// nothing can be offered
if (typeof CATALOGUE === "undefined") window.CATALOGUE = null;

// ---- what the file may say, from the same tables the board reads ---------------

var TYPE_HINTS = {
  fraction: "0 to 1, or a percent such as 50%",
  seconds: "a time in seconds",
  number: "a number",
  count: "a whole number",
  span: "how many lights it spreads over",
  whole: "a whole number",
  byte: "0 to 255",
  angle: "degrees, 0 to 360",
  colour: "a name such as warm, or six-digit hex with no #",
  boolean: "true or false",
  quarter: "0, 90, 180 or 270",
  name: "a file on this drive"
};

// The left side's own settings have shapes the type table does not carry
var CHANNEL_HINTS = {
  colour: "a name such as warm, or six-digit hex with no #",
  offset: "where the picture goes, as x|y, * centring that side",
  background: "the colour around the picture",
  bg: "the colour around the picture",
  tile: "repeat or mirror to fill the screen with copies, as across|down"
};

var TARGETS = [
  ["out1-7", "all seven outputs"],
  ["screenA", "a screen on SP/CE A"],
  ["screenB", "a screen on SP/CE B"],
  ["stripL", "an LED strip on L"],
  ["stripR", "an LED strip on R"],
  ["audio", "a sound played beside the effects"],
  ["board", "settings for the board itself"],
  ["[", "a scene heading, [Name: 10s]; entries above the first are always on"]
];

var BOARD_HINTS = {
  drive: "manual keeps the drive hidden until asked for",
  reload: "auto plays the file the moment it is saved, no eject needed",
  program: "a Python file to run instead of the effects",
  args: "what to pass that program, divided by |",
  screena: "what size of screen is on SP/CE A",
  screenb: "what size of screen is on SP/CE B",
  stripl: "how many LEDs are on a strip plugged into L",
  stripr: "the same for R"
};

// The spelling a completion inserts, where the file reads best in mixed case
var BOARD_CASE = {screena: "screenA", screenb: "screenB",
                  stripl: "stripL", stripr: "stripR"};

function targetKind(word) {
  var lowered = word.toLowerCase();
  if (lowered === "board") return "board";
  if (CATALOGUE && lowered === CATALOGUE.audio) return "audio";
  if (lowered.slice(0, 6) === "screen") return "screen";
  if (lowered.slice(0, 5) === "strip") return "strip";
  return "output";
}

function channelSettings(kind) {
  // A sound answers to none of the channel settings, autofx saying so where one
  // is written
  if (!CATALOGUE || kind === "board" || kind === "audio") return [];
  if (kind === "screen") return CATALOGUE.screen_settings || [];
  return CATALOGUE.output_settings || [];
}

function effectNames(kind) {
  if (!CATALOGUE) return [];
  if (kind === "screen") return Object.keys(CATALOGUE.screen_effects);
  if (kind === "audio") return Object.keys(CATALOGUE.audio_effects);
  return Object.keys(CATALOGUE.effects);
}

function effectTakes(name, kind) {
  if (!CATALOGUE) return null;
  if (kind === "screen") return CATALOGUE.screen_effects[name.toLowerCase()] || null;
  if (kind === "audio") return CATALOGUE.audio_effects[name.toLowerCase()] || null;
  var effect = CATALOGUE.effects[name.toLowerCase()];
  return effect ? effect.takes : null;
}

function settingType(name, kind) {
  if (!CATALOGUE) return null;
  var lowered = name.toLowerCase();
  return CATALOGUE.channel_kinds[lowered] ||
         (kind !== "board" && CATALOGUE.settings[lowered]) || null;
}

function valuesFor(name, kind) {
  if (!CATALOGUE) return null;
  var lowered = name.toLowerCase();
  if (kind === "board") {
    var allowed = CATALOGUE.board_settings[lowered];
    return allowed && allowed.length ? allowed.map(String) : null;
  }
  if (lowered === "colour" || lowered === "background" || lowered === "bg")
    return CATALOGUE.colours;
  if (lowered === "rotation") return ["0", "90", "180", "270"];
  if (lowered === "tile") return CATALOGUE.tiling || [];
  if (settingType(name, kind) === "boolean") return ["true", "false"];
  return null;
}

// ---- painting, the same roles the manual gives each word -----------------------

function esc(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function mark(role, text) {
  return text ? '<span class="' + role + '">' + text + "</span>" : text;
}

function settingTok(token) {
  var trailing = "";
  while (token.slice(-1) === ",") {
    trailing = "," + trailing;
    token = token.slice(0, -1);
  }
  var at = token.indexOf("=");
  if (at < 0) return mark("s-name", token) + trailing;
  return mark("s-name", token.slice(0, at)) + mark("s-punc", "=") +
         mark("s-value", token.slice(at + 1)) + trailing;
}

function tokens(text, asWord) {
  return text.split(/(\\s+)/).map(function (word) {
    return !word.trim() ? word : asWord(word);
  }).join("");
}

// What is marked as likely wrong is only what the tables know: names. Values are
// left unjudged, % and deg and lists living there, and the board stays the judge
function badWrap(marked) {
  return '<span class="s-bad">' + marked + "</span>";
}

function validSelector(word) {
  var bare = word.toLowerCase().replace(/^,+|,+$/g, "");
  if (!bare) return true;
  if (bare === "board" || /^screen[ab]$/.test(bare)) return true;
  if (CATALOGUE && bare === CATALOGUE.audio) return true;
  if (/^strip[lr]([0-9][0-9,\\-]*)?$/.test(bare)) return true;
  if (/^out[0-9][0-9,\\-.rgb*]*$/.test(bare)) return true;
  // A group after a comma names its outputs bare: 2, 5-3, 3.r
  return /^[0-9][0-9,\\-]*(\\.(r|g|b|\\*))?$/.test(bare);
}

function checkedSetting(word, allowed) {
  var marked = settingTok(word);
  if (!allowed) return marked;
  var name = word.split("=")[0].replace(/,+$/, "").toLowerCase();
  if (name === "bg") name = "background";
  return allowed.indexOf(name) >= 0 ? marked : badWrap(marked);
}

function highlightLine(line, continuation, context, inScene) {
  var hash = line.indexOf("#");
  var body = hash < 0 ? line : line.slice(0, hash);
  var comment = hash < 0 ? "" : mark("s-comment", esc(line.slice(hash)));

  if (!body.trim()) return esc(body) + comment;
  if (body.replace(/^\\s+/, "").slice(0, 1) === "[")
    return mark("s-scene", esc(body)) + comment;

  var at = body.indexOf(":");
  if (at < 0) {
    // A continuation line carries only settings; anything else continues nothing
    if (!continuation) return badWrap(esc(body)) + comment;
    var allowed = context && CATALOGUE && context.effect
                ? effectTakes(context.effect, context.kind) : null;
    return tokens(esc(body), function (word) {
      return word.indexOf("=") >= 0 ? checkedSetting(word, allowed) : word;
    }) + comment;
  }

  var opening = body.slice(0, at).match(/^\\s*([^\\s]+)/);
  var kind = opening ? targetKind(opening[1]) : "output";
  // Sound does not follow scenes, so its entry belongs above every heading
  var misplaced = kind === "audio" && inScene;
  var leftAllowed = CATALOGUE
                  ? (kind === "board" ? [] : channelSettings(kind)) : null;

  var mono = false;
  var left = tokens(esc(body.slice(0, at)), function (word) {
    if (word.indexOf("=") >= 0) return checkedSetting(word, leftAllowed);
    if (kind === "output" && word.indexOf(".") >= 0) mono = true;
    var marked = mark("s-target", word);
    return validSelector(word) && !misplaced ? marked : badWrap(marked);
  });

  // The first bare word names the effect; a board entry is settings the whole way
  var named = false;
  var rightAllowed = CATALOGUE && kind === "board"
                   ? Object.keys(CATALOGUE.board_settings) : null;
  var right = tokens(esc(body.slice(at + 1)), function (word) {
    if (!named && word.indexOf("=") < 0) {
      named = true;
      var marked = mark("s-effect", word);
      if (!CATALOGUE) return marked;
      if (kind === "board") return badWrap(marked);
      var name = word.replace(/,+$/, "").toLowerCase();
      rightAllowed = effectTakes(name, kind);
      if (!rightAllowed) return badWrap(marked);
      // A colour effect has nothing to show on a channel driven as a plain light
      if (mono && CATALOGUE.effects[name].kind === "colour") return badWrap(marked);
      return marked;
    }
    return checkedSetting(word, rightAllowed);
  });

  return left + mark("s-colon", ":") + right + comment;
}

function paint(text) {
  var open = null;
  var inScene = false;
  var painted = text.split("\\n").map(function (line) {
    var body = line.split("#")[0];
    var context = open;
    var at = body.indexOf(":");
    if (body.replace(/^\\s+/, "").slice(0, 1) === "[") inScene = true;
    if (!body.trim() || body.replace(/^\\s+/, "").slice(0, 1) === "[") {
      open = null;
      context = null;
    } else if (at >= 0) {
      var opening = body.slice(0, at).match(/^\\s*([^\\s]+)/);
      var effect = null;
      body.slice(at + 1).split(/\\s+/).forEach(function (word) {
        if (word && word.indexOf("=") < 0 && !effect)
          effect = word.replace(/,+$/, "");
      });
      open = {kind: opening ? targetKind(opening[1]) : "output", effect: effect};
      context = null;
    }
    return highlightLine(line, !!context, context, inScene);
  });
  return painted.join("\\n") + "\\n";
}

// ---- where the caret stands, for offering what fits there ----------------------

function entryBefore(text, caret) {
  // The logical entry up to the caret: this line, plus the lines above it that
  // it continues, since an entry's colon is on its first line
  var lineStart = text.lastIndexOf("\\n", caret - 1) + 1;
  var lines = [text.slice(lineStart, caret)];
  while (lineStart > 0 && lines[0].split("#")[0].indexOf(":") < 0) {
    var previousStart = text.lastIndexOf("\\n", lineStart - 2) + 1;
    var previous = text.slice(previousStart, lineStart - 1).split("#")[0];
    if (!previous.trim() || previous.replace(/^\\s+/, "").slice(0, 1) === "[") break;
    lines.unshift(previous);
    lineStart = previousStart;
    if (previous.indexOf(":") >= 0) break;
  }
  return lines.join(" ");
}

// Which outputs these lines already drive, ranges and components expanded
function outputsUsed(lines) {
  var used = {};
  lines.forEach(function (line) {
    var body = line.split("#")[0];
    var at = body.indexOf(":");
    if (at < 0 || !/^\\s*out[0-9]/i.test(body)) return;
    body.slice(0, at).split(/\\s+/).forEach(function (word) {
      if (word.indexOf("=") >= 0) return;
      word.toLowerCase().split(",").forEach(function (token) {
        token = token.replace(/^out/, "").split(".")[0];
        var range = token.match(/^([0-9]+)-([0-9]+)$/);
        if (range) {
          var from = Math.min(+range[1], +range[2]);
          var to = Math.max(+range[1], +range[2]);
          for (var n = from; n <= to; n++) used[n] = true;
        } else if (/^[0-9]+$/.test(token)) {
          used[+token] = true;
        }
      });
    });
  });
  return used;
}

// The caret's own scene, its line left out, and the always-on section above the
// first heading. Above the first heading the two are one and the same
function sceneScope(text, caret) {
  var lines = text.split("\\n");
  var here = text.slice(0, caret).split("\\n").length - 1;
  function heading(line) {
    return line.split("#")[0].replace(/^\\s+/, "").slice(0, 1) === "[";
  }
  var start = 0;
  for (var up = here; up >= 0; up--)
    if (heading(lines[up])) { start = up + 1; break; }
  var end = lines.length;
  for (var down = here + 1; down < lines.length; down++)
    if (heading(lines[down])) { end = down; break; }
  var first = lines.length;
  for (var scan = 0; scan < lines.length; scan++)
    if (heading(lines[scan])) { first = scan; break; }
  return {
    scene: lines.slice(start, end).filter(function (_, index) {
      return start + index !== here;
    }),
    always: start > 0 ? lines.slice(0, first) : []
  };
}

function contextAt(text, caret) {
  var lineStart = text.lastIndexOf("\\n", caret - 1) + 1;
  var line = text.slice(lineStart, caret);
  if (line.indexOf("#") >= 0) return null;
  if (line.replace(/^\\s+/, "").slice(0, 1) === "[") return null;

  var entry = entryBefore(text, caret);
  var prefix = line.match(/[^\\s:]*$/)[0];
  var found = {prefix: prefix, target: null, kind: "output", effect: null,
               comma: false, used: {}};

  // A comma closes its token, so the caret stands at a fresh word
  if (prefix.slice(-1) === ",") {
    found.comma = true;
    found.prefix = prefix = "";
  }

  var before = entry.slice(0, entry.length - prefix.length);
  var colon = before.indexOf(":");
  found.left = colon < 0;

  var opening = entry.match(/^\\s*([^\\s:]+)/);
  if (opening) {
    found.target = opening[1];
    found.kind = targetKind(opening[1]);
  }

  // A component anywhere in the selector makes the channel a plain light, so a
  // colour effect has nothing there to show itself on
  if (colon >= 0 && found.kind === "output")
    found.mono = entry.slice(0, entry.indexOf(":")).split(/\\s+/).some(function (word) {
      return word.indexOf("=") < 0 && word.indexOf(".") >= 0;
    });

  // What the entry already sets, to the end of the caret's line, so a setting
  // is only ever offered once
  var lineEnd = text.indexOf("\\n", caret);
  var whole = entry + " " +
              text.slice(caret, lineEnd < 0 ? text.length : lineEnd).split("#")[0];
  whole.split(/[\\s,]+/).forEach(function (word) {
    var at = word.indexOf("=");
    if (at > 0) found.used[word.slice(0, at).toLowerCase()] = true;
  });

  if (colon < 0) {
    // A comma before the colon says another output comes next, which is the
    // writer's to number, so nothing is offered and the hint line explains
    found.mode = found.comma ? "more" : before.trim() ? "channel" : "target";
  } else {
    found.mode = found.kind === "board" ? "setting" : "effect";
    before.slice(colon + 1).split(/\\s+/).forEach(function (word) {
      if (word && word.indexOf("=") < 0 && !found.effect) {
        found.effect = word.replace(/,+$/, "");
        found.mode = "setting";
      }
    });
    // The first word of a new line may start a new entry or carry on the one
    // above, so both are offered until the word says which
    if (line.indexOf(":") < 0) {
      if (line.slice(0, line.length - prefix.length).trim() === "") {
        found.mode = "fresh";
      } else {
        // A first word shaped like a selector settles it: the line is a new
        // entry still waiting for its colon, not the one above carrying on
        var starts = line.match(/^\\s*([^\\s:]+)/);
        if (starts && /^(out[0-9]|screen[ab]|strip[lr]|board)/i.test(starts[1])) {
          found.target = starts[1];
          found.kind = targetKind(starts[1]);
          found.effect = null;
          found.mode = "channel";
          found.used = {};
          line.split(/[\\s,]+/).forEach(function (word) {
            var given = word.indexOf("=");
            if (given > 0) found.used[word.slice(0, given).toLowerCase()] = true;
          });
        }
      }
    }
  }

  var at = found.prefix.indexOf("=");
  if (at >= 0) {
    found.mode = "value";
    found.setting = found.prefix.slice(0, at);
    found.prefix = found.prefix.slice(at + 1);
  }

  if (found.mode === "target" || found.mode === "fresh") {
    var scope = sceneScope(text, caret);
    found.sceneUsed = outputsUsed(scope.scene);
    found.alwaysUsed = outputsUsed(scope.always);
  }
  return found;
}

function offers(found) {
  if (!found) return [];
  var out = [];
  var seen = found.prefix.toLowerCase();

  function offer(insert, hint) {
    if (insert.toLowerCase().slice(0, seen.length) === seen && insert !== found.prefix)
      out.push({insert: insert, hint: hint || ""});
  }

  // fade and ease are one setting written two ways, so each rules the other out
  function unused(name) {
    if (found.used[name.toLowerCase()]) return false;
    if (name === "fade" && found.used.ease) return false;
    if (name === "ease" && found.used.fade) return false;
    return true;
  }

  function channelOffers() {
    channelSettings(found.kind).forEach(function (name) {
      if (!unused(name)) return;
      var type = settingType(name, found.kind);
      offer(name + "=", CHANNEL_HINTS[name] || TYPE_HINTS[type] || "");
    });
    offer(": ", "then the effect");
  }

  function settingOffers() {
    var takes = found.kind === "board"
              ? (CATALOGUE ? Object.keys(CATALOGUE.board_settings) : [])
              : found.effect ? effectTakes(found.effect, found.kind) : null;
    (takes || []).forEach(function (name) {
      if (!unused(name)) return;
      var shown = BOARD_CASE[name] || name;
      var hint = found.kind === "board" ? BOARD_HINTS[name]
               : TYPE_HINTS[settingType(name, found.kind)];
      offer(shown + "=", hint || "");
    });
  }

  // A word already naming outputs can take more of them, one colour channel, or
  // go to its effect. Half-written punctuation leaves the numbers to the writer
  function selectorOffers() {
    if (/^out[0-9]/i.test(found.prefix) && found.prefix.slice(-1) === ".") {
      offer(found.prefix + "r", "just the red");
      offer(found.prefix + "g", "just the green");
      offer(found.prefix + "b", "just the blue");
      offer(found.prefix + "*", "all three, each its own light");
      return;
    }
    if (/[-.,]$/.test(found.prefix)) return;
    if (/^out[0-9]/i.test(found.prefix) || /^strip[lr][0-9]/i.test(found.prefix)) {
      var tail = found.prefix.split(",").pop();
      offer(found.prefix + ",", "another output after it: out1,3,5-7");
      if (/^[0-9]+$/.test(tail.replace(/^[a-z]+/i, "")))
        offer(found.prefix + "-", "a range to another output, run either way");
      if (/^out/i.test(found.prefix) && tail.indexOf(".") < 0)
        offer(found.prefix + ".", "one colour channel alone: .r .g .b, or .*");
      offer(found.prefix + ": ", "then the effect");
    } else if (/^(screen[ab]|strip[lr]|board|audio)$/i.test(found.prefix)) {
      offer(found.prefix + ": ", "then the effect");
    }
  }

  // One output by number: the first this scene does not drive yet, and beside it
  // the first held by the always-on section, which a scene may take over
  function dynamicOutput() {
    var free = null;
    var takeover = null;
    for (var n = 1; n <= 7; n++) {
      if (found.sceneUsed[n]) continue;
      if (found.alwaysUsed[n]) {
        if (takeover === null) takeover = n;
      } else if (free === null) {
        free = n;
      }
    }
    if (free !== null)
      offer("out" + free, free === 1 ? "one output" : "the next output not used here");
    if (takeover !== null)
      offer("out" + takeover, "takes over an always-on output while this scene shows");
  }

  function freshStarts() {
    dynamicOutput();
    TARGETS.forEach(function (pair) { offer(pair[0], pair[1]); });
    selectorOffers();
  }

  if (found.mode === "target") {
    freshStarts();

  } else if (found.mode === "channel") {
    channelOffers();

  } else if (found.mode === "effect") {
    effectNames(found.kind).forEach(function (name) {
      var effect = CATALOGUE.effects[name];
      if (found.mono && effect && effect.kind === "colour") return;
      var hint = effect && effect.kind === "colour" ? "brings its own colours" : "";
      offer(name, hint);
    });

  } else if (found.mode === "setting") {
    settingOffers();

  } else if (found.mode === "fresh") {
    // A new line under an entry: carrying it on comes first, a fresh start after
    // a dividing line
    settingOffers();
    var split = out.length;
    freshStarts();
    if (split && out.length > split) out.divider = split;

  } else if (found.mode === "value") {
    (valuesFor(found.setting, found.kind) || []).forEach(function (value) {
      offer(value);
    });
    // A pipe joins the parts of a value that has them; a comma after a value on
    // the left starts the next output group
    if (found.prefix) {
      var name = found.setting.toLowerCase();
      var piped = {fade: "rise|fall, each its own seconds",
                   ease: "rise|fall, each its own seconds",
                   offset: "x|y, * centring that side",
                   tile: "across|down",
                   hold: "one end|the other",
                   args: "the next argument"};
      if (piped[name])
        offer(found.prefix + "|", piped[name]);
      else if (name === "colour" && found.effect &&
               found.effect.toLowerCase() === "rgb_blink")
        offer(found.prefix + "|", "another colour to blink through");
      if (found.left && found.kind !== "screen" && found.kind !== "board")
        offer(found.prefix + ",", name === "colour"
              ? "a colour for each output"
              : "then another output with settings of its own");
    }
  }
  return out;
}

function hintFor(found) {
  if (!found) return "";
  if (!CATALOGUE)
    return "catalogue.js is not beside this page, so nothing can be suggested; " +
           "the copy on the FX drive has it";
  if (found.mode === "more")
    return "another output comes next: a number, or a range such as 5-3, " +
           "then its settings or the colon";
  if ((found.mode === "target" || found.mode === "fresh") &&
      /^out[0-9]/i.test(found.prefix))
    return "outputs join with commas, ranges run either way, and .r .g .b " +
           "or .* takes one colour channel alone";
  if (found.mode === "value" || (found.mode === "setting" && found.prefix)) {
    var name = found.mode === "value" ? found.setting : found.prefix;
    if (found.kind === "board") return BOARD_HINTS[name.toLowerCase()] || "";
    // A drawing names a Python file, which belongs in a Python editor
    if (found.effect === "graphics" && name.toLowerCase().indexOf("file") === 0)
      return "a Python file with a draw(canvas, elapsed) in it, written in Thonny " +
             "or VS Code rather than here";
    var type = settingType(name, found.kind);
    return type ? name.replace(/,+$/, "") + ": " +
                  (CHANNEL_HINTS[name.toLowerCase()] || TYPE_HINTS[type]) : "";
  }
  if (found.effect) {
    var takes = effectTakes(found.effect, found.kind);
    if (takes) return found.effect + " takes: " + takes.join(", ");
  }
  if (found.kind === "audio")
    return "one sound plays at a time, and its entry sits above every scene heading";
  if (found.mode === "channel")
    return "before the colon: how the " +
           (found.kind === "screen" ? "screen is set" : "lights are set");
  return "";
}

// ---- the page -----------------------------------------------------------------

var entry = document.getElementById("entry");
var painted = document.getElementById("painted");
var paintBox = document.getElementById("paint");
var suggest = document.getElementById("suggest");
var hintLine = document.getElementById("hint");

var STARTER = "# One entry per line: which lights, a colon, then the effect.\\n" +
              "# Settings you leave out take their usual value.\\n\\n" +
              "board: reload=auto\\n\\n" +
              "out1-7: rainbow_wave speed=0.3\\n";

var state = {dirHandle: null, fileHandle: null, offered: [], rows: [], lit: 0};

function repaint() {
  painted.innerHTML = paint(entry.value);
  // The box grows with the file, a spare row deep, so the text never scrolls
  // vertically inside it and the page carries a long file instead
  var rowHeight = parseFloat(getComputedStyle(entry).lineHeight);
  var wanted = (entry.value.split("\\n").length + 1) * rowHeight + 48;
  paintBox.parentNode.style.height = Math.max(384, wanted) + "px";
  paintBox.scrollTop = entry.scrollTop;
  paintBox.scrollLeft = entry.scrollLeft;
}

function banner(text, warn, detail) {
  var box = document.getElementById("banners");
  box.innerHTML = "";
  if (!text) return;
  var note = document.createElement("div");
  // warn may also be "hold", the amber of a check still running
  note.className = warn === "hold" ? "banner hold" : warn ? "banner warn" : "banner";
  note.textContent = text;
  if (detail) {
    var lines = document.createElement("pre");
    lines.textContent = detail;
    note.appendChild(lines);
  }
  box.appendChild(note);
}

// Where the caret's line sits on the screen, found by mirroring the text up to it
function caretPlace() {
  var mirror = document.createElement("div");
  var styles = getComputedStyle(entry);
  ["font", "whiteSpace", "tabSize"].forEach(function (key) {
    mirror.style[key] = styles[key];
  });
  mirror.style.position = "absolute";
  mirror.style.visibility = "hidden";
  mirror.style.whiteSpace = "pre";
  var upTo = entry.value.slice(0, entry.selectionStart);
  mirror.textContent = upTo.slice(upTo.lastIndexOf("\\n") + 1);
  document.body.appendChild(mirror);
  var width = mirror.offsetWidth;
  document.body.removeChild(mirror);

  var rect = entry.getBoundingClientRect();
  var rowHeight = parseFloat(styles.lineHeight);
  var lineTop = rect.top + parseFloat(styles.paddingTop) +
                (upTo.split("\\n").length - 1) * rowHeight - entry.scrollTop;
  return {
    left: rect.left + parseFloat(styles.paddingLeft) + width - entry.scrollLeft,
    below: lineTop + rowHeight + 2,
    above: lineTop - 2
  };
}

function showSuggestions() {
  var caret = entry.selectionStart;
  if (caret !== entry.selectionEnd) return hideSuggestions();
  var found = contextAt(entry.value, caret);
  hintLine.textContent = hintFor(found);

  var offered = offers(found);
  if (!offered.length) return hideSuggestions();

  state.offered = offered;
  state.found = found;
  state.lit = 0;
  state.rows = [];
  suggest.innerHTML = "";
  offered.slice(0, 40).forEach(function (one, index) {
    if (index && index === offered.divider) {
      var rule = document.createElement("div");
      rule.className = "rule";
      suggest.appendChild(rule);
    }
    var row = document.createElement("div");
    var name = document.createElement("span");
    name.textContent = one.insert;
    row.appendChild(name);
    if (one.hint) {
      var why = document.createElement("small");
      why.textContent = one.hint;
      row.appendChild(why);
    }
    if (index === 0) row.className = "lit";
    row.onmousedown = function (event) {
      event.preventDefault();
      accept(index);
    };
    suggest.appendChild(row);
    state.rows.push(row);
  });
  // Placed below the caret's line, or above it where the screen runs out
  suggest.style.visibility = "hidden";
  suggest.className = "suggest shown";
  var place = caretPlace();
  var top = place.below;
  if (top + suggest.offsetHeight > window.innerHeight - 8)
    top = Math.max(8, place.above - suggest.offsetHeight);
  suggest.style.top = top + "px";
  suggest.style.left = Math.max(8, Math.min(place.left,
      window.innerWidth - suggest.offsetWidth - 8)) + "px";
  suggest.style.visibility = "";
}

function hideSuggestions() {
  suggest.className = "suggest";
  state.offered = [];
}

function light(index) {
  var count = state.rows.length;
  state.lit = (index + count) % count;
  state.rows.forEach(function (row, i) {
    row.className = i === state.lit ? "lit" : "";
  });
  state.rows[state.lit].scrollIntoView({block: "nearest"});
}

function accept(index) {
  var one = state.offered[index === undefined ? state.lit : index];
  if (!one) return;
  var caret = entry.selectionStart;
  var start = caret - state.found.prefix.length;
  // The colon closes the word before it, so it steps back over the gap
  if (one.insert.slice(0, 1) === ":")
    while (start > 0 && entry.value[start - 1] === " ") start--;
  entry.focus();
  entry.setSelectionRange(start, caret);
  // insertText keeps the undo history; setRangeText is the fallback without it
  if (!document.execCommand("insertText", false, one.insert))
    entry.setRangeText(one.insert, start, caret, "end");
  hideSuggestions();
  changed();
}

function changed() {
  repaint();
  try { localStorage.setItem("fx-editor-draft", entry.value); } catch (e) {}
  showSuggestions();
}

entry.addEventListener("input", changed);
entry.addEventListener("scroll", function () {
  paintBox.scrollTop = entry.scrollTop;
  paintBox.scrollLeft = entry.scrollLeft;
  hideSuggestions();
});
// The dropdown is pinned to the screen, so anything moving under it lets go of it
window.addEventListener("resize", hideSuggestions);
window.addEventListener("scroll", function (event) {
  if (event.target instanceof Node && suggest.contains(event.target)) return;
  hideSuggestions();
}, true);
entry.addEventListener("click", showSuggestions);
entry.addEventListener("blur", function () {
  setTimeout(hideSuggestions, 150);
});
entry.addEventListener("keydown", function (event) {
  if (!state.offered.length) {
    if (event.key === " " && event.ctrlKey) {
      event.preventDefault();
      showSuggestions();
    }
    return;
  }
  if (event.key === "ArrowDown") { event.preventDefault(); light(state.lit + 1); }
  else if (event.key === "ArrowUp") { event.preventDefault(); light(state.lit - 1); }
  else if (event.key === "Tab" || event.key === "Enter") {
    event.preventDefault();
    accept();
  }
  else if (event.key === "Escape") hideSuggestions();
});

// ---- the drive ------------------------------------------------------------------

// ---- remembering the drive ------------------------------------------------------

// The drive's handle survives in IndexedDB, so after the first visit it is reached
// with one click and a permission bubble instead of the file dialog every time. A
// page cannot go looking for the drive itself; remembering the answer is what there
// is. Anything failing in here falls back to the dialog
function rememberDrive(handle) {
  try {
    var open = indexedDB.open("fx-pages", 1);
    open.onupgradeneeded = function () { open.result.createObjectStore("handles"); };
    open.onsuccess = function () {
      try {
        open.result.transaction("handles", "readwrite")
            .objectStore("handles").put(handle, "drive");
      } catch (e) {}
    };
  } catch (e) {}
}

function rememberedDrive() {
  return new Promise(function (settle) {
    try {
      var open = indexedDB.open("fx-pages", 1);
      open.onupgradeneeded = function () { open.result.createObjectStore("handles"); };
      open.onerror = function () { settle(null); };
      open.onsuccess = function () {
        try {
          var ask = open.result.transaction("handles").objectStore("handles").get("drive");
          ask.onsuccess = function () { settle(ask.result || null); };
          ask.onerror = function () { settle(null); };
        } catch (e) { settle(null); }
      };
    } catch (e) { settle(null); }
  });
}

async function pickDrive() {
  var kept = await rememberedDrive();
  if (kept) {
    try {
      if (await kept.requestPermission({mode: "readwrite"}) === "granted") {
        await kept.getFileHandle("effects.txt");
        return kept;
      }
    } catch (e) {}
  }
  var picked;
  try {
    picked = await window.showDirectoryPicker(
        kept ? {mode: "readwrite", startIn: kept} : {mode: "readwrite"});
  } catch (e) {
    if (e.name === "AbortError") throw e;
    picked = await window.showDirectoryPicker({mode: "readwrite"});
  }
  rememberDrive(picked);
  return picked;
}

async function connect() {
  var dir = await pickDrive();
  state.dirHandle = dir;
  state.fileHandle = await dir.getFileHandle("effects.txt");
  var onBoard = await (await state.fileHandle.getFile()).text();
  var held = entry.value.trim();
  if (onBoard.trim() !== held && (!held || held === STARTER.trim() ||
      confirm("Load effects.txt from the drive and replace what is written here? " +
              "Undo (Ctrl+Z) brings your text back."))) {
    // Through the undo history, so what was here is one Ctrl+Z away
    entry.focus();
    entry.setSelectionRange(0, entry.value.length);
    if (!document.execCommand("insertText", false, onBoard)) entry.value = onBoard;
    entry.setSelectionRange(0, 0);
    repaint();
  }
  document.getElementById("check").disabled = false;
  document.getElementById("status").textContent = "connected to the drive";
  // The next thing to do carries the colour: opening first, then saving
  var open = document.getElementById("open");
  open.className = "";
  open.textContent = "Open a different drive";
  var save = document.getElementById("save");
  save.className = "primary";
  save.disabled = false;
}

document.getElementById("open").onclick = async function () {
  try {
    await connect();
    banner("");
  } catch (e) {
    banner("Could not open the drive: " + e.name + ". Is it showing? " +
           "A double press of the board's button brings it back.", true);
  }
};


// ---- waiting for the board -----------------------------------------------------

// Only the board writes errors.txt, and only where it has re-read the file, so a
// change there is proof it acted. It answers a save in about four seconds.
//
// Never read effects.txt while waiting. A read of the file just saved holds off the
// write the computer still has in hand, and the board then waits half a minute to
// see it, measured 2026-08-22
// The board answers a save in about four seconds, so silence is worth reporting at
// six and watching quietly after, rather than sitting on the answer until the last
// poll. A change to errors.txt is proof either way and ends the wait at once
var BOARD_SETTLE_MS = 6000;
var BOARD_WAIT_MS = 15000;
var BOARD_POLL_MS = 250;

function playsItself(text) {
  return /\\breload\\s*=\\s*auto\\b/i.test(text);
}

// Written into errors.txt before saving, so the board's answer is always a
// change: it deletes the file where the save reads clean and rewrites it where
// not, so this line vanishing is the answer either way. Self-describing, since a
// board that never reads the file leaves it to be found later
var CHECKING = "The board has not read the file yet.";

// Writes the marker; returns whether it took, a full drive being the reason not
async function markChecking() {
  try {
    var handle = await state.dirHandle.getFileHandle("errors.txt", {create: true});
    var writable = await handle.createWritable();
    await writable.write(CHECKING + "\\n");
    await writable.close();
    return true;
  } catch (e) {
    return false;
  }
}

// The text of errors.txt, null where there is none, and false where the drive is
// away mid-reload and the question cannot be answered yet
async function readErrors() {
  try {
    var handle = await state.dirHandle.getFileHandle("errors.txt");
    return (await (await handle.getFile()).text()).trim();
  } catch (e) {
    return e.name === "NotFoundError" ? null : false;
  }
}

// Polls until errors.txt differs from what it said before the save, calling
// nothingYet() once the settle time passes, saying the check is still running: an
// answer can arrive after the settle, so nothing is claimed until the wait is over.
// Seeing the drive away is proof the board acted, so an unchanged answer after that
// is a real answer rather than an early one
async function waitForBoard(before, nothingYet) {
  var deadline = Date.now() + BOARD_WAIT_MS;
  var settled = Date.now() + BOARD_SETTLE_MS;
  var wentAway = false;
  var told = false;
  while (Date.now() < deadline) {
    await new Promise(function (settle) { setTimeout(settle, BOARD_POLL_MS); });
    var now = await readErrors();
    if (now === false) {
      wentAway = true;
      continue;
    }
    if (now !== before) return now;
    if (wentAway) return now;
    if (!told && Date.now() > settled) {
      nothingYet();
      told = true;
    }
  }
  return before;
}

// What to say once the wait is over. Silence cannot be told from a board that has
// not got there yet, so it is reported as nothing said rather than as all well
function sayWhatHappened(said, also) {
  if (said === CHECKING)
    banner("The board did not pick the save up. Eject the FX drive, or press " +
           "the board's button once, and it plays.", true);
  else if (said)
    banner("The board wasn't happy with some of it:", true, said);
  else
    banner("Playing on the board. No problems reported." + (also || ""));
}

document.getElementById("save").onclick = async function () {
  try {
    if (!state.fileHandle) await connect();
    var text = entry.value;
    // The board acts on a save only where the file it is already running asked it to,
    // so the first save that turns it on still needs an eject
    var running = await (await state.fileHandle.getFile()).text();
    var errorsBefore = playsItself(running) ? await readErrors() : undefined;
    // The marker makes the answer an edge even where nothing else changes
    if (errorsBefore !== undefined && await markChecking()) errorsBefore = CHECKING;
    var writable = await state.fileHandle.createWritable();
    await writable.write(text);
    await writable.close();
    var back = await (await state.fileHandle.getFile()).text();
    if (back !== text) throw new Error("the file read back differently");
    if (errorsBefore === undefined) {
      banner("On its way. " + (playsItself(text)
             ? "Eject the FX drive, or press the board's button once, to play this one. "
               + "From now on a save plays on its own."
             : "Eject the FX drive on this computer, and the board plays it. Double-press "
               + "the board's button to bring the drive back, then ask 'Did it work?'."));
      return;
    }
    banner("Saved. Waiting for the board to pick it up...", "hold");
    var was = errorsBefore === false ? null : errorsBefore;
    sayWhatHappened(await waitForBoard(was, function () {
      banner("Playing on the board. Checking for problems...", "hold");
    }));
  } catch (e) {
    if (e.name === "QuotaExceededError") {
      // The drive is there, it is simply full: saving writes a temporary copy
      // first, so it needs the file's size free
      banner("The FX drive is full, so there was no room to save. Delete a " +
             "picture or sound from it and try again.", true);
      return;
    }
    state.fileHandle = null;
    state.dirHandle = null;
    banner("That didn't reach the board: " + e.name + ". Is the FX drive showing? " +
           "A double press of its button brings it back; then try again.", true);
  }
};

document.getElementById("check").onclick = async function () {
  // A blink before the answer, so asking again visibly did something even when
  // the answer reads the same
  banner("Asking the board...", "hold");
  await new Promise(function (settle) { setTimeout(settle, 350); });
  try {
    var handle = await state.dirHandle.getFileHandle("errors.txt");
    var text = await (await handle.getFile()).text();
    if (text.trim() === CHECKING) {
      banner("The board has not read the file yet. Eject the FX drive, or press " +
             "the board's button once.", "hold");
      return;
    }
    banner("The board wasn't happy with some of it:", true, text.trim());
  } catch (e) {
    if (e.name === "NotFoundError")
      banner("Nothing reported. The board found no problem with the file.");
    else
      banner("Couldn't look: " + e.name + ". Is the drive showing?", true);
  }
};

var draft = null;
try { draft = localStorage.getItem("fx-editor-draft"); } catch (e) {}
entry.value = draft || STARTER;
repaint();
</script>
</body>
</html>
"""

CATALOGUE = """\
// Generated from the autofx tables. Do not edit.
var CATALOGUE = {
 "effects": {
  "binary_counter": {
   "kind": "mono",
   "takes": [
    "interval",
    "count",
    "step"
   ]
  },
  "blink": {
   "kind": "mono",
   "takes": [
    "speed",
    "phase",
    "duty"
   ]
  },
  "blink_wave": {
   "kind": "mono",
   "takes": [
    "speed",
    "length",
    "phase",
    "duty"
   ]
  },
  "flash": {
   "kind": "mono",
   "takes": [
    "speed",
    "flashes",
    "window",
    "phase",
    "duty"
   ]
  },
  "flash_sequence": {
   "kind": "mono",
   "takes": [
    "speed",
    "length",
    "flashes",
    "window",
    "phase",
    "duty"
   ]
  },
  "flicker": {
   "kind": "mono",
   "takes": [
    "brightness",
    "dimness",
    "bright_min",
    "bright_max",
    "dim_min",
    "dim_max"
   ]
  },
  "hsv": {
   "kind": "colour",
   "takes": [
    "hue",
    "sat",
    "val"
   ]
  },
  "hue_step": {
   "kind": "colour",
   "takes": [
    "interval",
    "hue",
    "sat",
    "val",
    "steps"
   ]
  },
  "none": {
   "kind": "mono",
   "takes": []
  },
  "pelican_crossing": {
   "kind": "mono",
   "takes": [
    "red_interval",
    "flashing_interval",
    "green_interval",
    "amber_interval"
   ]
  },
  "pulse": {
   "kind": "mono",
   "takes": [
    "speed",
    "phase"
   ]
  },
  "pulse_wave": {
   "kind": "mono",
   "takes": [
    "speed",
    "length",
    "phase"
   ]
  },
  "rainbow": {
   "kind": "colour",
   "takes": [
    "speed",
    "sat",
    "val"
   ]
  },
  "rainbow_wave": {
   "kind": "colour",
   "takes": [
    "speed",
    "length",
    "sat",
    "val"
   ]
  },
  "random": {
   "kind": "mono",
   "takes": [
    "interval",
    "brightness_min",
    "brightness_max"
   ]
  },
  "rgb": {
   "kind": "colour",
   "takes": [
    "red",
    "green",
    "blue"
   ]
  },
  "rgb_blink": {
   "kind": "colour",
   "takes": [
    "colour",
    "speed",
    "phase",
    "duty"
   ]
  },
  "static": {
   "kind": "mono",
   "takes": [
    "brightness"
   ]
  },
  "sweep": {
   "kind": "mono",
   "takes": [
    "speed",
    "length",
    "extent",
    "hold"
   ]
  },
  "traffic_light": {
   "kind": "mono",
   "takes": [
    "red_interval",
    "red_amber_interval",
    "green_interval",
    "amber_interval"
   ]
  }
 },
 "screen_effects": {
  "gif": [
   "file",
   "fps",
   "interval",
   "loop",
   "ping_pong",
   "first_as_last",
   "hold"
  ],
  "graphics": [
   "file",
   "fps",
   "interval",
   "width",
   "height"
  ],
  "image": [
   "file"
  ],
  "sequence": [
   "folder",
   "fps",
   "interval",
   "loop",
   "ping_pong",
   "first_as_last",
   "hold"
  ]
 },
 "audio": "audio",
 "audio_effects": {
  "wav": [
   "file",
   "loop"
  ]
 },
 "settings": {
  "speed": "number",
  "phase": "fraction",
  "duty": "fraction",
  "window": "fraction",
  "length": "count",
  "flashes": "count",
  "steps": "count",
  "extent": "span",
  "brightness": "fraction",
  "brightness_min": "fraction",
  "brightness_max": "fraction",
  "dimness": "fraction",
  "bright_min": "seconds",
  "bright_max": "seconds",
  "dim_min": "seconds",
  "dim_max": "seconds",
  "interval": "seconds",
  "hold": "seconds",
  "count": "whole",
  "step": "whole",
  "red_interval": "seconds",
  "red_amber_interval": "seconds",
  "flashing_interval": "seconds",
  "green_interval": "seconds",
  "amber_interval": "seconds",
  "red": "byte",
  "green": "byte",
  "blue": "byte",
  "hue": "angle",
  "sat": "fraction",
  "val": "fraction",
  "colour": "colour",
  "file": "name",
  "folder": "name",
  "fps": "number",
  "loop": "boolean",
  "ping_pong": "boolean",
  "first_as_last": "boolean",
  "width": "count",
  "height": "count"
 },
 "colours": [
  "black",
  "blue",
  "cool",
  "cyan",
  "green",
  "magenta",
  "red",
  "warm",
  "white",
  "yellow"
 ],
 "channel_kinds": {
  "level": "fraction",
  "fade": "seconds",
  "ease": "seconds",
  "backlight": "fraction",
  "rotation": "quarter",
  "mirror": "boolean",
  "pixel_double": "boolean"
 },
 "screen_ports": [
  "screena",
  "screenb"
 ],
 "strips": [
  "stripl",
  "stripr"
 ],
 "output_settings": [
  "level",
  "colour",
  "fade",
  "ease"
 ],
 "screen_settings": [
  "backlight",
  "rotation",
  "mirror",
  "offset",
  "background",
  "pixel_double",
  "tile"
 ],
 "tiling": [
  "off",
  "repeat",
  "mirror"
 ],
 "board_settings": {
  "drive": [
   "manual"
  ],
  "reload": [
   "manual",
   "auto"
  ],
  "program": null,
  "args": null,
  "screena": [
   "2.8",
   "1.54"
  ],
  "screenb": [
   "2.8",
   "1.54"
  ],
  "stripl": null,
  "stripr": null
 }
};
"""
