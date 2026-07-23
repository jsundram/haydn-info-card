#!/bin/bash
# Rasterize the site's icon SVGs -> the PNGs the <head> + manifest reference.
# The SVGs are the single source of truth; never hand-edit the PNGs.
#   favicon.svg        (rounded tile)   -> favicon-16, favicon-32          [browser tab only]
#   icon.svg           (square+opaque)  -> apple-touch-icon(180), icon-192, icon-512
#   icon-maskable.svg  (square, inset)  -> icon-maskable-512               [Android maskable]
# The home-screen / PWA icons come from the SQUARE icon.svg so the apple-touch-icon isn't
# double-masked (transparent rounded corners under iOS's own mask); iOS/Android round it.
# Prefers rsvg-convert (brew install librsvg); falls back to headless Chrome/Chromium.
set -euo pipefail
cd "$(dirname "$0")"

render() { # svg size out
  local svg="$1" size="$2" out="$3"
  if command -v rsvg-convert >/dev/null; then
    rsvg-convert -w "$size" -h "$size" "$svg" -o "$out"
    return
  fi
  for c in chromium chromium-browser google-chrome "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
    command -v "$c" >/dev/null 2>&1 || [ -x "$c" ] || continue
    "$c" --headless --no-sandbox --hide-scrollbars --force-device-scale-factor=1 \
         --window-size="$size,$size" --screenshot="$out" "file://$PWD/$svg" 2>/dev/null
    return
  done
  echo "ERROR: need rsvg-convert or Chrome/Chromium to rasterize $svg" >&2
  exit 1
}

render favicon.svg        16  favicon-16.png
render favicon.svg        32  favicon-32.png
render icon.svg           180 apple-touch-icon.png
render icon.svg           192 icon-192.png
render icon.svg           512 icon-512.png
render icon-maskable.svg  512 icon-maskable-512.png

echo "wrote favicon-16/32, apple-touch-icon, icon-192, icon-512, icon-maskable-512"
