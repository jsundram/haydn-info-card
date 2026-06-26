"""Fetch exact Spotify track durations (and titles) for the linked movements.

Uses the client-credentials flow (public metadata, no user login). Set
SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET in the environment. The app's
credentials live in the Spotify developer dashboard (Client ID is in the URL,
Client Secret is behind "View client secret"):

    https://developer.spotify.com/dashboard/9c4d88ab97ac4bb7979f398627c764c3

Reads the linked track IDs out of web/opera.json (each track is linked to a
specific quartet movement), fetches duration_ms + title in batches of 50, and
writes data/spotify_durations.json keyed by track id:

    {"<track_id>": {"quartet_id": "001_0m1", "title": "...", "duration_ms": ...}}

`quartet_id` is the movement the track is *assigned* to in opera.json, using the
same key as the `ID` field in data/movements.json (OPUS_WORKmMVMT, e.g.
001_0m1) so the two files join directly. The Spotify `title` is stored alongside
so the assignment can be sanity-checked against what the track actually is: if a
track assigned to 001_0m1 is titled "...Op. 9 No. 2...", the mismatch is
visible without re-fetching. The fetch parses the opus out of each title and
prints a summary of any opus mismatches (the symptom behind scrambled bar
widths). make_web_data.py reads `duration_ms` to overlay these onto each
movement's `durations` value (it also still accepts the old flat
track_id -> duration_ms schema).

    SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=... uv run src/spotify_durations.py

This is a one-off: the output is cached/committed, so the regular build reads it
without any network access. The credentials are read from the environment and
never written to disk. Spotify hosts (accounts/api.spotify.com) are in the
project's sandbox network allowlist so the fetch needs no approval prompt.
"""
import base64
import json
import os
import re
import urllib.parse
import urllib.request

OPERA = "web/opera.json"
OUT = "data/spotify_durations.json"

# Pull the opus number out of a Spotify track title, e.g.
# "String Quartet in B-Flat Major, Op. 1 No. 1, Hob. III:1: I. Presto" -> 1.
OPUS_RE = re.compile(r"\bOp\.?\s*(\d+)", re.IGNORECASE)


def get_token(client_id, client_secret):
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token", data=body,
        headers={"Authorization": f"Basic {auth}",
                 "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["access_token"]


def track_id(url):
    if url and "/track/" in url:
        return url.rsplit("/track/", 1)[1].split("?")[0]
    return None


def collect_tracks(opera):
    """track_id -> quartet movement id (matches movements.json ID, e.g. '001_0m1').

    Each opera.json track is positionally aligned with the quartet's mvmtNums,
    so the movement a track is linked to is recoverable here. Returns an
    insertion-ordered dict (de-duped on track id, first assignment wins) and
    warns if a single track id is linked to more than one movement."""
    mapping = {}
    for block in opera:
        for q in block["quartets"]:
            tracks = q.get("tracks") or []
            mvmts = q.get("mvmtNums") or []
            for url, mvmt in zip(tracks, mvmts):
                tid = track_id(url)
                if not tid:
                    continue
                qid = "%sm%s" % (q["id"], mvmt)
                if tid in mapping and mapping[tid] != qid:
                    print("warning: track %s linked to both %s and %s"
                          % (tid, mapping[tid], qid))
                    continue
                mapping[tid] = qid
    return mapping


def fetch_tracks(token, ids):
    """track_id -> {"title": str, "duration_ms": int} for every id Spotify knows."""
    out = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        url = "https://api.spotify.com/v1/tracks?ids=" + ",".join(chunk)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            for t in json.load(r)["tracks"]:
                if t:
                    out[t["id"]] = {"title": t["name"], "duration_ms": t["duration_ms"]}
    return out


def title_opus(title):
    """Opus number named in a Spotify title, or None if not found."""
    m = OPUS_RE.search(title or "")
    return int(m.group(1)) if m else None


def report_mismatches(records):
    """Print quartet-id assignments whose Spotify title names a different opus.

    These are the likely mismaps behind durations that don't line up with
    data/movements.json. Title parsing is best-effort; titles with no parseable
    opus are reported separately rather than flagged as wrong."""
    mismatched, unparsed = [], []
    for tid, rec in sorted(records.items()):
        assigned_opus = int(rec["quartet_id"].split("_")[0])
        op = title_opus(rec["title"])
        if op is None:
            unparsed.append((rec["quartet_id"], rec["title"]))
        elif op != assigned_opus:
            mismatched.append((rec["quartet_id"], op, rec["title"]))
    if mismatched:
        print("\n%d track(s) whose title names a different opus than assigned:" % len(mismatched))
        for qid, op, title in mismatched:
            print("  assigned %-9s but title says Op. %-3s  %r" % (qid, op, title))
    else:
        print("\nno opus mismatches: every title's opus matches its assigned quartet id")
    if unparsed:
        print("%d title(s) had no parseable opus (check by hand):" % len(unparsed))
        for qid, title in unparsed:
            print("  %-9s %r" % (qid, title))


def main():
    cid = os.environ["SPOTIFY_CLIENT_ID"]
    secret = os.environ["SPOTIFY_CLIENT_SECRET"]
    opera = json.load(open(OPERA))
    mapping = collect_tracks(opera)          # track_id -> quartet_id
    ids = list(mapping)
    token = get_token(cid, secret)
    fetched = fetch_tracks(token, ids)       # track_id -> {title, duration_ms}

    records = {}
    for tid in ids:
        t = fetched.get(tid)
        if not t:
            continue
        records[tid] = {
            "quartet_id": mapping[tid],
            "title": t["title"],
            "duration_ms": t["duration_ms"],
        }
    with open(OUT, "w") as f:
        json.dump(records, f, indent=0, sort_keys=True)
    print("fetched %d/%d tracks -> %s" % (len(records), len(ids), OUT))
    report_mismatches(records)


if __name__ == "__main__":
    main()
