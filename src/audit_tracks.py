"""Audit the linked Spotify tracks against our movement assignment, by title.

For each quartet, fetches every linked track's title from Spotify and checks that
the track sitting in movement slot N actually *is* movement N. It does this by
finding, per quartet, the assignment of tracks->our-movements that best matches
the tempo words (brute force over permutations; identity wins ties). When the
best assignment differs from the current one, the quartet is flagged with the
suggested corrected mapping.

Writes:
  data/spotify_track_titles.json  id -> Spotify title (raw reference)
  data/track_audit.json           per-movement audit + suggested fixes

so the source (quartetroulette movements sheet) can be corrected.

    SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=... uv run src/audit_tracks.py
"""
import base64
import itertools
import json
import os
import re
import urllib.parse
import urllib.request

OPERA = "web/opera.json"
TITLES = "data/spotify_track_titles.json"
AUDIT = "data/track_audit.json"


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


def fetch_names(token, ids):
    out = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        req = urllib.request.Request(
            "https://api.spotify.com/v1/tracks?ids=" + ",".join(chunk),
            headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            for t in json.load(r)["tracks"]:
                if t:
                    out[t["id"]] = t["name"]
    return out


def tokens(text):
    """Movement-descriptor tokens: the part after the last ':' in a Spotify
    title (or a raw tempo), minus Roman numerals and punctuation."""
    text = text.split(":")[-1].lower()
    text = re.sub(r"\b[ivx]+\b", " ", text)        # drop roman numerals
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return {w for w in text.split() if len(w) > 1}


def best_assignment(our_tempos, titles):
    """Permutation perm such that our movement i is best served by titles[perm[i]].
    Maximizes shared tempo tokens; prefers identity on ties."""
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
    token = get_token(os.environ["SPOTIFY_CLIENT_ID"], os.environ["SPOTIFY_CLIENT_SECRET"])
    opera = json.load(open(OPERA))

    ids = []
    for block in opera:
        for q in block["quartets"]:
            for url in (q.get("tracks") or []):
                tid = track_id(url)
                if tid:
                    ids.append(tid)
    ids = list(dict.fromkeys(ids))
    names = fetch_names(token, ids)
    with open(TITLES, "w") as f:
        json.dump(names, f, indent=0, sort_keys=True, ensure_ascii=False)

    audit = []
    flagged = []
    for block in opera:
        for q in block["quartets"]:
            tids = [track_id(u) for u in (q.get("tracks") or [])]
            if not tids or not all(tids):
                continue
            titles = [names.get(t, "") for t in tids]
            perm, ok = best_assignment(q["mvmts"], titles)
            for i, (mv, tempo) in enumerate(zip(q["mvmtNums"], q["mvmts"])):
                audit.append({
                    "id": q["id"], "opus": q["opus"], "number": q["number"],
                    "movement": mv, "our_tempo": tempo,
                    "current_track": tids[i], "current_title": titles[i],
                    "ok": perm[i] == i,
                    "should_be_track": tids[perm[i]],
                    "should_be_title": titles[perm[i]],
                })
            if not ok:
                flagged.append((q, tids, titles, perm))

    with open(AUDIT, "w") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)

    print("checked %d movements across %d quartets" % (len(audit), sum(len(b["quartets"]) for b in opera)))
    print("flagged %d quartet(s) with a likely track-order error:\n" % len(flagged))
    for q, tids, titles, perm in flagged:
        nm = "Op.%s%s" % (q["opus"], (" #%d" % q["number"]) if q["number"] is not None else "")
        print("=== %s (%s) ===" % (nm, q["id"]))
        for i, (mv, tempo) in enumerate(zip(q["mvmtNums"], q["mvmts"])):
            mark = " " if perm[i] == i else "X"
            short = titles[perm[i]].split(":")[-1].strip()[:42]
            print("  [%s] mvt %s (%s): should link track %s — %s"
                  % (mark, mv, tempo[:24], tids[perm[i]], short))


if __name__ == "__main__":
    main()
