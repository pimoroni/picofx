# Picker

`tools/build_editor.py` builds each board's picker from this folder, twice:

- `boards/<BOARD>/editor/picker.html`, kept in the repository. It is one whole, readable page,
  so it opens straight from disk with no server. Put the board's `catalogue.js` beside it, as
  the build does.
- The page the FX drive carries, packed into the board's `fx_libs/fx_editor.py`. It is the same
  page with its style and script minified by esbuild.

Rebuild after changing a part, `page.html`, the board's `editor/fx_board.json` or anything the
catalogue reads:

```sh
npm ci --prefix tools/picker
python3 tools/build_editor.py boards/PIMORONI_MIGHTYFX
```

`npm ci` installs the tools pinned in `tools/picker/package.json`, once: esbuild, and the parsers
the module scripts use. CI runs the module check, then the build with `--check` for every board,
and fails if a committed page or module is stale.

## Layout

- `page.html` is the page's head, stylesheet and markup. The build fills in `__BOARD_NAME__`,
  `__VERSION__` and `__BOARD__`, the board's description, which `01_looks.js` reads.
- Every other file is a part: a numbered script added to the page in number order, as
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

The build checks every import names a part the board takes and something that part exports,
then joins the parts into one script in number order, without the import and export lines.
A part's top-level statements run in that order, so a statement may only use what a part before
it has made.

A part for every board never imports from a feature folder. It reaches a feature's code through
a hook the feature fills in: `screenHooks` and `firmwareHooks` in `07_board.js`, and
`discoverKinds` in `discover/28_discover.js` for each kind of example other than a program.

After moving code between parts, rewrite the imports and check them:

```sh
node tools/picker/fix_imports.js
node tools/picker/check_modules.js
```

A part that needs work done by a later one offers a list, and the later part adds a function to
it:

- `drawSteps.before` and `drawSteps.after`, run on every `draw()`.
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
