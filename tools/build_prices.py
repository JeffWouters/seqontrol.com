#!/usr/bin/env python3
"""Fill the price blocks on the product pages from tools/prices.py.

Two kinds of marker, both written as an opening and a closing comment so the generator can find its
own output again and replace it in place (idempotent, like every other step here):

  <!--PRICE:key-->...<!--/PRICE-->               one table cell on products/index.html
  <!--PRICE-TIERS:key-->...<!--/PRICE-TIERS-->   the tier cards on a product's own page

Everything between the two comments is owned by this script. Edit prices.py, not the page.

Runs after build_licensing.py and before build_nav.py. It touches nothing those two write, so the
position only matters for the CI reproducibility diff, which runs the whole pipeline in order.

Run: python tools/build_prices.py
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prices import PRODUCT_PAGES, SUMMARY, TIERS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CELL_RE = re.compile(r'( *)<!--PRICE:([a-z]+)-->.*?<!--/PRICE-->', re.S)
TIERS_RE = re.compile(r'( *)<!--PRICE-TIERS:([a-z]+)-->.*?<!--/PRICE-TIERS-->', re.S)


def cell(pad: str, key: str) -> str:
    if key not in SUMMARY:
        raise SystemExit(f"build_prices: <!--PRICE:{key}--> has no entry in prices.SUMMARY")
    spec = SUMMARY[key]
    out = [f'{pad}<!--PRICE:{key}-->', f'{pad}<span class="unit">{spec["unit"]}</span>']
    if spec["rows"]:
        out.append(f'{pad}<dl>')
        for label, fig in spec["rows"]:
            out.append(f'{pad}  <dt>{label}</dt><dd>{fig}</dd>')
        out.append(f'{pad}</dl>')
    if spec["note"]:
        out.append(f'{pad}<span class="note-line">{spec["note"]}</span>')
    out.append(f'{pad}<!--/PRICE-->')
    return "\n".join(out)


def tiers(pad: str, key: str) -> str:
    if key not in TIERS:
        raise SystemExit(f"build_prices: <!--PRICE-TIERS:{key}--> has no entry in prices.TIERS")
    spec = TIERS[key]
    last = len(spec["tiers"]) - 1
    out = [f'{pad}<!--PRICE-TIERS:{key}-->', f'{pad}<div class="flavours">']
    for i, (step, name, fig, suffix, feats) in enumerate(spec["tiers"]):
        # The middle tier is outlined in purple and the top tier is navy, as on the home page ladder.
        css = "flavour" + (" featured" if i == 1 else "") + (" on-navy" if i == last and last > 0 else "")
        out.append(f'{pad}  <div class="{css}">')
        out.append(f'{pad}    <div class="tier">{step}</div>')
        out.append(f'{pad}    <h3>{name}</h3>')
        out.append(f'{pad}    <div class="price">{fig} <small>{suffix}</small></div>')
        out.append(f'{pad}    <ul class="checklist">')
        for f in feats:
            out.append(f'{pad}      <li>{f}</li>')
        out.append(f'{pad}    </ul>')
        out.append(f'{pad}  </div>')
    out.append(f'{pad}</div>')
    if spec.get("volume"):
        lead, bands = spec["volume"]
        out.append(f'{pad}<p class="volume"><span class="label">{lead}</span>')
        for pct, threshold in bands:
            out.append(f'{pad}  <span><b>{pct}</b> {threshold}</span>')
        out.append(f'{pad}  <a href="../pricing.html#{key}">Worked bills and every product&rsquo;s pricing</a>')
        out.append(f'{pad}</p>')
    if spec.get("foot"):
        out.append(f'{pad}<p class="small dim">{spec["foot"]}</p>')
    out.append(f'{pad}<!--/PRICE-TIERS-->')
    return "\n".join(out)


def main() -> None:
    pages = ["products/index.html"] + [f"products/{f}" for f in PRODUCT_PAGES.values()]
    changed = 0
    for rel in pages:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        src = open(path, encoding="utf-8").read()
        out = CELL_RE.sub(lambda m: cell(m.group(1), m.group(2)), src)
        out = TIERS_RE.sub(lambda m: tiers(m.group(1), m.group(2)), out)
        if out != src:
            open(path, "w", encoding="utf-8", newline="\n").write(out)
            changed += 1
            print(f"  {rel}")
    print(f"price blocks filled in {changed} pages")


if __name__ == "__main__":
    main()
