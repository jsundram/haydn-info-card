#!/bin/bash
# Rasterize the site's icon SVGs -> the PNGs the <head> + manifest reference.
# The SVGs are the single source of truth; never hand-edit the PNGs.
#   favicon.svg        -> favicon-16/32, apple-touch-icon (180), icon-192, icon-512
#   icon-maskable.svg  -> icon-maskable-512 (full-bleed, for Android's maskable slot)
# Needs rsvg-convert (brew install librsvg). Run from web/.
set -euo pipefail
cd "$(dirname "$0")"

rsvg-convert -w 16  -h 16  favicon.svg -o favicon-16.png
rsvg-convert -w 32  -h 32  favicon.svg -o favicon-32.png
rsvg-convert -w 180 -h 180 favicon.svg -o apple-touch-icon.png
rsvg-convert -w 192 -h 192 favicon.svg -o icon-192.png
rsvg-convert -w 512 -h 512 favicon.svg -o icon-512.png
rsvg-convert -w 512 -h 512 icon-maskable.svg -o icon-maskable-512.png

echo "wrote favicon-16/32, apple-touch-icon, icon-192, icon-512, icon-maskable-512"
