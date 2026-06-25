# Haydn Info Card — interactive web version

An interactive periodic-table-of-quartets web card for Haydn's 68 string
quartets, modeled on the
[Periodic Table of Boccherini String Quartets](https://github.com/jsundram/quartets.boccherini.org).

Each opus is a row (year, Haydn's age, opus number, byname); each quartet is a
card showing its key (major/minor, with the key-signature accidentals on the
left edge), Hoboken III number + number-within-opus, nickname, and a bar per
movement (minuet/scherzo movements lightened). Minor keys get a pink mode bar.
Hover (or tap, on touch devices) a card for full detail: opus/number/key,
Hoboken number, nickname, Peters volume, position within the key, and the
movement tempos. Light/dark mode follows the system preference, and the layout
has a print stylesheet (Cmd/Ctrl+P → enable "Background graphics").

## Files

- `index.html` — the whole app (CSS + D3 in one file). Loads `opera.json`.
- `opera.json` — generated data (do not hand-edit; see below).
- `d3.v7.min.js` — D3 v7, served locally.

## Regenerating the data

`opera.json` is generated from the same source data as the printed card
(`data/quartets.json`, `data/movements.json`, `data/haydn_peters.json`) via
`read.py`, so the two stay in sync. From the repo root:

```sh
uv run src/make_web_data.py -o web/opera.json
```

Opus years/bynames and the row groupings live in `src/make_web_data.py`.

Spotify track links come from quartetroulette's movements sheet (a sibling repo:
`../quartet-chooser/.sheet_cache/… - The Movements.json`, the default for
`--spotify`). If that file isn't present the build still succeeds, just without
`tracks` (and the bars aren't clickable). All 280 movements are covered when it
is present.

## Build

`./build.sh` regenerates `opera.json` and renders the screenshots:

- `web/screenshot-iphone.png` — full-page, retina (3×), real iPhone mobile layout
- `web/screenshot-desktop.png` — full-page desktop

Both are git-ignored build artifacts. Screenshots use `src/screenshot.py`
(Playwright driving the bundled `chrome-headless-shell` in single-process mode,
with `opera.json` inlined into a temp page) — that combination runs without a
server and, under Claude Code, inside the sandbox with no approval prompts. The
iPhone capture emulates touch so the page's mobile `@media` rules apply.

Run a single screenshot directly, e.g.:

```sh
uv run src/screenshot.py -o /tmp/iphone.png                 # iPhone (default)
uv run src/screenshot.py -o /tmp/desk.png --width 1500 --scale 2 --no-mobile
```

`./shot.sh [out.png]` is a lighter zero-Python alternative for a quick desktop
shot (fixed window size, not full-page).

## Viewing locally

`index.html` fetches `opera.json`, so it needs to be served over HTTP (opening
the file directly is blocked by the browser's same-origin policy). From this
directory:

```sh
python3 -m http.server 8000
# then open http://localhost:8000/
```

## Status

Core grid, plus: the per-opus "periodic table" color splash behind each opus
number (same colormap as the printed card); the key position ("2/4", bottom
left) and Peters volume (I–IV, bottom right) on each card face; and movement
bars whose widths are proportional to each movement's measure count, on a single
global scale so a quartet's total bar length is comparable across cards, left
aligned to a common origin. Each movement bar is a playable Spotify link (click
the bar, or the movement in the hover tooltip, which also lists per-movement and
total measures).

Not yet carried over from the printed card / Boccherini app:

- **Peters volume** (I–IV) is in the hover tooltip but not on the card face.
- The **footnote** explaining the "67.5 quartets" count is absent.
- External links the Boccherini card carries (IMSLP scores, Spotify recordings,
  per-quartet QR codes) — the Haydn source data doesn't include those URLs yet.
