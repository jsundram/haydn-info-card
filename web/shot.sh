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
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$DIR/screenshot.png}"
[[ "$OUT" = /* ]] || OUT="$PWD/$OUT"

SHELL_BIN="$(/usr/bin/find "$HOME/.cache/ms-playwright" -name chrome-headless-shell -type f 2>/dev/null | head -1)"
if [[ -z "$SHELL_BIN" ]]; then
    echo "chrome-headless-shell not found under ~/.cache/ms-playwright" >&2
    exit 1
fi

TMP="$(mktemp -d "${TMPDIR:-/tmp}/haydnshot.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

# Build a self-contained page: define window.OPERA_DATA before index.html runs.
{
    printf '<script>window.OPERA_DATA='
    cat "$DIR/opera.json"
    printf ';</script>\n'
    cat "$DIR/index.html"
} > "$TMP/page.html"
cp "$DIR/d3.v7.min.js" "$TMP/"   # index.html loads d3 by relative path

"$SHELL_BIN" --headless --single-process --no-zygote --no-sandbox --disable-gpu \
    --user-data-dir="$TMP/profile" --hide-scrollbars --force-device-scale-factor=1 \
    --window-size="${WIDTH:-1500},${HEIGHT:-2150}" \
    --screenshot="$OUT" "file://$TMP/page.html" 2>/dev/null

echo "wrote $OUT ($(stat -f %z "$OUT") bytes)"
