"""Full-page PNG screenshot of the web card, defaulting to a retina iPhone.

Uses Playwright driving the cached chrome-headless-shell in single-process mode,
which is the combination that runs inside the Claude Code sandbox (CDP over a
pipe — no socket bind, no multi-process Mach ports — so no approval prompts).
Single-process Chromium can't fetch file:// URLs, so opera.json is inlined into a
temporary self-contained page (same trick as web/shot.sh).

Touch/pointer emulation (is_mobile + has_touch) is what makes the page's mobile
@media rules apply, so the iPhone capture shows the real phone layout.

Used by web/build.sh.  Example:
    uv run src/screenshot.py -o web/screenshot-iphone.png
    uv run src/screenshot.py -o web/screenshot-desktop.png --width 1500 --no-mobile --scale 2
"""
import glob
import os
import shutil
import tempfile

import click
from PIL import Image
from playwright.sync_api import sync_playwright


def find_chromium():
    """The Playwright-cached headless shell binary, if present (else None -> default)."""
    hits = glob.glob(os.path.expanduser(
        "~/.cache/ms-playwright/*/chrome-headless-shell-*/chrome-headless-shell"))
    return hits[0] if hits else None


@click.command()
@click.option("-o", "--out", required=True, type=click.Path(), help="output png")
@click.option("--web-dir", default=os.path.join(os.path.dirname(__file__), "..", "web"),
              help="directory holding index.html / opera.json / d3.v7.min.js")
@click.option("--width", default=393, help="viewport CSS width (iPhone 14/15 = 393)")
@click.option("--height", default=852, help="viewport CSS height")
@click.option("--scale", default=3, help="device scale factor (retina = 2 or 3)")
@click.option("--mobile/--no-mobile", default=True, help="emulate touch (applies mobile @media rules)")
@click.option("--pad", default=6, help="CSS px kept around the table when cropping (0 = flush)")
def main(out, web_dir, width, height, scale, mobile, pad):
    web_dir = os.path.abspath(web_dir)
    out = os.path.abspath(out)

    tmp = tempfile.mkdtemp(prefix="haydnshot.")
    try:
        with open(os.path.join(web_dir, "opera.json")) as f:
            data = f.read()
        with open(os.path.join(web_dir, "index.html")) as f:
            html = f.read()
        with open(os.path.join(tmp, "page.html"), "w") as f:
            f.write("<script>window.OPERA_DATA=%s;</script>\n%s" % (data, html))
        shutil.copy(os.path.join(web_dir, "d3.v7.min.js"), tmp)

        with sync_playwright() as p:
            launch = dict(args=["--single-process", "--no-zygote", "--no-sandbox",
                                "--disable-gpu", "--allow-file-access-from-files"])
            binary = find_chromium()
            if binary:
                launch["executable_path"] = binary
            browser = p.chromium.launch(**launch)
            context = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=scale,
                is_mobile=mobile, has_touch=mobile)
            page = context.new_page()
            page.goto("file://%s/page.html" % tmp, wait_until="load")
            page.wait_for_selector(".quartet-card", timeout=10000)

            # Visual bounding box of the painted content (text ink for the
            # headings, element boxes for rows/legend). The page centers the table
            # in a wider canvas, so this lets us trim the side margins and sit the
            # last column at the right edge.
            #
            # We deliberately avoid full_page: it widens the viewport to fit the
            # content, which trips the mobile @media (max-width:800px) breakpoint
            # and disables the transform:scale phone layout mid-capture. Instead we
            # keep the device width fixed and just grow the viewport's height to
            # fit, then capture with a clip box.
            measure = """() => {
                const boxes = [];
                document.querySelectorAll('.opus-row, .legend .item')
                    .forEach(e => boxes.push(e.getBoundingClientRect()));
                document.querySelectorAll('h1, .subtitle, .footer').forEach(e => {
                    const r = document.createRange();
                    r.selectNodeContents(e);
                    boxes.push(r.getBoundingClientRect());
                });
                return {
                    left: Math.min(...boxes.map(b => b.left)),
                    right: Math.max(...boxes.map(b => b.right)),
                    top: Math.min(...boxes.map(b => b.top)),
                    bottom: Math.max(...boxes.map(b => b.bottom)),
                };
            }"""
            b = page.evaluate(measure)
            page.set_viewport_size({"width": width, "height": int(b["bottom"]) + 2 * pad + 8})
            b = page.evaluate(measure)
            clip = {
                "x": max(0, b["left"] - pad),
                "y": max(0, b["top"] - pad),
                "width": (b["right"] - b["left"]) + 2 * pad,
                "height": (b["bottom"] - b["top"]) + 2 * pad,
            }
            page.screenshot(path=out, clip=clip)
            browser.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    img = Image.open(out)
    print("wrote %s (%d bytes, %dx%d)" % (out, os.path.getsize(out), img.width, img.height))


if __name__ == "__main__":
    main()
