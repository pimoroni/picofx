export function hexOf(rgb) {
  return rgb.map(function (v) {
    return ("0" + Math.round(v).toString(16)).slice(-2);
  }).join("");
}

function hueRgb(deg) {
  var h = ((deg % 360) + 360) % 360 / 60;
  var x = 255 * (1 - Math.abs((h % 2) - 1));
  var table = [[255, x, 0], [x, 255, 0], [0, 255, x],
               [0, x, 255], [x, 0, 255], [255, 0, x]];
  return table[Math.floor(h) % 6].map(Math.round);
}

function hueOf(rgb) {
  var top = Math.max.apply(null, rgb);
  var low = Math.min.apply(null, rgb);
  if (top === low || low > 0) return null;
  var span = top - low;
  var deg;
  if (top === rgb[0]) deg = ((rgb[1] - rgb[2]) / span) % 6;
  else if (top === rgb[1]) deg = (rgb[2] - rgb[0]) / span + 2;
  else deg = (rgb[0] - rgb[1]) / span + 4;
  deg *= 60;
  return (deg + 360) % 360;
}

export function takeApart(rgb) {
  var top = Math.max.apply(null, rgb) / 255;
  var low = Math.min.apply(null, rgb) / 255;
  return {hue: hueOf(rgb.map(function (v) {
            return top === low ? 0 : Math.round((v / 255 - low) / (top - low) * 255);
          })) || 0,
          sat: top ? (top - low) / top : 0,
          value: top};
}

export function hexRgb(hex) {
  return [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16),
          parseInt(hex.slice(5, 7), 16)];
}

export function astrayOf(side) {
  var wired = side.order.map(function (lamp) { return side.wiring.indexOf(lamp); });
  var count = wired.length;
  var upTo = [];
  var onFrom = [];
  for (var at = 0; at < count; at++) {
    upTo[at] = 1;
    for (var earlier = 0; earlier < at; earlier++) {
      if (wired[earlier] < wired[at]) upTo[at] = Math.max(upTo[at], upTo[earlier] + 1);
    }
  }
  for (var back = count - 1; back >= 0; back--) {
    onFrom[back] = 1;
    for (var later = back + 1; later < count; later++) {
      if (wired[later] > wired[back]) onFrom[back] = Math.max(onFrom[back], onFrom[later] + 1);
    }
  }
  var longest = Math.max.apply(null, upTo.concat([0]));
  var atStep = {};
  upTo.forEach(function (steps, place) {
    if (steps + onFrom[place] - 1 === longest) atStep[steps] = (atStep[steps] || 0) + 1;
  });
  return side.order.filter(function (lamp, place) {
    var onOne = upTo[place] + onFrom[place] - 1 === longest;
    return !(onOne && atStep[upTo[place]] === 1);
  });
}

export var WORDS = {
  red: [255, 0, 0], orange: [255, 128, 0], yellow: [255, 255, 0], green: [0, 255, 0],
  cyan: [0, 255, 255], blue: [0, 0, 255], purple: [128, 0, 255], magenta: [255, 0, 255],
  pink: [255, 128, 128], warm: [255, 192, 96], white: [255, 255, 255],
  cool: [96, 192, 255], black: [0, 0, 0]
};

export var SWATCHES = ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "magenta",
                "pink", "warm", "white", "cool"];

export function rgbInk(rgb) { return "rgb(" + rgb.join(",") + ")"; }

export function wordFor(hex) {
  var lower = hex.replace("#", "").toLowerCase();
  return SWATCHES.filter(function (name) { return hexOf(WORDS[name]) === lower; })[0] || null;
}

export function fieldColour(hue, sat) {
  return hueRgb(hue).map(function (v) { return Math.round(v + (255 - v) * (1 - sat)); });
}

export var FAINTEST = 0.05;

export function atBrightness(hex, level) {
  if (!(level < 1)) return hex;
  return "#" + hexOf(hexRgb(hex).map(function (v) { return Math.round(v * level); }));
}
