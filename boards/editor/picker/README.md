# Picker

`tools/build_editor.py` builds each board's picker from this folder, twice:

- `boards/<BOARD>/editor/picker.html`, kept in the repository. It links every stylesheet and
  imports every module from here as they are, so a change shows on reload. Modules need a
  server, not `file://`:

  ```sh
  python3 -m http.server 8765
  ```

  then open `http://127.0.0.1:8765/boards/PIMORONI_MIGHTYFX/editor/picker.html`. Every module's
  exports are on `window` there, for the console and the tests.
- The page the FX drive carries, packed into `fx_libs/fx_editor.py`: one file, with the
  stylesheets and modules bundled and minified by esbuild.

The build needs the pinned tools in `tools/picker`:

```sh
npm ci --prefix tools/picker
```

## Layout

- `page.html` is the page's skeleton. `__STYLES__` becomes the stylesheets, in number order, and
  `__BUILD__` the board's description and the version, which `01_looks.js` reads.
- A folder named after a feature (`screens`, `hub`, `sound`, `sensor`, `discover`) is taken only
  by a board with that feature. Nested, as `discover/screens/`, it needs both.
- A part's stylesheet shares its name: `31_stretch_bar.js` and `31_stretch_bar.css`.
- `99_start.js` starts the page: it lists what a draw renders, in order, and draws.

## Modules

Each part is a module. It imports what it uses and exports what other parts or the tests use:

```js
import {h, replace} from "./00_dom.js";
import {draw} from "./00_draw.js";
import {pick} from "./03_runs.js";

export function renderStretches(where, run) { ... }
```

Parts load in number order, except that a part always loads after every part it imports. The
build refuses parts that import each other in a circle, so a lower layer never reaches up:

- `00_dom`, `00_draw`, `00_banner`: elements, the draw and paint steps, the banner.
- `01_colours`, `01_looks`, `02_blink`: colours, the catalogue's looks and their tuning.
- `03_outputs`, `03_lines`, `03_reading`, `03_kept`, `03_runs`: the board's outputs and wiring,
  writing and reading effect lines, lines kept from the file, the runs of lights and their
  stretches.
- `04_scenes`, `05_strips`, `07_board`, `07_writing`: scenes, strips, the board line, the file.
- `02_preview` and the views above it draw from those. None of them is imported by the model.

A lower part that needs something done by a higher one offers a hook and the higher part
registers with it: `drawSteps`, `paintSteps`, `bodyParts`, `connectSteps`, `programsReadSteps`,
`sceneHooks`, `screenHooks`, `addTab`. A part's state is written only by that part; others call
its setter (`activate`, `setLayout`, `setPrograms`).

A core part never imports a feature part. Features layer the same way, as `screens/` does from
`12_screens` (model) through `13_screen_art`, `14_screen_text`, `16_screen_settings` and
`17_screen_pair` to `18_screens_tab`.

After moving code between parts, run:

```sh
node tools/picker/fix_imports.js
node tools/picker/check_modules.js
```

`tools/picker/move.js from.js to.js name...` moves top-level declarations between parts,
`uses.js part.js` shows what each declaration uses, and `layer.js a.js b.js ...` reports what
has to move for those parts to only import downwards.

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

Nested CSS, one block per component, using the tokens in `00_base.css`'s `:root`: the `--text-*`
sizes, `--space-*` spacing, `--radius-*` corners and the colour palette.

## Tests

```sh
pytest tests/picker
```

Every board's picker reads the manual's entries and some scripted edits, and must write the
same file as `tests/picker/golden/`. `PICKER_GOLDEN=update` rewrites the goldens, only for a
change that is meant to alter the file. `test_shipped.py` runs the minified page from the module.
