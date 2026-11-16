import {
  BOARD, LOOKS, RISE_OF_DWELL, RISE_OF_FLASH, SETTING_NAMES, SIGNAL_TIMINGS, blinkDuty, blinkSpeed,
  lerp, lookNamed, marqueeGap, nameSet, numberIn, r2, riseFor, spreadLength, spreadStops, timingOf
} from "./looks.js";
import {OPENING_LOOK, blank, mono, outs, settle} from "./runs.js";

// ---- the looks and the opening stretch, once every part is in place -----------------------------
// The looks' own tuning and the looks added beside the catalogue's, then each run opened on one
// stretch playing the board's opening look. Each needs parts before it, so they run here.

(function (scanner, chase) {
  scanner.mood = "Trail";
  chase.mood = "Trail";
  var scannerLine = scanner.entries;
  scanner.entries = function (target, pace, mood) {
    return scannerLine(target, pace, 0.5).map(function (line) {
      var speed = numberIn(line, "speed", 1);
      var length = numberIn(line, "length", 2);
      var extent = numberIn(line, "extent", 1);
      var dwell = 2 * extent / (speed * Math.max(1, length - 1));
      return line.replace(/ fade=[\d.]+/, " fade=" + riseFor(RISE_OF_DWELL * dwell) + "|" +
                                          lerp(0.15, 2, mood));
    });
  };
  function chaseLines(lines, mood) {
    return lines.map(function (line) {
      var flash = numberIn(line, "window", 0.4) * 0.5 / numberIn(line, "speed", 1);
      return line.replace(/ fade=[\d.]+/, " fade=" + riseFor(RISE_OF_FLASH * flash) + "|" +
                                          lerp(0.05, 0.8, mood));
    });
  }
  var chaseLine = chase.entries, chaseAlone = chase.alone;
  chase.entries = function (target, pace, mood) {
    return chaseLines(chaseLine(target, pace, 0.5), mood);
  };
  chase.alone = function (target, pace, mood) {
    return chaseLines(chaseAlone(target, pace, 0.5), mood);
  };
}(lookNamed("Scanner"), lookNamed("Chase")));

LOOKS.splice(LOOKS.indexOf(lookNamed("Breathe")) + 1, 0, {
  name: "Blink", mood: "On time", spans: true, onMono: true,
  strip: ["#ff2d1a", "#111111", "#ff2d1a", "#111111", "#ff2d1a", "#111111", "#ff2d1a"],
  entries: function (target, pace, mood) {
    return [target.selector + " colour=red: blink speed=" + blinkSpeed(pace) +
            " duty=" + blinkDuty(mood)];
  },
  alone: function (target, pace, mood) {
    return this.entries(target, pace, mood);
  }
});

LOOKS.splice(LOOKS.indexOf(lookNamed("Chase")) + 1, 0, {
  name: "Marquee", mood: "Spacing", detents: 5, spans: true, onMono: true,
  strip: ["#ffc27a", "#111111", "#111111", "#ffc27a", "#111111", "#111111", "#ffc27a"],
  entries: function (target, pace, mood) {
    var gap = marqueeGap(mood);
    return [target.selector + " colour=warm: blink_wave speed=" + lerp(0.2, 1.5, pace) +
            " length=" + gap + " duty=" + r2(1 / gap)];
  },
  alone: function (target, pace, mood) {
    return [target.selector + " colour=warm: blink speed=" + lerp(0.2, 1.5, pace) +
            " duty=" + r2(1 / marqueeGap(mood))];
  }
});

// Red, red and amber, green, amber on three lamps, as Pelican crossing takes its five. It lands
// on the first three playing lights, and any beyond them are told to stay dark. The intervals
// keep a real signal's proportions, and the pace scales them all
LOOKS.splice(LOOKS.indexOf(lookNamed("Pelican crossing")), 0, {
  name: "Traffic light", mood: "Fade", spans: false, onMono: true,
  strip: ["#ff0000", "#ff7800", "#00d28c", "#111111", "#111111", "#111111", "#111111"],
  entries: function (target, pace, mood) {
    var scale = lerp(2, 0.4, pace);
    var lamps = target.playing.slice(0, 3);
    var rest = target.playing.slice(3);
    var colours = ["red", "ff7800", "00d28c"].slice(0, lamps.length);
    var lines = [nameSet(target, lamps) + " colour=" + colours.join(",") +
                 " ease=" + lerp(0.05, 0.6, mood) +
                 ": traffic_light red_interval=" + r2(12 * scale) +
                 " red_amber_interval=" + r2(2 * scale) +
                 " green_interval=" + r2(12 * scale) +
                 " amber_interval=" + r2(3 * scale)];
    if (rest.length) lines.push(nameSet(target, rest) + ": none");
    return lines;
  },
  alone: false
});
LOOKS.forEach(function (look) {
  if (SETTING_NAMES[look.name]) look.mood = SETTING_NAMES[look.name];
});

Object.keys(SIGNAL_TIMINGS).forEach(function (name) {
  var look = lookNamed(name);
  var ownLines = look.entries;
  look.entries = function (target, pace, mood) {
    return ownLines(target, pace, mood).map(function (line) {
      SIGNAL_TIMINGS[name].forEach(function (part) {
        line = line.replace(new RegExp(" " + part[0] + "=[\\d.]+"),
                            " " + part[0] + "=" + timingOf(name, part[0]));
      });
      return line;
    });
  };
});

(function (rainbow, wave) {
  rainbow.entries = function (target, pace, mood) {
    return [target.selector + ": rainbow_wave speed=" + lerp(0.05, 0.8, pace) +
            " length=" + spreadLength(target.count, mood)];
  };
  rainbow.detents = spreadStops;
  wave.entries = function (target, pace, mood) {
    return [target.selector + " colour=cool: pulse_wave speed=" + lerp(0.1, 1, pace) +
            " length=" + spreadLength(target.count, mood)];
  };
  wave.detents = spreadStops;
}(lookNamed("Rainbow"), lookNamed("Wave")));

// Campfire's intensity is how far its flicker dips. The effect's own brightness is held at full
// so the stretch's Brightness is the one that sets how bright it is. Its pace is the model's
(function (campfire) {
  campfire.entries = function (target, pace, mood) {
    return [target.selector + " colour=ff5a00: flicker_each dimness=" + lerp(0.15, 0.8, mood) +
            " bright_min=" + lerp(0.1, 0.02, pace) + " bright_max=" + lerp(0.4, 0.1, pace) +
            " dim_min=" + lerp(0.08, 0.02, pace) + " dim_max=" + lerp(0.3, 0.08, pace)];
  };
}(lookNamed("Campfire")));

outs.sections = [blank(0, outs.lamps.length - 1)];
outs.sections[0].look = OPENING_LOOK;
if (mono.lamps.length && BOARD.opening.mono) {
  mono.sections = [blank(0, mono.lamps.length - 1)];
  mono.sections[0].look = BOARD.opening.mono;
}
settle();
