# Picker

`tools/build_editor.py` builds each board's `editor/picker.html` from this folder.

## Layout

- `page.html` is the page's skeleton. `__STYLES__` is replaced by every `NN_*.css` part and the
  script by every `NN_*.js` part, both in number order.
- A folder named after a feature (`screens`, `hub`, `sound`, `sensor`, `discover`) is taken only
  by a board with that feature. Nested, as `discover/screens/`, it needs both.
- A part's stylesheet shares its name: `31_stretch_bar.js` and `31_stretch_bar.css`.
- `99_start.js` starts the page, so every other part's top-level code has run by then.

## Modules

Each part is a module. It imports what it uses from other parts and exports what they use:

```js
import {h, replace} from "./00_dom.js";
import {draw, pick} from "./03_runs.js";

export function renderStretches(where, run) { ... }
```

The build checks every import resolves for each board, then joins the parts into one script.
After moving code between parts, run:

```sh
npm ci --prefix tools/picker
node tools/picker/fix_imports.js
node tools/picker/check_modules.js
```

A core part never imports a feature part. A feature registers with core instead, as the screens
part fills in `screenHooks` and `discover/screens` adds to `discoverKinds`.

## Markup

- Build elements with `h(tag, props, ...children)` from `00_dom.js`, and replace a region's
  contents with `replace(element, ...children)`.
- Use the element that says what a thing is: `section` and a heading for a region, `ol`/`ul` for
  lists, `button` for actions, `fieldset`/`legend` and `label` for settings, `output` for values.
- A component has one class on its root. Style its children by element or role under it.
- State is an attribute: `aria-current`, `aria-pressed`, `aria-expanded`, `disabled`, `hidden`,
  or `data-*`. Not toggled classes.
- Values that change go in as custom properties, `style: {"--wash": colour}`, not inline rules.
- One part owns a region and draws all of it. Other parts pass it data; they do not reach into
  its markup afterwards.

## Styles

Nested CSS, one block per component, using the tokens in `00_page.css`'s `:root`.
`00_page.css` is the old stylesheet, emptied as each region moves to its own part.

## Tests

```sh
pytest tests/picker
```

Every board's picker reads the manual's entries and some scripted edits, and must write the
same file as `tests/picker/golden/`. `PICKER_GOLDEN=update` rewrites the goldens, only for a
change that is meant to alter the file.
