"""Refresh exact Spotify track durations for the linked movements.

Uses the client-credentials flow (public metadata, no user login). Reads
SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET from the environment, or from a
.spotify-creds file in the repo root (KEY=VALUE lines). The app's credentials
live in the Spotify developer dashboard:

    https://developer.spotify.com/dashboard/9c4d88ab97ac4bb7979f398627c764c3

data/spotify_durations.json is the SOURCE OF TRUTH for the per-movement Spotify
links: it maps each movement ID ("{quartet_id}m{mvmt_num}") to its
{track_id, duration_ms}, e.g.:
    {"001_0m1": {"track_id": "02TAPWjDbcEwa1KBnqOw16", "duration_ms": 144186}, ...}

This script reads that file's track_ids, fetches the current duration_ms for
each (batches of 50), and writes the file back in place.

make_web_data.py then derives web/opera.json from this file — both the clickable
track links (a fixed prefix + track_id) and each movement's Buchberger duration.
The data flow is therefore acyclic: this cache -> opera.json, never back. To add
or change a linked recording, edit the track_id for that movement ID here, then
re-run this script to refresh its duration.

    uv run src/spotify_durations.py

This is a one-off: the output is cached/committed, so the regular build reads it
without any network access. Spotify hosts (accounts/api.spotify.com) are in the
project's sandbox network allowlist.
"""
import base64
import json
import os
import urllib.parse
import urllib.request

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


def fetch_durations(token, ids):
    """Return {track_id: duration_ms} for the given track ids."""
    out = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        url = "https://api.spotify.com/v1/tracks?ids=" + ",".join(chunk)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            for t in json.load(r)["tracks"]:
                if t:
                    out[t["id"]] = t["duration_ms"]
    return out


def main():
    cid, secret = load_creds()
    cache = json.load(open(OUT))   # {movement_id: {track_id, duration_ms}}
    ids = list(dict.fromkeys(       # de-dup, preserve order
        e["track_id"] for e in cache.values() if e.get("track_id")))
    token = get_token(cid, secret)
    durations = fetch_durations(token, ids)
    print("fetched %d track durations" % len(durations))

    out, stale = {}, []
    for mvmt_id, entry in cache.items():
        tid = entry.get("track_id")
        ms = durations.get(tid)
        if ms is None:              # keep the cached duration if the refetch missed
            stale.append(mvmt_id)
            ms = entry.get("duration_ms")
        out[mvmt_id] = {"track_id": tid, "duration_ms": ms}

    with open(OUT, "w") as f:
        json.dump(out, f, indent=0, sort_keys=True)
    print("wrote %d movement durations -> %s" % (len(out), OUT))
    if stale:
        print("kept cached duration for (no fresh value): %s" % ", ".join(stale))


if __name__ == "__main__":
    main()
