"""Fetch exact Spotify track durations for the linked movements.

Uses the client-credentials flow (public metadata, no user login). Reads
SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET from the environment, or from a
.spotify-creds file in the repo root (KEY=VALUE lines). The app's credentials
live in the Spotify developer dashboard:

    https://developer.spotify.com/dashboard/9c4d88ab97ac4bb7979f398627c764c3

Reads the linked track IDs out of web/opera.json, fetches track names and
duration_ms in batches of 50. Uses best-tempo-token matching (permutation
search) to correctly assign each Spotify track to its quartet movement —
catching cases where the linked tracks are in the wrong order in the source
data.

Writes data/spotify_durations.json as {movement_id: {track_id, duration_ms}}, e.g.:
    {"001_0m1": {"track_id": "02TAPWjDbcEwa1KBnqOw16", "duration_ms": 144186}, ...}

Storing the track ID alongside the duration makes it possible to verify which
specific Buchberger recording each duration comes from.

make_web_data.py overlays these onto each movement's `durations` value by
looking up the movement ID ("{quartet_id}m{mvmt_num}") directly.

    uv run src/spotify_durations.py

This is a one-off: the output is cached/committed, so the regular build reads
it without any network access. Spotify hosts (accounts/api.spotify.com) are in
the project's sandbox network allowlist.
"""
import base64
import itertools
import json
import os
import re
import urllib.parse
import urllib.request

OPERA = "web/opera.json"
OUT = "data/spotify_durations.json"
CREDS_FILE = ".spotify-creds"


def load_creds():
    """Read SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET from env or .spotify-creds."""
    cid = os.environ.get("SPOTIFY_CLIENT_ID")
    secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not (cid and secret) and os.path.exists(CREDS_FILE):
        for line in open(CREDS_FILE):
            k, _, v = line.strip().partition("=")
            if k == "SPOTIFY_CLIENT_ID":
                cid = v
            elif k == "SPOTIFY_CLIENT_SECRET":
                secret = v
    if not cid or not secret:
        raise RuntimeError(
            "Set SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET in the environment "
            "or in .spotify-creds"
        )
    return cid, secret


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


def collect_ids(opera):
    ids = []
    for block in opera:
        for q in block["quartets"]:
            for url in (q.get("tracks") or []):
                tid = track_id(url)
                if tid:
                    ids.append(tid)
    return list(dict.fromkeys(ids))  # de-dup, preserve order


def fetch_tracks(token, ids):
    """Return {track_id: {"name": str, "duration_ms": int}}."""
    out = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        url = "https://api.spotify.com/v1/tracks?ids=" + ",".join(chunk)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            for t in json.load(r)["tracks"]:
                if t:
                    out[t["id"]] = {"name": t["name"], "duration_ms": t["duration_ms"]}
    return out


def tokens(text):
    """Movement-descriptor tokens: part after last ':', minus Roman numerals and punctuation."""
    text = text.split(":")[-1].lower()
    text = re.sub(r"\b[ivx]+\b", " ", text)
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return {w for w in text.split() if len(w) > 1}


def best_assignment(our_tempos, titles):
    """Permutation mapping our movement i to Spotify track titles[perm[i]].

    Maximizes shared tempo tokens; identity wins ties. Returns (perm, is_identity).
    """
    n = len(our_tempos)
    ot = [tokens(t) for t in our_tempos]
    st = [tokens(t) for t in titles]
    identity = tuple(range(n))

    def score(perm):
        return sum(len(ot[i] & st[perm[i]]) for i in range(n))

    id_score = score(identity)
    best, best_score = identity, id_score
    for perm in itertools.permutations(range(n)):
        s = score(perm)
        if s > best_score:
            best, best_score = perm, s
    return best, (best_score == id_score)


def main():
    cid, secret = load_creds()
    opera = json.load(open(OPERA))
    ids = collect_ids(opera)
    token = get_token(cid, secret)
    tracks = fetch_tracks(token, ids)
    print("fetched %d track names+durations" % len(tracks))

    out = {}
    reordered = []
    for block in opera:
        for q in block["quartets"]:
            tids = [track_id(u) for u in (q.get("tracks") or [])]
            if not tids or not all(tids):
                continue
            titles = [tracks.get(t, {}).get("name", "") for t in tids]
            perm, ok = best_assignment(q["mvmts"], titles)
            if not ok:
                reordered.append(q["id"])
            for i, mvnum in enumerate(q["mvmtNums"]):
                mvmt_id = "%sm%d" % (q["id"], mvnum)
                assigned_tid = tids[perm[i]]
                ms = tracks.get(assigned_tid, {}).get("duration_ms")
                if ms:
                    out[mvmt_id] = {"track_id": assigned_tid, "duration_ms": ms}

    with open(OUT, "w") as f:
        json.dump(out, f, indent=0, sort_keys=True)
    print("wrote %d movement durations -> %s" % (len(out), OUT))
    if reordered:
        print("reordered tracks for: %s" % ", ".join(reordered))


if __name__ == "__main__":
    main()
