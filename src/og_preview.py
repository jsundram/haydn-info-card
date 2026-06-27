"""Generate Open Graph / link-preview images for the web pages.

These committed PNGs are the og:image / twitter:image thumbnails shown when the
pages are shared (OS share sheet, Slack, iMessage, X, ...):

    web/index-preview.png     <- index.html   (the periodic-table card)
    web/scatter-preview.png   <- scatter.html  (the movement scatterplot)

Each is a fixed 1200x630 crop (the Open Graph standard 1.91:1), captured at 2x
for retina (so the file is 2400x1260). Uses the same single-process-Chromium +
inlined-OPERA_DATA trick as screenshot.py, so it runs inside the Claude Code
sandbox (single-process Chromium can't fetch file:// URLs).

    uv run src/og_preview.py        # regenerate both
Used by web/build.sh.
"""
import glob
import os
import shutil
import tempfile

import click
from PIL import Image
from playwright.sync_api import sync_playwright

W, H = 1200, 630   # Open Graph standard size (1.91:1)

# (source page, output png, a selector that signals the page has rendered)
PAGES = [
    ("index.html", "index-preview.png", ".quartet-card"),
    ("scatter.html", "scatter-preview.png", "circle.dot"),
]


def find_chromium():
    """Path to a Chromium/headless-shell binary, or None to use Playwright's default.

    Prefers the maintainer's Playwright cache; also handles a sandbox where the
    browsers live under $PLAYWRIGHT_BROWSERS_PATH (e.g. /opt/pw-browsers)."""
    patterns = ["~/.cache/ms-playwright/*/chrome-headless-shell-*/chrome-headless-shell"]
    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if browsers_path:
        patterns += [
            os.path.join(browsers_path, "chromium-*/chrome-linux/chrome"),
            os.path.join(browsers_path, "chromium_headless_shell-*/chrome-linux/headless_shell"),
        ]
    for pattern in patterns:
        hits = glob.glob(os.path.expanduser(pattern))
        if hits:
            return hits[0]
    return None


@click.command()
@click.option("--web-dir", default=os.path.join(os.path.dirname(__file__), "..", "web"),
              help="directory holding the html / opera.json / d3.v7.min.js")
@click.option("--scale", default=2, help="device scale factor (retina = 2)")
def main(web_dir, scale):
    web_dir = os.path.abspath(web_dir)
    tmp = tempfile.mkdtemp(prefix="haydnog.")
    try:
        with open(os.path.join(web_dir, "opera.json")) as f:
            data = f.read()
        shutil.copy(os.path.join(web_dir, "d3.v7.min.js"), tmp)

        launch = dict(args=["--single-process", "--no-zygote", "--no-sandbox",
                            "--disable-gpu", "--allow-file-access-from-files"])
        binary = find_chromium()
        if binary:
            launch["executable_path"] = binary

        with sync_playwright() as p:
            for src, outname, selector in PAGES:
                with open(os.path.join(web_dir, src)) as f:
                    html = f.read()
                page_path = os.path.join(tmp, src)
                with open(page_path, "w") as f:
                    f.write("<script>window.OPERA_DATA=%s;</script>\n%s" % (data, html))

                # A fresh browser per page: single-process Chromium tears down
                # when its first context closes, so it can't be reused.
                browser = p.chromium.launch(**launch)
                context = browser.new_context(
                    viewport={"width": W, "height": H}, device_scale_factor=scale)
                page = context.new_page()
                page.goto("file://%s" % page_path, wait_until="load")
                page.wait_for_selector(selector, timeout=10000)
                page.wait_for_timeout(400)   # let d3 finish painting
                out = os.path.join(web_dir, outname)
                page.screenshot(path=out, clip={"x": 0, "y": 0, "width": W, "height": H})
                browser.close()
                img = Image.open(out)
                print("wrote %s (%d bytes, %dx%d)" % (out, os.path.getsize(out), img.width, img.height))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
