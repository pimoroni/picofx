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
