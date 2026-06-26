# Haydn Info Card — interactive web version

**Live: <https://jsundram.github.io/haydn-info-card/>**

An interactive periodic-table-of-quartets web card for Haydn's 68 string
quartets, modeled on the
[Periodic Table of Boccherini String Quartets](https://github.com/jsundram/quartets.boccherini.org).

## What it shows

Each opus is a row labeled with its year, Haydn's age, opus number (stacked
"Opus N"), and byname (Fürnberg, Sun, Russian, …), on a per-opus color splash.
Each quartet is a card:

- **Key** big-centered (major/minor), with the key-signature accidentals (♯/♭)
  down the left edge.
- **Mode bar** (top): Hoboken III number (left) + number-within-opus (right);
  **minor keys** get a neutral **gray** bar (light in dark mode).
- **Nickname** (Title-cased) below the mode bar.
- **Bottom corners**: position within key ("2/4", left) and Peters volume
  (I–IV, right).
- **Movement bars** (bottom strip): one bar per movement, **width proportional
  to its duration** (the exact length of the linked Spotify track) on a single
  global scale (so total length is comparable across quartets), tinted with the
  **opus color**; minuet/scherzo bars are lighter + outlined. **Click a bar to
  play the movement on Spotify.**

Hover (or tap) a card for a tooltip: opus/number/key, Hoboken number, nickname,
Peters volume, position within key, and the movement list with per-movement and
total measures (each a Spotify link). Light/dark mode follows the system
preference; there are also print and mobile (phone) layouts.

## Status

Live and feature-complete relative to the printed card. Everything from the
print card is represented (per-opus colors, Peters volume, key position, the
revised-count footnote, the 67.5★→68 framing), plus web-only additions: Hoboken
numbers, edge accidentals, measure-scaled **playable** movement bars, dark mode.

Not carried over (the Haydn source data lacks the URLs): IMSLP score links and
per-quartet QR codes that the Boccherini card has.

## Files

- `index.html` — the whole app (CSS + D3 inline). Fetches `opera.json`, unless a
  build step has inlined it as `window.OPERA_DATA` (see Screenshots).
- `opera.json` — generated data (do **not** hand-edit; regenerate — see below).
  It is committed and is what GitHub Pages serves.
- `d3.v7.min.js` — D3 v7, served locally.
- `build.sh` — regenerate data + render screenshots.
- `shot.sh` — quick desktop screenshot (no Python).

(The generators live at the repo root: `src/make_web_data.py`, `src/screenshot.py`.)

## Deployment

GitHub Pages, via [`.github/workflows/pages.yml`](../.github/workflows/pages.yml),
publishes the `web/` folder on **any push to `main`** (Pages source = "GitHub
Actions"). The site is static with relative asset paths, so it works under the
`/haydn-info-card/` project subpath. CI publishes the **committed** files only —
it does not regenerate data — so **commit a fresh `opera.json`** when the data
changes. A custom domain would be a `web/CNAME` file + a DNS record.

## Regenerating the data

`opera.json` is generated from the same source as the printed card
(`data/quartets.json`, `data/movements.json`, `data/haydn_peters.json`) via
`read.py`, so the two stay in sync. From the repo root:

```sh
uv run src/make_web_data.py -o web/opera.json
```

Layout (`ROWS`), opus years/bynames (`OPUS_META`), merged-pair bynames, grid
columns (`column()`), nickname Title-casing, and the Spotify join all live in
`src/make_web_data.py`. Spotify track links come from quartetroulette's movements
sheet (sibling repo: `../quartet-chooser/.sheet_cache/… - The Movements.json`,
the `--spotify` default). If absent, the build still succeeds without `tracks`
(bars not clickable); all 280 movements are covered when present.

**Movement durations** (which drive the bar widths) are the exact lengths of the
linked Spotify tracks, cached in `data/spotify_durations.json` (committed).
Regenerate that cache only when the track links change:

```sh
SPOTIFY_CLIENT_ID=… SPOTIFY_CLIENT_SECRET=… uv run src/spotify_durations.py
```

Credentials live in the [Spotify dashboard](https://developer.spotify.com/dashboard/9c4d88ab97ac4bb7979f398627c764c3)
(client-credentials flow, no user login). They're read from the env and never
written to disk; `accounts/api.spotify.com` are in the project sandbox network
allowlist. If the cache is missing, durations fall back to the Angeles Quartet
recordings in `movements.json`.

## Build / screenshots

`./build.sh` regenerates `opera.json` and renders (git-ignored) screenshots:
`web/screenshot-iphone.png` (full-page, retina 3×, real phone layout) and
`web/screenshot-desktop.png`. Or a single one:

```sh
uv run src/screenshot.py -o /tmp/iphone.png                 # iPhone (default)
uv run src/screenshot.py -o /tmp/desk.png --width 1500 --scale 2 --no-mobile
```

`./shot.sh [out.png]` is a lighter zero-Python desktop shot (fixed size, not
full-page).

## Viewing locally

`index.html` fetches `opera.json`, so serve over HTTP (opening the file directly
is blocked by same-origin policy):

```sh
python3 -m http.server 8000   # from web/, then open http://localhost:8000/
```

## Development notes

**Data flow:** `read.py` (shared with the print card) → `src/make_web_data.py` →
`web/opera.json` → `index.html` renders it with D3.

**`opera.json` schema** — an array of opus *blocks* in render order:

```
{ opus: "76"|"54/55", year, nickname (byname), color (#hex), row (int),
  quartets: [ {
    id, opus (int), number (#|null), hoboken ("III:N"|null),
    key ("B-flat"|"D"), major (bool), nickname, peters (1–4|null),
    key_number, key_count, column (1–6),
    mvmts:[tempo], measures:[int], durations:[sec], mvmtNums:[int], tracks:[url|null]
  } ] }
```

**Rendering (index.html):**
- *Rows* group blocks by `row`. Merged pairs (54/55, 71/74) are a single block;
  77 and 103 are two blocks in one row, with the 103 block pushed to column 6 via
  `margin-left:auto` (the last quartet at the last column).
- *Columns*: each quartet has a `column` (1–6); rendering walks 1→max and emits a
  `.quartet-blank` for empty columns, so absent quartets (2#3, 2#5) show as gaps
  and Op. 1 #0 fills the slot vacated by the absent 1#5 (column 5).
- *Opus color* is set inline as `--opus-color` on the label and each card; it
  drives the label splash gradient and the movement-bar badge.
- *Movement bars* use one global `pxPerSec` (computed once) so the longest
  quartet fills the badge and the rest are proportional; Op. 103 is centered
  because its surviving movements are 2 & 3. `durations` = exact Spotify
  linked-track length (else the Angeles recording); see below.
- The "Opus" prefix is `rem`-sized (independent of the number) so it aligns on
  every label; 3+ char numbers ("103", "54/55") get the `.compact` class.

**Gotchas (these caused real bugs):**
- The mobile layout uses `transform: scale(0.35)` (a real-phone hack). Two
  consequences for headless capture:
  1. `getBoundingClientRect()` returns *scaled* sizes, so the movement-bar scale
     probe must use **`offsetWidth`** (layout px) or every bar renders ~⅓ short.
  2. Playwright `full_page` widens the viewport past the 800px mobile breakpoint,
     disabling the transform mid-capture. `screenshot.py` therefore **never** uses
     `full_page`: it fixes the device width, grows only the height, and captures a
     `clip` box measured from the painted content.
- Chromium can't run multi-process inside the Claude Code sandbox (Mach ports),
  and single-process Chromium can't `fetch()` a `file://` URL — so the screenshot
  tools inline `opera.json` as `window.OPERA_DATA` into a temp page. That inline
  path exists **only** for screenshots; the served site fetches `opera.json`
  normally.

**Possible next features:** IMSLP/score links, non-Spotify recording links,
per-quartet QR codes (all need source URLs Haydn data doesn't yet have); a custom
domain; optional per-opus rainbow card backgrounds (currently only the label
splash + badge are colored).
