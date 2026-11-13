import {h} from "./00_dom.js";
import {WORDS, rgbInk} from "./05_effects.js";

export function swatchRow(options) {
  return h("ul", {class: "swatches", role: "radiogroup", "aria-label": options.label},
    options.names.map(function (name) {
      return h("li", {}, h("button", {type: "button", role: "radio", title: name,
                                      "aria-checked": String(!options.custom && options.chosen === name),
                                      style: {"--swatch": rgbInk(WORDS[name])},
                                      onclick: function () { options.onSwatch(name); }},
        h("span", {}, name)));
    }),
    h("li", {}, h("button", {type: "button", role: "radio", "data-custom": true,
                             "aria-checked": String(options.custom), title: options.customTitle,
                             style: {"--picked": options.picked || null},
                             onclick: options.onCustom},
      h("span", {}, "custom"))));
}

export function colourField(options) {
  var marker = h("span");
  var preview = h("output", {title: options.previewTitle});
  var hex = h("input", {type: "text", maxLength: 7, spellcheck: false, value: options.hex,
                        title: options.hexTitle,
                        oninput: function () {
                          var got = options.typed(hex.value.replace("#", "").trim().toLowerCase());
                          if (got) show(got);
                        },
                        onchange: options.done});

  function show(at) {
    marker.style.setProperty("--x", (at.hue / 360 * 100) + "%");
    marker.style.setProperty("--y", ((1 - at.sat) * 100) + "%");
    marker.style.setProperty("--colour", at.colour);
    preview.style.setProperty("--colour", at.preview);
    if (at.hex !== undefined) hex.value = at.hex;
  }

  function pointing(event) {
    var bounds = field.getBoundingClientRect();
    var across = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
    var down = Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height));
    show(Object.assign({hue: across * 360, sat: 1 - down}, options.pick(across * 360, 1 - down)));
  }

  var field = h("div", {class: "field", role: "presentation",
                        onpointerdown: function (event) {
                          field.setPointerCapture(event.pointerId);
                          pointing(event);
                        },
                        onpointermove: function (event) {
                          if (field.hasPointerCapture(event.pointerId)) pointing(event);
                        },
                        onpointerup: options.done}, marker);
  show(options.at);
  return h("div", {class: "colourfield"}, field, h("div", {}, h("label", {}, "Hex ", hex), preview));
}
