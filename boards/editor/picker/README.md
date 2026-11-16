# Picker

`tools/build_editor.py` builds each board's picker from this folder. The parts are modules, which
esbuild bundles into:

- `boards/<BOARD>/editor/picker.html`, kept in the repository. It holds the parts as one
  readable script, so it opens straight from disk with no server. Put the board's
  `catalogue.js` beside it, as the build does.
- The page the FX drive carries, packed into the board's `fx_libs/fx_editor.py`. It is the same
  page with its style and script minified.

Rebuild after changing a part, `page.html`, the board's `editor/fx_board.json` or anything the
catalogue reads:

```sh
npm ci --prefix tools/picker
python3 tools/build_editor.py boards/PIMORONI_MIGHTYFX
```

`npm ci` installs the tools pinned in `tools/picker/package.json`, once: esbuild, and the parsers
the module scripts use. CI runs the module check, then the build with `--check` for every board,
and fails if a committed page or module is stale.

To work on the parts, `--dev` also writes `editor/picker.dev.html`, which loads them as modules,
so a change shows on reload. Modules load only from a server:

```sh
python3 tools/build_editor.py --dev boards/PIMORONI_MIGHTYFX
python3 -m http.server 8765
```

then open `http://127.0.0.1:8765/boards/PIMORONI_MIGHTYFX/editor/picker.dev.html`. The page is not
committed.

## Layout

- `page.html` is the page's head, stylesheet and markup. The build fills in `__BOARD_NAME__`,
  `__VERSION__` and `__BUILD__`, the board's description and the version, which `01_looks.js`
  reads.
- Every other file is a part: a numbered module, which runs after the parts it imports, as
  `05_strips.js` after `04_scenes.js`.
- A folder named after a feature (`screens`, `hub`, `sound`, `sensor`, `discover`, `firmware`) is
  taken only by a board whose description has that feature. Inside another, as
  `discover/screens/`, it is taken only where the board has both. Its parts are numbered among
  the rest, so `12_screens.js` loads between `11_tabs.js` and `13_sound.js`.
- A board can add parts of its own in its `editor/picker/` folder. They join the shared parts by
  number, and must not share a name with one.
- `99_start.js` is last. It draws the page once every part is in place.

## Parts

Each part imports what it uses from the parts that declare it, and exports what other parts use:

```js
import {draw} from "./00_draw.js";
import {pick, runs} from "./03_runs.js";

export function renderStripBar(where, run) { ... }
```

The build checks every import names a part the board takes and something that part exports, and
refuses parts that import each other in a circle. It then bundles the parts, each after every
part it imports and otherwise in number order, with `99_start.js` last. A part's top-level
statements run in that order, so a statement may only use what the parts it imports have made.

Nothing may depend on the order two independent parts run in. A list that parts add steps to
keeps them in an order its owner states, through `addStep()` in `00_draw.js`, such as
`DRAW_AFTER` for the draw and `BODY_ORDER` for a scene's share of each part. Building with
`PICKER_REVERSE_TIES=1` runs independent parts the other way round, to check.

A variable is written only by the part that declares it. Other parts call that part's function
to change it, such as `activate()`, `setLayout()` or `setPrograms()`.

A part for every board never imports from a feature folder. It reaches a feature's code through
a hook the feature fills in: `screenHooks` and `firmwareHooks` in `07_board.js`, `sceneHooks`
in `04_scenes.js` for the sensor part, and `discoverKinds` in `discover/28_discover.js` for each
kind of example other than a program.

After moving code between parts, rewrite the imports and check them:

```sh
node tools/picker/fix_imports.js
node tools/picker/check_modules.js
```

A part that needs work done by a later one offers a list or an object, and the later part adds
its function to it:

- `drawSteps.before` and `drawSteps.after`, run on every `draw()`, and `drawParts`, the named
  steps between them that `DRAW_ORDER` in `00_draw.js` puts in order, and `paintSteps`.
- `stripDrawing` in `05_strips.js`, `screenParts` in `screens/12_screens.js` and `hubParts` in
  `hub/15_hub.js`, which the later parts of the strips, screens and hub fill in.
- `programsReadingSteps` and `programsReadSteps`, as the drive's programs are read and once they
  are.
- `chosenSteps`, for the settings drawn under a chosen stretch.
- `boardLineSteps`, `bannerSteps`, `connectSteps`, `notFittedSteps`, `programCardSteps` and
  `programViewSteps`, at those points.
- `bodyParts`, for a part's own share of a scene, and `driveParts`, for the files a part keeps
  on the FX drive.

## Styles

The stylesheet is in `page.html`. Use its tokens, declared on `:root`, rather than literal
values:

- `--space-1` to `--space-7` for gaps, margins and padding, .125rem to 1.5rem.
- `--radius-xs` to `--radius-xl` and `--radius-round` for corners, 4px to 16px.
- `--text-xs` to `--text-xl` and `--text-display` for text sizes, 12px to 20px and 48px, and
  `--font` and `--font-mono` for the families.
- The palette: `--bg`, `--panel`, `--surface`, `--surface-2`, `--ink`, `--dim`, `--dim-strong`,
  `--line`, `--line-strong`, `--accent` and the rest, for every colour that is not white, a
  brand colour or a shade of black or white.
