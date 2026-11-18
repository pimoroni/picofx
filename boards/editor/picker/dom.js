// ---- building elements ----------------------------------------------------------------------
// The element builder the parts make their markup with, so the code reads as the tree it makes.

// Make an element, "svg:" before the tag for one in the SVG namespace, with its properties and
// children. A property named on... is set as the element's handler, as onclick, so code that clears
// or calls a handler finds it there. style takes CSS properties, text the element's text and html
// its markup. Anything else is set as a property where the element has one that can be set, and as
// an attribute otherwise, true as a bare attribute. A property null, undefined or false is left
// out, as is such a child. Children may be nested in arrays, and anything not a node becomes text
export function h(tag, props, ...children) {
  var element = tag.indexOf("svg:") === 0
    ? document.createElementNS("http://www.w3.org/2000/svg", tag.slice(4))
    : document.createElement(tag);
  Object.entries(props || {}).forEach(function ([key, value]) {
    if (value === null || value === undefined || value === false) return;
    if (key.indexOf("on") === 0) element[key] = value;
    else if (key === "style") Object.entries(value).forEach(function ([name, set]) {
      if (set !== null && set !== undefined) element.style.setProperty(name, set);
    });
    else if (key === "text") element.textContent = value;
    else if (key === "html") element.innerHTML = value;
    else if (settable(element, key)) element[key] = value;
    else element.setAttribute(key, value === true ? "" : value);
  });
  append(element, children);
  return element;
}

// Whether a key is set as a property, as disabled or value are, which on an SVG element none is
function settable(element, key) {
  if (element instanceof SVGElement || !(key in element) || typeof element[key] === "function") return false;
  for (var holder = element; holder; holder = Object.getPrototypeOf(holder)) {
    var described = Object.getOwnPropertyDescriptor(holder, key);
    if (described) return !!described.set || !!described.writable;
  }
  return false;
}

function append(element, children) {
  children.flat(Infinity).forEach(function (child) {
    if (child === null || child === undefined || child === false) return;
    element.appendChild(child instanceof Node ? child : document.createTextNode(String(child)));
  });
  return element;
}

// Empty an element and fill it with the children given, as h() takes them
export function replace(element, ...children) {
  element.replaceChildren();
  return append(element, children);
}
