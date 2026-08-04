#!/bin/bash
# Screenshot the Haydn web card to a PNG, runnable inside the Claude Code sandbox
# (so it needs no approval prompts).
#
# Why this is fiddly: Chromium can't run multi-process in the sandbox (blocked
# Mach ports) and single-process Chromium won't fetch a file:// URL. So we inline
# opera.json into a temporary self-contained page and render that single-process.
#
# Usage:  ./shot.sh [output.png]      (default: web/screenshot.png)
#         WIDTH=1200 HEIGHT=1700 ./shot.sh out.png
#         MOBILE=1 ./shot.sh out.png    phone layout (defaults to 390x844)
#         DARK=1 ./shot.sh out.png      dark mode (the .dark-mode testing class)
#         DSF=3 ./shot.sh out.png       device scale factor (crisp close-ups)
#
# MOBILE=1 rewrites the touch-device media query "(hover: none) and
# (pointer: coarse) and (max-width: 800px)" to plain "(max-width: 800px)" in
# the temporary page (CSS and the matching JS MOBILE_MQ), because the headless
# shell always reports a hovering fine pointer and would otherwise never take
# the mobile code path. Close emulation, not the shipped query: it can't catch
# bugs in the hover/pointer terms themselves.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$DIR/screenshot.png}"
[[ "$OUT" = /* ]] || OUT="$PWD/$OUT"

if [[ "${MOBILE:-}" = 1 ]]; then
    WIDTH="${WIDTH:-390}"
    HEIGHT="${HEIGHT:-844}"
fi

SHELL_BIN="$(/usr/bin/find "$HOME/.cache/ms-playwright" -name chrome-headless-shell -type f 2>/dev/null | head -1)"
if [[ -z "$SHELL_BIN" ]]; then
    echo "chrome-headless-shell not found under ~/.cache/ms-playwright" >&2
    exit 1
fi

TMP="$(mktemp -d "${TMPDIR:-/tmp}/haydnshot.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

# Build a self-contained page: define window.OPERA_DATA before index.html runs.
{
    [[ "${DARK:-}" = 1 ]] && printf '<script>document.documentElement.classList.add("dark-mode")</script>\n'
    printf '<script>window.OPERA_DATA='
    cat "$DIR/opera.json"
    printf ';</script>\n'
    if [[ "${MOBILE:-}" = 1 ]]; then
        sed 's/(hover: none) and (pointer: coarse) and (max-width: 800px)/(max-width: 800px)/g' "$DIR/index.html"
    else
        cat "$DIR/index.html"
    fi
} > "$TMP/page.html"
cp "$DIR/d3.v7.min.js" "$TMP/"   # index.html loads d3 by relative path

"$SHELL_BIN" --headless --single-process --no-zygote --no-sandbox --disable-gpu \
    --user-data-dir="$TMP/profile" --hide-scrollbars --force-device-scale-factor="${DSF:-1}" \
    --window-size="${WIDTH:-1500},${HEIGHT:-2150}" \
    --screenshot="$OUT" "file://$TMP/page.html" 2>/dev/null

echo "wrote $OUT ($(stat -f %z "$OUT") bytes)"
