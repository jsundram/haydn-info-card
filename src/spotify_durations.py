"""Fetch exact Spotify track durations for the linked movements.

Uses the client-credentials flow (public metadata, no user login). Set
SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET in the environment. The app's
credentials live in the Spotify developer dashboard (Client ID is in the URL,
Client Secret is behind "View client secret"):

    https://developer.spotify.com/dashboard/9c4d88ab97ac4bb7979f398627c764c3

Reads the linked track IDs out of web/opera.json, fetches duration_ms in batches
of 50, and writes data/spotify_durations.json (track_id -> duration_ms).
make_web_data.py overlays these onto each movement's `durations` value.

    SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=... uv run src/spotify_durations.py

This is a one-off: the output is cached/committed, so the regular build reads it
without any network access. The credentials are read from the environment and
never written to disk. Spotify hosts (accounts/api.spotify.com) are in the
project's sandbox network allowlist so the fetch needs no approval prompt.
"""
import base64
import json
import os
import urllib.parse
import urllib.request

OPERA = "web/opera.json"
OUT = "data/spotify_durations.json"


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
    return list(dict.fromkeys(ids))  # de-dup, keep order


def fetch_durations(token, ids):
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
    cid = os.environ["SPOTIFY_CLIENT_ID"]
    secret = os.environ["SPOTIFY_CLIENT_SECRET"]
    opera = json.load(open(OPERA))
    ids = collect_ids(opera)
    token = get_token(cid, secret)
    durations = fetch_durations(token, ids)
    with open(OUT, "w") as f:
        json.dump(durations, f, indent=0, sort_keys=True)
    print("fetched %d/%d track durations -> %s" % (len(durations), len(ids), OUT))


if __name__ == "__main__":
    main()
