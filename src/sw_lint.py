#!/usr/bin/env python3
"""Commit-time checks for web/sw.js's precache contract.

web/sw.js precaches the app SHELL. Five mistakes are cheap to catch here and expensive at runtime:

1. A staged SHELL file with an unchanged V. An edit to a precached file only reaches installed
   clients when V changes — forget the bump and the fix ships to the repo but never to anyone's
   home-screen copy. The single most common PWA deploy bug.
2. A SHELL entry that doesn't exist on disk. It can never be fetched, so it permanently wedges
   the old-generation collect: both cache generations pile up on every device, with the stale one
   still answering via the whole-store fallback. (pwa-starter#7)
3. A cross-origin SHELL entry. The fetch handler passes other origins straight through, so the
   entry would be cached but never served — vendor the file locally instead.
4. A V without a numeric tail. The tail orders generations for sw.js's collect and app.js's
   checkVer() ranking; a non-numeric V makes collection silently stop, no error, no symptom,
   until caches pile up. Rename the stem freely — keep the digits.
5. app.js's VER_PREFIX not matching V's stem. checkVer() ranks installed caches by that prefix,
   so a renamed stem on one side silently breaks the update pill. The stems must agree.

Paths in sw.js's SHELL are relative to web/ (e.g. "./index.html" -> web/index.html); this prefixes
them so they match git's repo-relative staged names. Adapted from pwa-starter/scripts/sw-lint.py
@ b1e34e1.

The pre-commit hook runs it warn-only; run it in CI with a real exit code. By hand:
    uv run src/sw_lint.py     (or: python3 src/sw_lint.py)
"""
import os
import re
import subprocess
import sys

SW = "web/sw.js"
APP = "web/app.js"


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def ver(src):
    # Anchored to the DECLARATION — the same expression app.js's checkVer() uses (keep them in
    # agreement). sw.js's comments cite version names as examples, so a first-match-anywhere
    # scan would read a comment.
    m = re.search(r'const V\s*=\s*"([^"]*)"', src)
    return m.group(1) if m else None


def shell_entries(src):
    m = re.search(r"const SHELL\s*=\s*\[(.*?)\]", src, re.S)
    if not m:
        return []
    # Alternation, not a strip pass: deleting //-comments first would also eat the "//" inside a
    # cross-origin URL plus every entry after it on that line — failing open on exactly what the
    # cross-origin check exists to catch. Scanning left to right, a comment consumes any strings
    # it contains, so a commented-out entry ('// "./old-page.html",') is correctly ignored.
    return [s for s in re.findall(r'//[^\n]*|"([^"]+)"', m.group(1)) if s]


def main():
    idx = sh("git", "show", f":{SW}")            # staged web/sw.js
    if idx.returncode != 0:
        return 0                                  # no sw.js in the index / not a repo
    src = idx.stdout
    v = ver(src)
    entries = shell_entries(src)
    problems = []

    if v is not None and not re.search(r"\d+$", v):
        problems.append(f'V is "{v}", which has no numeric tail. The tail orders cache '
                        "generations (sw.js's collect, app.js's ranking) — rename the stem "
                        "freely, but keep the digits.")

    app = sh("git", "show", f":{APP}")
    if v is not None and app.returncode == 0:
        m = re.search(r'const VER_PREFIX\s*=\s*"([^"]*)"', app.stdout)
        stem = re.sub(r"\d+$", "", v)
        if m and m.group(1) != stem:
            problems.append(f'{APP}\'s VER_PREFIX is "{m.group(1)}" but sw.js\'s V stem is '
                            f'"{stem}" — checkVer() ranks caches by that prefix, so the update '
                            "pill silently stops tracking this app. Keep the two in agreement.")

    top = sh("git", "rev-parse", "--show-toplevel").stdout.strip()
    for entry in entries:
        if "://" in entry:
            problems.append(f'SHELL entry "{entry}" is cross-origin — the fetch handler passes '
                            "other origins straight through, so it caches but never serves. "
                            "Vendor the file locally.")
            continue
        p = entry.lstrip("./")
        if not p:
            continue                              # "./" — the scope root, served as index.html
        if p.endswith("/"):
            p += "index.html"                     # a directory entry serves its index.html
        p = "web/" + p
        if top and not os.path.exists(os.path.join(top, p)):
            problems.append(f'SHELL entry "{entry}" doesn\'t exist ({p}) — an unfetchable entry '
                            "wedges the old-generation collect on every device. Fix the path or "
                            "generate the file.")

    shell = {"web/" + e.lstrip("./") for e in entries if "://" not in e and e.strip("./")}
    staged = set(sh("git", "diff", "--cached", "--name-only").stdout.split())
    touched = sorted((staged & shell) - {SW})
    if touched:
        head = sh("git", "show", f"HEAD:{SW}")
        old = ver(head.stdout) if head.returncode == 0 else None
        if old is not None and v == old:          # not the first commit, and V unchanged
            problems.append(f'V is still "{v}" but this commit changes precached shell files '
                            f'({", ".join(touched)}) — bump V in {SW} or installed clients '
                            "keep the cached version.")

    if not problems:
        return 0
    print(f"  {SW}:")
    for p in problems:
        print(f"   - {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
