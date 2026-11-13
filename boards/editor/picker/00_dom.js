export function h(tag, props, ...children) {
  var element = tag.indexOf("svg:") === 0
    ? document.createElementNS("http://www.w3.org/2000/svg", tag.slice(4))
    : document.createElement(tag);
  Object.entries(props || {}).forEach(function ([key, value]) {
    if (value === null || value === undefined || value === false) return;
    if (key.indexOf("on") === 0) element.addEventListener(key.slice(2), value);
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

export function replace(element, ...children) {
  element.replaceChildren();
  return append(element, children);
}
