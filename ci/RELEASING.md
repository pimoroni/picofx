# Preparing a picofx release for the picker's updater

The picker shows an "Update available" button beside its version when GitHub has a newer picofx
release than the board runs. Pressing it opens a sheet with the release notes, the steps to flash,
and one download for the board. This page lists what a release needs for that to work.

How the picker decides, in brief:

- It checks only after "Open FX drive" is pressed, by asking
  `https://api.github.com/repos/pimoroni/picofx/releases/latest`. The picker keeps the answer in
  the browser for 24 hours, and does not keep an answer with no file for the board.
- It compares the release's tag with the version built into the picker, which is the board's
  firmware version. A build made between releases shows "X preview" and counts as older than
  release X.
- It offers one file, `<stem>-v<tag>-pimoroni-micropython-with-libs.uf2`. The stems come from each
  board's `boards/<BOARD>/editor/fx_board.json`.

## Before tagging

1. **Set the version.** `PICOFX_VERSION` in `picofx/__init__.py` must equal the tag exactly, with
   no leading "v", such as `1.2.0`. CI's release build runs `tools/build_editor.py --release <tag>`,
   which stops if the two differ.
2. **Point Discover at main.** `DISCOVER_BRANCH` in
   `boards/editor/picker/discover/discover.js` must be `main`. The release build stops
   otherwise.
3. **Rebuild the examples indexes after setting the version.** Run
   `python3 tools/build_examples_index.py boards/<BOARD>` for each board whose `fx_board.json`
   names an `examples_index`, so each example's lowest firmware reads the new version, and commit
   the result before tagging. Each file's earlier versions are carried from the index at the
   previous release tag, so the index the tag holds becomes the next release's history. The picker
   needs that history to tell an older copy of an example from one the user changed.
4. **Check the file names still match.** The picker looks for the `-with-libs.uf2` image that
   `ci/micropython.sh` names for a drive build. If CI's file names or matrix shortnames change,
   update the `release` entries in each `fx_board.json` to match.

## Publishing the release

1. **Publish it directly.** Create the release and press "Publish release", not "Save draft".
   CI builds the `.uf2` files on the release's `created` event, and GitHub does not run workflows
   for a draft. A release saved as a draft and published later gets no files, and the picker then
   says "This release has no file for <board> yet."
2. **Do not mark it as a pre-release** if boards should be offered it. `releases/latest` skips
   pre-releases and drafts, so the picker never sees them.
3. **Wait for CI to upload the files.** Until they are attached, a picker that checks says the
   release has no file yet. It does not keep that answer, so the next "Open FX drive" asks again.
4. **Check the assets.** Each board's file should be listed:
   - `tiny_fx_drive-v<tag>-pimoroni-micropython-with-libs.uf2`
   - `tiny_fx_w_drive-v<tag>-pimoroni-micropython-with-libs.uf2`
   - `mighty_fx_drive-v<tag>-pimoroni-micropython-with-libs.uf2`
   - `plasma_2350_drive-v<tag>-pimoroni-micropython-with-libs.uf2`

## Writing the release notes

The sheet shows the release's own notes as plain text, under "What's new", with a link to the full
notes on GitHub.

- Use `##` headings and `-` bullets. Bold and code marks are removed, and a link shows its text
  only.
- Keep the top of the notes short and readable for someone who does not write code. Developer
  detail can follow under its own headings.
- Put API changes under `## Breaking`, as pimoroni-pico does. The picker shows that section as an
  ordinary part of the notes, since it does not affect someone using the picker.

### Warnings for picker users

A line that starts with `:warning:` is lifted out of the notes into an amber box at the top of the
sheet, and the Update available button turns amber. GitHub shows the code as the warning sign, and
a line starting with the sign itself works too, as does a GitHub `> [!WARNING]` or
`> [!CAUTION]` alert.

Use a warning only for something a picker user must act on before updating, such as a release that
empties the FX drive or changes the flash layout. For example:

```markdown
:warning: This release empties the FX drive. Copy your files off it before updating.
```

The sheet normally ends its steps with "Your FX drive and the files on it are kept." A release with
a warning replaces that line with "Read the warning at the top before you start.", so any release
that loses the user's files must carry one.

## After the release

1. **Bump the version.** Set `PICOFX_VERSION` to the next version straight away, so builds made
   from then on show "<next> preview". A build left at "<tag> preview" after the release is offered
   that same release.
2. **Test from a board.** Open the picker from the drive of a board on an older version and press
   "Open FX drive". A browser that checked in the last 24 hours keeps its earlier answer. To check
   again sooner, remove the `fx-picker-firmware-release` entry from the browser's local storage for
   the page.

## Adding a board

Give its `fx_board.json` a `release` entry:

```json
"release": {"files": {"<ci shortname>": "<board name>"}, "bootloader_drive": "RP2350",
            "reset_button": "RST"}
```

`bootloader_drive` is the name of the drive the board shows in BOOTSEL mode, `RPI-RP2` on an
RP2040 and `RP2350` on an RP2350. `reset_button` is the reset button's name in the update
steps, written as the picker writes BOOT as "Boot": `RST` where the board prints RST, and `Reset`
where it prints RESET. The board's `manual.json` gives the same name as its `RESET_BUTTON` term.
`tools/build_editor.py` includes the updater only for a board with a `release` entry.

A board whose wireless build is a separate firmware sharing the same pages, as Tiny FX W does,
lists that build under `wireless_files` and its plain build under `files`. The two builds place
the FX drive differently, so the wrong one empties it. The build then packs a second catalogue,
and the firmware writes it to the drive when the board's class reports `WIRELESS`, so the picker
offers only the build the board runs. A board with one build, such as Mighty FX or Plasma 2350,
lists its file under `files` alone, whether or not it has wireless.
