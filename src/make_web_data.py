"""
Generate web/opera.json for the interactive (D3) Haydn info card.

This reuses read.py (the same data pipeline that drives the printed card) so the
web card and the print card stay in sync. It reshapes the per-quartet records
into the "opus block" schema used by the Boccherini periodic-table web app
(https://github.com/jsundram/quartets.boccherini.org), adapted for Haydn:

  - catalog number  -> Hoboken III:N   (Boccherini used Gerard numbers)
  - opus nickname   -> dedicatee/byname (Sun, Russian, Erdody, ...)
  - Peters volume   -> roman numeral, surfaced in the tooltip

Run from the repo root:  uv run src/make_web_data.py -o web/opera.json
"""
import click
import json
import os

import read as Quartets


# quartetroulette's movements sheet carries a Spotify Track ID per movement.
DEFAULT_SPOTIFY = ("../quartet-chooser/.sheet_cache/"
    "1Q9MVjq5rOm-vZsfmm1ACg47Q4086W_8Obvn2UqjvrP4 - The Movements.json")

# (opus, work, mvmt) -> spotify url, populated in main() if the sheet is found.
SPOTIFY = {}

# movement_id -> {duration_ms, track_id}, from data/spotify_durations.json (exact
# linked-track lengths fetched by src/spotify_durations.py). This committed cache
# carries the Spotify track_id per movement, so it is the primary source for the
# clickable track links too (the movements sheet is only a fallback) — a clickable
# URL is just this fixed prefix + the track_id.
SPOTIFY_DUR = {}
SPOTIFY_TRACK_URL = "https://open.spotify.com/track/%s"


def track_url(quartet_id, mvmt):
    """Clickable Spotify URL for a movement from the committed durations cache,
    or None if the cache has no track_id for it."""
    entry = SPOTIFY_DUR.get("%sm%d" % (quartet_id, mvmt))
    track_id = entry.get("track_id") if isinstance(entry, dict) else None
    return SPOTIFY_TRACK_URL % track_id if track_id else None


def load_spotify(path):
    """Map (opus:int, work:str, mvmt:str) -> spotify url from the movements sheet.

    Work number is '' for the single-quartet opera (42, 103), matching how those
    quartets carry no '#'. Returns {} (no links) if the sheet isn't present.
    """
    if not path or not os.path.exists(path):
        return {}
    rows = json.load(open(path))
    header = rows[0]
    col = {k: i for i, k in enumerate(header)}
    get = lambda r, k: (r[col[k]] if col[k] < len(r) else "").strip()
    out = {}
    for r in rows[1:]:
        if get(r, "Composer") != "Haydn":
            continue
        opus = int(get(r, "Catalog Number").replace("Opus ", ""))
        out[(opus, get(r, "Work Number"), get(r, "Movement Number"))] = get(r, "Spotify Track ID")
    return out


# Layout: each row is a list of "blocks"; a block is a list of opus numbers.
# A block with >1 opus renders under a single merged label as one continuous set
# (e.g. 54+55 as a set of six, no spacer/label between them). A row with >1 block
# renders those blocks side by side with a spacer between (e.g. 77 and 103).
ROWS = [
    [[1]], [[2]], [[9]], [[17]], [[20]], [[33]], [[42]], [[50]],
    [[54, 55]], [[64]], [[71, 74]], [[76]], [[77], [103]],
]

# Byname for merged blocks (overrides the first opus's byname).
MERGED_BYNAME = {(54, 55): "Tost I/II", (71, 74): "Apponyi"}

# (year, nickname) per opus. Years match the printed card / timeline.
OPUS_META = {
      1: (1758, "Fürnberg"),
      2: (1758, "Fürnberg"),
      9: (1769, ""),
     17: (1771, ""),
     20: (1772, "Sun"),
     33: (1781, "Russian"),
     42: (1785, ""),
     50: (1787, "Prussian"),
     54: (1788, "Tost I"),
     55: (1788, "Tost II"),
     64: (1790, "Tost III"),
     71: (1793, "Apponyi"),
     74: (1793, "Apponyi"),
     76: (1797, "Erdődy"),
     77: (1799, "Lobkowitz"),
    103: (1803, "Fries"),
}


def parse_key(raw):
    """'Eb' -> ('E-flat', major=True); 'd' -> ('D', major=False); 'f#' -> ('F-sharp', False)."""
    major = raw[0].isupper()
    letter = raw[0].upper()
    accidental = ""
    if len(raw) > 1:
        if raw[1] in ("b", "-"):
            accidental = "-flat"
        elif raw[1] == "#":
            accidental = "-sharp"
    return letter + accidental, major


def title_case(s):
    """Capitalize the first letter of each word, preserving the rest (so the
    source's inconsistent casing — 'tortoise & hare', 'Compliment' — comes out
    uniform: 'Tortoise & Hare', 'Compliment')."""
    return " ".join(w[:1].upper() + w[1:] if w else w for w in s.split(" "))


def nickname(q):
    """First nickname, leading 'The ' stripped, '/'-alternates dropped, Title Cased."""
    nicks = q.get("nickname") or [""]
    n = (nicks[0] or "").strip()
    if "/" in n:
        n = n.split("/")[0].strip()
    for prefix in ("The ", "the "):
        if n.startswith(prefix):
            n = n[len(prefix):]
    return title_case(n)


def ordered_movements(q):
    """This quartet's movements, ordered by movement number."""
    return sorted(q.get("movements", []), key=lambda m: m.get("mvmt", 0))


def opus_color(opus):
    """Hex of the per-opus 'periodic table' color, from read.py's colormap."""
    name = Quartets.CMAP.get(opus, "white")
    c = Quartets.COLS.get(name, {}).get("value")
    if not c:
        return None
    return "#%02x%02x%02x" % (int(255 * c.red), int(255 * c.green), int(255 * c.blue))


def column(opus, number):
    """Grid column (1-6) for a quartet, so cards line up by number across rows.

    - column = number within the opus (x#1 -> col 1, x#6 -> col 6);
    - the second half of a merged pair (Op. 55, 74) is shifted +3 so 55#1 sits in
      col 4, continuing its partner's row;
    - Op. 1 #0 fills the slot vacated by the absent 1#5 (col 5);
    - single-quartet opera (no number) sit in col 1.
    Gaps left by absent quartets (e.g. 2#3, 2#5) become empty columns.
    """
    if opus == 1 and number == 0:
        return 5
    if number is None:
        return 1
    if opus in (55, 74):
        return number + 3
    return number


def movement_durations(movement, quartet_id):
    """Per-movement length in seconds for both recorded performances:
    {"angeles": <local recording>, "buchberger": <exact linked Spotify track>}.
    buchberger is None if the movement has no linked track."""
    buchberger = None
    mvmt_id = "%sm%d" % (quartet_id, movement["mvmt"])
    entry = SPOTIFY_DUR.get(mvmt_id)
    if entry:
        ms = entry["duration_ms"] if isinstance(entry, dict) else entry
        buchberger = round(ms / 1000, 1)
    return {"angeles": round(movement["duration"], 1), "buchberger": buchberger}


def make_quartet(q):
    key, major = parse_key(q["key"])
    hob = q.get("hoboken")
    number = q.get("#")
    mvmts = ordered_movements(q)
    work = "" if number is None else str(number)
    # Prefer the committed durations cache (carries the track_id); fall back to
    # the optional movements sheet for any movement the cache doesn't cover.
    tracks = [track_url(q["ID"], m["mvmt"]) or SPOTIFY.get((q["opus"], work, str(m["mvmt"])))
              for m in mvmts]
    quartet = {
        "id": q["ID"],
        "opus": q["opus"],
        "number": number,
        "column": column(q["opus"], number),
        "hoboken": ("III:%d" % hob) if hob else None,
        "key": key,
        "major": major,
        "nickname": nickname(q),
        "peters": q.get("peters"),
        "key_number": q.get("key_number"),
        "key_count": q.get("key_count"),
        "mvmts": [m["tempo"] for m in mvmts],
        "measures": [m["measures"] for m in mvmts],
        # Time signature per movement as [numerator, denominator] (e.g. [2, 4]);
        # the web card renders it "2/4". Used by the scatterplot's meter filter.
        "meters": [m["meter"] for m in mvmts],
        # Per-movement {angeles, buchberger} lengths in seconds. Buchberger (the
        # exact linked Spotify track) drives the bar widths; both show in the
        # tooltip. See src/spotify_durations.py for the Buchberger values.
        "durations": [movement_durations(m, q["ID"]) for m in mvmts],
        # Real movement numbers — Op. 103 only preserves movements 2 and 3.
        "mvmtNums": [m["mvmt"] for m in mvmts],
    }
    if any(tracks):
        quartet["tracks"] = tracks
    return quartet


@click.command()
@click.option("-o", "--outfile", type=click.Path(writable=True), required=True, help="output json (e.g. web/opera.json)")
@click.option("-c", "--color-json", default="./colors/sashamaps.json", help="json file specifying colors (read.py needs it)")
@click.option("-d", "--datadir", default="./data", help="data directory")
@click.option("-s", "--spotify", default=DEFAULT_SPOTIFY, help="quartetroulette movements sheet (for Spotify links)")
def main(outfile, color_json, datadir, spotify):
    global SPOTIFY, SPOTIFY_DUR
    SPOTIFY = load_spotify(spotify)
    print("spotify: %d movement links" % len(SPOTIFY) if SPOTIFY
          else "spotify: sheet not found (%s) — no links" % spotify)
    dur_path = os.path.join(datadir, "spotify_durations.json")
    if os.path.exists(dur_path):
        SPOTIFY_DUR = json.load(open(dur_path))
        print("spotify: %d exact track durations" % len(SPOTIFY_DUR))
    quartets = Quartets.get_data(data_dir=datadir, colorf=color_json, extend=False)
    by_opus = {}
    for q in quartets:
        by_opus.setdefault(q["opus"], []).append(q)

    by_number = lambda q: (q.get("#") is None, q.get("#") or 0)
    blocks = []
    for row_index, row in enumerate(ROWS):
        for opera in row:                       # opera: list of opus numbers in this block
            first = opera[0]
            year, nick = OPUS_META[first]
            if len(opera) > 1:
                nick = MERGED_BYNAME.get(tuple(opera), nick)
            qs = []
            for opus in opera:
                qs += sorted(by_opus.get(opus, []), key=by_number)
            blocks.append({
                "opus": "/".join(str(o) for o in opera),
                "year": year,
                "nickname": nick,
                "color": opus_color(first),
                "row": row_index,
                "quartets": [make_quartet(q) for q in qs],
            })

    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    with open(outfile, "w") as f:
        json.dump(blocks, f, indent=2, ensure_ascii=False)

    n_quartets = sum(len(b["quartets"]) for b in blocks)
    print("wrote %d opus blocks / %d quartets to %s" % (len(blocks), n_quartets, outfile))


if __name__ == "__main__":
    main()
