# Picker

`tools/build_editor.py` builds each board's picker from this folder, twice:

- `boards/<BOARD>/editor/picker.html`, kept in the repository. It links every stylesheet and
  imports every module from here as they are, so a change shows on reload. Modules need a
  server, not `file://`:

  ```sh
  python3 -m http.server 8765
  ```

  then open `http://127.0.0.1:8765/boards/PIMORONI_MIGHTYFX/editor/picker.html`. The page loads
  only the parts nothing else imports: each feature's top part and `start.js`, which imports
  the rest of core.
- The page the FX drive carries, packed into `fx_libs/fx_editor.py`: one file, with the
  stylesheets and modules bundled and minified by esbuild.

The build needs the pinned tools in `tools/picker`:

```sh
npm ci --prefix tools/picker
```

## Layout

- `page.html` is the page's skeleton. `__STYLES__` becomes the stylesheets, `base.css` and
  `controls.css` first and the rest in the order their parts load, and
  `__BUILD__` the board's description and the version, which `looks.js` reads.
- A folder named after a feature (`screens`, `hub`, `sound`, `sensor`, `discover`) is taken only
  by a board with that feature. Nested, as `discover/screens/`, it needs both.
- A part's stylesheet shares its name: `stretch_bar.js` and `stretch_bar.css`.
- `start.js` is where core is put together: the draw sequence (settle, render, finish), the
  steps run on opening a drive, and the first draw once every part has loaded. A core part that
  only registers hooks is imported from here, as `import "./readback.js";`.

## Modules

Each part is a module. It imports what it uses and exports what other parts or the tests use:

```js
import {h, replace} from "./dom.js";
import {draw} from "./draw.js";
import {pick} from "./runs.js";

export function renderStretches(where, run) { ... }
```

A part always loads after every part it imports. The build refuses parts that import each other
in a circle, so a lower layer never reaches up:

- `dom`, `draw`, `banner`: elements, the draw and paint steps, the banner.
- `colours`, `blink`, `looks`: colours, blink patterns, the catalogue's looks and their tuning.
- `outputs`, `lines`, `reading`, `kept`, `runs`: the board's outputs and wiring, writing and
  reading effect lines, lines kept from the file, the runs of lights and their stretches.
- `scenes`, `strips`, `board`, `writing`: scenes, strips, the board line, the file.
- `preview` and the views above it draw from those. None of them is imported by the model.

A lower part that needs something done by a higher one offers a hook and the higher part
registers with it: `drawSteps`, `paintSteps`, `bodyParts`, `boardWords`, `programsReadSteps`,
`sceneHooks`, `screenHooks`, `addTab`.

Nothing may depend on the order two independent parts load in. Where order matters it is
stated: the start's draw and connect sequences, `WRITTEN_IN_ORDER` for a scene's lines,
`BOARD_LINE_ORDER` for the board line, `PART_ORDER` for a scene tab's icons, `FEATURE_TABS`.
CI runs the tests again with `PICKER_REVERSE_TIES=1`, which loads independent parts the other
way round.

A part's state is written only by that part; others call its setter (`activate`, `setLayout`,
`setPrograms`).

A core part never imports a feature part. Features layer the same way, as `screens/` does from
`screens` (model) through `screen_art`, `screen_text`, `screen_settings` and `screen_pair` to
`screens_tab`.

After moving code between parts, run:

```sh
node tools/picker/fix_imports.js
node tools/picker/check_modules.js
```

`tools/picker/move.js from.js to.js name...` moves top-level declarations between parts,
`uses.js part.js` shows what each declaration uses, and `layer.js a.js b.js ...` reports what
has to move for those parts to only import downwards.

## Markup

- Build elements with `h(tag, props, ...children)` from `dom.js`, and replace a region's
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

Nested CSS, one block per component, using the tokens in `base.css`'s `:root`: the `--text-*`
sizes, `--space-*` spacing, `--radius-*` corners and the colour palette.

## Tests

```sh
pytest tests/picker
```

Every board's picker reads the manual's entries and some scripted edits, and must write the
same file as `tests/picker/golden/`. `PICKER_GOLDEN=update` rewrites the goldens, only for a
change that is meant to alter the file. The tests put every module's exports on `window` to
drive the page. `test_shipped.py` runs the minified page from the module.
