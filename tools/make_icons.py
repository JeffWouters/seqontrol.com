"""Icon set: white shield, purple cloud / ring / magnifier / check.

The delivered artwork paints the shield navy, which is drawn for a white page.
The lockup used across this site lifts that shield so it reads white with the
purple furniture on top, and the icons now match it: shield pure white, every
purple element untouched, background transparent.

That suits dark browser chrome. On a light strip a white shield disappears, so
the navy original is emitted too and linked behind
`media="(prefers-color-scheme: light)"`.

apple-touch-icon sits on an opaque dark tile — iOS drops alpha onto black, and a
white shield needs a dark ground to read against anyway.

Run: python tools/make_icons.py

This is the only script that writes icons. make_logo_variants.py used to write
favicon-32.png, apple-touch-icon.png and icon-512.png as well, with the shield
lifted to --text rather than white and a transparent apple-touch icon, so
whichever script ran last decided what shipped. Its icon loop was removed on
2026-08-31 rather than the order being documented — the treatment here is the
one the site links, and it is the only one that answers for light browser chrome
or produces favicon.ico at all.

It depends on extract_logo.py, not on make_logo_variants.py: the only input is
assets/seqontrol-symbol.png, which extract_logo.py produces and which this script
recolours itself. With the icon loop gone from make_logo_variants.py, the two
scripts no longer touch a single file in common.

It only runs when invoked directly. At import scope it regenerated the icons as
a side effect of `import make_icons`, which is how sixteen tracked binaries were
rewritten by a script that merely checked the tools still load.
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")
# A working preview, not a site asset, so it is deliberately written outside the repo.
PREVIEW = os.environ.get("SEQONTROL_PREVIEW_DIR", r"Z:\tmp")

PURPLE = (108, 82, 217)
NAVY = (26, 27, 75)
WHITE = (255, 255, 255)
SITE_BG = (11, 15, 23)


def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def shield_to(sym, colour):
    """Repaint only the navy (the shield); leave every purple pixel alone.
    Interpolating rather than thresholding keeps the anti-aliased rim clean."""
    o = sym.copy()
    p = o.load()
    for y in range(o.height):
        for x in range(o.width):
            r, g, b, a = p[x, y]
            if not a:
                continue
            dn, dp = dist((r, g, b), NAVY), dist((r, g, b), PURPLE)
            t = dn / (dn + dp) if (dn + dp) else 1.0     # 1 = purple, 0 = navy
            p[x, y] = tuple(
                int(colour[i] + (PURPLE[i] - colour[i]) * t) for i in range(3)
            ) + (a,)
    return o


def square(sym, size, inset=0.94):
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    s = sym.copy()
    s.thumbnail((int(size * inset), int(size * inset)), Image.LANCZOS)
    canvas.alpha_composite(s, ((size - s.width) // 2, (size - s.height) // 2))
    return canvas


def preview(white_shield, src):
    """Both treatments against both browser chromes, for eyeballing."""
    sheet = Image.new("RGB", (460, 200), (128, 128, 128))
    d = ImageDraw.Draw(sheet)
    for row, (sym, note) in enumerate(((white_shield, "white shield (default)"),
                                       (src, "navy shield (light chrome)"))):
        y = 16 + row * 96
        d.rectangle([0, y, 230, y + 80], fill=(242, 242, 242))
        d.rectangle([230, y, 460, y + 80], fill=(32, 33, 36))
        d.text((6, y + 2), note, fill=(90, 90, 90))
        for half in (0, 230):
            x = half + 26
            for sz in (16, 32, 48):
                c = square(sym, sz)
                sheet.paste(c, (x, y + 26), c)
                x += sz + 30
    os.makedirs(PREVIEW, exist_ok=True)
    sheet.save(os.path.join(PREVIEW, "favicon-final.png"))
    print("preview ok")


def main() -> None:
    symbol = os.path.join(A, "seqontrol-symbol.png")
    if not os.path.exists(symbol):
        raise SystemExit(f"make_icons: {symbol} is missing — run tools/extract_logo.py first")
    src = Image.open(symbol).convert("RGBA")
    white_shield = shield_to(src, WHITE)

    # favicon.ico — white shield, transparent, multi-resolution
    ico_path = os.path.join(ROOT, "favicon.ico")
    square(white_shield, 256).save(
        ico_path, format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("favicon.ico:", os.path.getsize(ico_path) // 1024, "KB — white shield")

    for size, name in ((32, "favicon-32.png"), (512, "icon-512.png")):
        square(white_shield, size).save(os.path.join(A, name), "PNG", optimize=True)
        print(f"{name}: {size}x{size}  {os.path.getsize(os.path.join(A, name))//1024} KB — white shield")

    # light-chrome fallback: the artwork's own navy shield
    square(src, 32).save(os.path.join(A, "favicon-32-light.png"), "PNG", optimize=True)
    print(f"favicon-32-light.png: 32x32  "
          f"{os.path.getsize(os.path.join(A, 'favicon-32-light.png'))//1024} KB — navy shield")

    old = os.path.join(A, "favicon-32-dark.png")
    if os.path.exists(old):
        os.remove(old)
        print("removed favicon-32-dark.png (superseded)")

    # apple-touch: opaque, dark tile so the white shield has something to sit on
    size = 180
    tile = Image.new("RGB", (size, size), SITE_BG)
    s = white_shield.copy()
    s.thumbnail((int(size * 0.74), int(size * 0.74)), Image.LANCZOS)
    tile.paste(s, ((size - s.width) // 2, (size - s.height) // 2), s)
    tile.save(os.path.join(A, "apple-touch-icon.png"), "PNG", optimize=True)
    print(f"apple-touch-icon.png: {size}x{size}  "
          f"{os.path.getsize(os.path.join(A, 'apple-touch-icon.png'))//1024} KB — dark tile")

    preview(white_shield, src)


if __name__ == "__main__":
    main()
