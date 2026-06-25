#!/bin/bash
# Build the interactive web card: regenerate its data and render screenshots
# (a retina iPhone full-page capture, plus a desktop one).
#
# Usage:  web/build.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$DIR")"
cd "$ROOT"

echo "==> data: web/opera.json"
uv run src/make_web_data.py -o web/opera.json

echo "==> screenshot: iPhone (retina, full page)"
uv run src/screenshot.py -o web/screenshot-iphone.png

echo "==> screenshot: desktop (full page)"
uv run src/screenshot.py -o web/screenshot-desktop.png --width 1500 --height 1000 --scale 2 --no-mobile

echo "done."
