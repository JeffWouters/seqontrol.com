#!/usr/bin/env python3
"""Own the two product lists that appear on every page.

The products submenu and the footer's product column were copied into 27 files
by hand, at three different directory depths. Adding a product meant 54 edits
and one of them silently pointing at the wrong path — which is exactly what
happened the first time. One list here, rendered per page depth.

Availability is a property of the product, so the "Soon" tag on a coming-soon
entry is derived rather than remembered.

Run: python tools/build_nav.py
"""
from __future__ import annotations

import html
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# order is deliberate: what is running, roughly by how often it is bought, then what is coming.
#
# The fourth field is the availability LABEL, not a boolean, because "not running" is two
# different states and the site was rendering them as one. "Soon" means built and close;
# "In dev" means real work is still happening. Collapsing them told a visitor that
# PosturePortal and CompliancePortal were equally far away, which is not true in either
# direction. None means it is running today.
PRODUCTS = [
    ("sharecare.html",         "ShareCare",         "--t-sharecare",  None),
    ("securityportal.html",    "SecurityPortal",    "--t-security",   None),
    ("conditionalaccessportal.html", "ConditionalAccessPortal", "--t-condaccess", "Soon"),
    ("webscan.html",           "WebScan",           "--t-webscan",    None),
    ("complianceportal.html",  "CompliancePortal",  "--t-compliance", "Soon"),
    ("postureportal.html",     "PosturePortal",     "--t-posture",    "In dev"),
    ("mailtrust.html",         "MailTrust",         "--t-mailtrust",  None),
    ("dredd.html",             "Dredd",             "--t-dredd",      "In dev"),
]

# The footer's Company column carries the three free assessments — one per
# product a prospect can start with before talking to anyone. It was duplicated
# in the same 28 files as the product list, so it is owned here too.
COMPANY = [
    ("exposure-report.html", "Free exposure report"),
    ("spoofing-report.html", "Free spoofing check"),
    ("surface-report.html",  "Free surface scan"),
    ("guides/index.html",    "Guides"),
    ("about.html",           "About"),
    ("platform.html",        "Platform"),
    ("for-msps.html",        "For MSPs"),
    ("pricing.html",         "Pricing"),
    ("contact.html",         "Contact"),
]

# The footer's Compare column, owned here for the same reason as the two above: it was three
# list items copied into 30 files at two depths, and a third comparison page meant writing it
# 30 times or not at all.
COMPARE = [
    ("vs-cipp.html",            "vs CIPP"),
    ("vs-grc-platforms.html",   "vs GRC platforms"),
    ("vs-m365-governance.html", "vs M365 governance"),
    ("vs-secure-score.html",    "vs Secure Score"),
]

# Trust and Elsewhere were the last two footer columns still copied by hand into 28 files, and they
# had already drifted: the homepage - the most-read page on the site - was missing "What we don't
# do", so it listed three items where every other page listed four. That is exactly the 1-in-28 drift
# this module exists to end, and leaving two columns out of it left the door open.
#
# "What we don't do" leading the Trust column is deliberate: a limits page that is hard to find is a
# limits page nobody believes.
TRUST = [
    ("limits.html",   "What we don't do"),
    ("security.html", "Security"),
    ("privacy.html",  "Privacy"),
    ("terms.html",    "Terms"),
]

# Absolute, so unlike every other list here these take no depth prefix.
ELSEWHERE = [
    ("https://jeffops.com", "JeffOps"),
]

# The top-level nav, owned here for the same reason as everything else below. It was uniform in
# CONTENT across all 32 pages and varied only by relative depth, which is exactly the thing this file
# already computes — and the moment a second entry needed a submenu, the old approach broke: the
# SUBNAV regex replaced EVERY ul.subnav on the page, so a pricing submenu would have been overwritten
# with the product list on the next run.
NAV = [
    ("platform.html",      "Platform", None),
    ("products/index.html", "Products", "products"),
    ("pricing.html",       "Pricing",  None),
    ("for-msps.html",      "For MSPs", None),
    ("guides/index.html",  "Guides",   None),
    ("contact.html",       "Contact",  None),
]

# WAS a Pricing submenu reaching licensing.html. That page was merged into pricing on 2026-08-19 — the
# submenu existed only to bridge a split that no longer exists, so Pricing is a plain entry again.
PRICING_SUB = []

# A product's availability was being stated in five places: the nav badge (here), the Status line on
# its own page, two counts on index.html, a sentence on products/index.html and the pricing panel.
# Three were wrong simultaneously on 2026-08-19. Four of those five are now rendered from this one
# list — nav badge, Status line, card badge and, since the split, the state-note banner. Prose counts
# still are not, and remain the drift risk check_availability exists to bound.
#
# The badge here now matches CARD_STATUS. It used to print a green "Built" for a "Soon" product and
# lean on the sentence beside it to explain that you still cannot have it — the same green-badge-on-
# an-unreleased-product pattern that made four cards wrong on products/index.html. Since 2026-08-23
# these products have their own pages, where the sidebar badge sits inches from a banner saying the
# opposite, so the two are now the same three states throughout: green only for something shipped.
STATUS = {
    None:       ("built", "Built",             "Running today"),
    "Soon":     ("early", "Coming soon",       "Built and running &mdash; not released yet"),
    "In dev":   ("soon",  "Under development", "Not yet available"),
}

# products/index.html shows the same eight products as cards, and each card's availability badge was
# typed by hand. On 2026-08-21 four of the eight were wrong: CompliancePortal, ConditionalAccessPortal
# and Dredd all claimed "Built", so the products index was offering three things nobody can buy, while
# a fourth (PosturePortal) was oversold as merely "Coming soon". The badge is keyed off the card's tone
# class, which already names the product, so it is now derived like the nav badge and the Status line.
#
# Separate from STATUS above because a card badge stands alone. STATUS pairs a badge with a sentence
# that carries the nuance ("Built" + "Coming soon - not yet released"); strip the sentence and that
# badge becomes a lie. Three states, three existing styles: green built, amber close, grey still being
# written.
CARD_STATUS = {
    None:     ("built", "Built"),
    "Soon":   ("early", "Coming soon"),
    "In dev": ("soon",  "Under development"),
}

TONE_LABEL = {tone[4:]: label for _h, _n, tone, label in PRODUCTS}

# The inner match must not leave the card it started in. It was a bare .*? under re.S, which is
# unbounded: a card with no status span of its own runs on and stamps its availability onto whatever
# span comes next. products/index.html carries an unrelated class="status" span in a comparison-table
# cell, so that is not hypothetical, and this function exists precisely because four of eight badges
# were wrong once already.
#
# The bound is </?article, not <article. Blocking only the OPENING tag stops the match at the next
# card rather than at the end of this one - which still lets a badge-less card reach past its own
# </article> and rewrite that table cell. Verified by deleting a card's span and re-running: with
# <article the table cell was rewritten; with </?article nothing outside the card changes.
PCARD_RE = re.compile(
    r'(<article class="pcard tone-([a-z]+)">(?:(?!</?article).)*?)<span class="status [a-z]+">[^<]*</span>',
    re.S)


def card_badge(m: "re.Match") -> str:
    key = m.group(2)
    if key not in TONE_LABEL:
        # Silently returning the tag unchanged is how a mis-typed tone class keeps a stale badge
        # forever. Say so; the run still completes, because a warning that stops the build over a
        # cosmetic class name would be worse than the drift it prevents.
        print(f"  WARNING: pcard tone-{key} is not in PRODUCTS; its badge is not being generated")
        return m.group(0)
    css, text = CARD_STATUS[TONE_LABEL[key]]
    return f'{m.group(1)}<span class="status {css}">{text}</span>'


# THE STATE OF A PRODUCT, SAID AT THE TOP OF ITS OWN PAGE. The four unreleased products shared one
# page until 2026-08-23 and now have four of their own. A page per product is a better read, but it
# reintroduces the risk the shared page removed: a product page that looks exactly like a page for
# something you can buy. So each unreleased product's page opens with this notice, and like the nav
# badge, the card badge and the Status line it is DERIVED from PRODUCTS rather than typed - four
# statements of the same fact, none of which can drift from the others.
#
# Shipped products carry no notice. The page for something you can buy does not need a banner saying
# so, and adding one would make the notice ordinary rather than a warning.
STATE_NOTE = {
    "Soon": (
        "Built, but you cannot buy it yet",
        "This one is built and running, and it is close. You still cannot buy it, and nothing on "
        "this page is an invitation to try. Its price is published so the number is settled before "
        "it ships rather than negotiated after."),
    "In dev": (
        "Still being written",
        "Real work is still happening on this one. It is not available, it carries no list price, "
        "and there is no date &mdash; a date invented to fill this space would be the first thing on this "
        "site you could catch us out on. Ask, and you will get an honest read on where it is."),
}

STATE_RE = re.compile(r'( *)<div class="state-note[^"]*">.*?</div>', re.S)


def state_note(pad: str, label: str | None, tone: str) -> str:
    """The availability banner for one product page, or nothing for a shipped product."""
    if label is None:
        return f'{pad}<div class="state-note"></div>'
    title, body = STATE_NOTE[label]
    css, badge = CARD_STATUS[label]
    return (f'{pad}<div class="state-note tone-{tone[4:]}">\n'
            f'{pad}  <p class="state-head"><span class="status {css}">{badge}</span> {title}</p>\n'
            f'{pad}  <p class="mb0">{body}</p>\n'
            f'{pad}</div>')


# The skip link is the first thing a keyboard user needs and the easiest thing to forget. The 22
# generated pages all had one because chrome() carries it out of contact.html; the six hand-written
# pages did not - including the homepage and every shipped product page, which is precisely the set
# where tabbing past the whole nav costs the most. Every page already had the <main id="main"> target,
# so only the link was missing. Inserted here rather than pasted into six files, because pasting into
# six files is how it came to be missing from six files.
# Footer images sit below the fold on every page, so they have no business competing for bandwidth
# with the content. Two of the three share a src with the header and are cache hits, so the real
# saving is the tagline - one request and about 9 KB per page. Small, but it is free and it is on
# every page.
#
# Header images are deliberately left alone. No loading attribute already means eager, which is what
# an above-the-fold logo should be; adding loading="eager" would be markup that changes nothing.
# Content images are left alone too - they already carry a deliberate eager/lazy split, and the one
# eager case is the homepage hero, which is very likely the LCP element. Lazy-loading that would
# make the number this section exists to improve worse.
# Every .table-scroll carries tabindex="0" - verify.py enforces that, because a scrollable region
# a mouse can pan must also be reachable from a keyboard. What nothing enforced was that the
# resulting focus stop has a NAME: 16 of 23 had none, so a screen reader announced them as bare
# groups, and the 7 that did have one all said "Licence comparison".
#
# Derived from the nearest preceding heading rather than hand-written into 23 places, for the same
# reason the nav and the footer columns are derived: a label typed into markup is a label that
# drifts, and a new table added tomorrow gets named for free. build_licensing sets its own
# per-product label and is left alone - the check below only fills in what is still unnamed.
SCROLL_RE = re.compile(r'<div class="table-wrap table-scroll"(?![^>]*aria-label)([^>]*)>')
HEADING_RE = re.compile(r'<h[1-4][^>]*>(.*?)</h[1-4]>', re.S)
TAGS_RE = re.compile(r'<[^>]*>')


def name_tables(src: str) -> str:
    """Give every unnamed scrollable table an accessible name taken from its own heading."""
    def one(m: "re.Match") -> str:
        heading = HEADING_RE.findall(src[:m.start()])
        if not heading:
            return m.group(0)
        label = html.unescape(TAGS_RE.sub("", heading[-1])).strip()
        label = " ".join(label.split())[:80]
        if not label:
            return m.group(0)
        attrs = m.group(1)
        if "role=" not in attrs:
            attrs += ' role="group"'
        return f'<div class="table-wrap table-scroll"{attrs} aria-label="{html.escape(label, quote=True)}">'
    return SCROLL_RE.sub(one, src)


IMG_RE = re.compile(r'<img\b[^>]*>', re.S)


def lazy_footer(src: str) -> str:
    marker = '<footer class="site-footer">'
    if marker not in src:
        return src
    cut = src.index(marker)
    head, foot = src[:cut], src[cut:]

    def add(m: "re.Match") -> str:
        tag = m.group(0)
        if "loading=" in tag:
            return tag
        return tag[:-1].rstrip() + ' loading="lazy">'

    return head + IMG_RE.sub(add, foot)


# The contact form's fallback path composes a mailto, and it needs an address. It used to carry a
# '{contact}' placeholder that build_legal.py substituted while the handler was a generated inline
# script; when the handler moved into the static js/site.js on 2026-08-21 nothing substituted it any
# more and every fallback resolved to the literal "mailto:{contact}" - a dead link on the only
# conversion path the site has. Stamped here instead, from the one constant that defines it, so the
# address cannot drift from the five forms that use it.
from build_legal import CONTACT  # noqa: E402

CONTACT_FORM_RE = re.compile(r'<form id="contact-form"([^>]*)>')


def stamp_contact(m: "re.Match") -> str:
    # strip any previous stamp first so a second run is a no-op rather than an append
    attrs = re.sub(r'\s*data-contact="[^"]*"', "", m.group(1))
    return '<form id="contact-form"%s data-contact="%s">' % (attrs, CONTACT)


SKIP = '<a class="skip-link" href="#main">Skip to content</a>'


def add_skip(src: str) -> str:
    if SKIP in src or "<body>" not in src:
        return src
    if 'id="main"' not in src:
        return src   # no target: a broken skip link is worse than none
    return src.replace("<body>", "<body>\n" + SKIP, 1)


STATUS_RE = re.compile(r'( *)<h3>Status</h3>\s*<ul>.*?</ul>', re.S)
NAVLINKS = re.compile(r'( *)<ul class="nav-links".*?</ul>\s*</nav>', re.S)
SUBNAV = re.compile(r'( *)<ul class="subnav">.*?</ul>', re.S)
FOOTER = re.compile(r'( *)<h2>Products</h2>\n *<ul>.*?</ul>', re.S)
COMPANY_RE = re.compile(r'( *)<h2>Company</h2>\n *<ul>.*?</ul>', re.S)
COMPARE_RE = re.compile(r'( *)<h2>Compare</h2>\n *<ul>.*?</ul>', re.S)
TRUST_RE = re.compile(r'( *)<h2>Trust</h2>\n *<ul>.*?</ul>', re.S)
ELSEWHERE_RE = re.compile(r'( *)<h2>Elsewhere</h2>\n *<ul>.*?</ul>', re.S)


def status_block(pad: str, label: str | None) -> str:
    css, badge, text = STATUS[label]
    return (f'{pad}<h3>Status</h3>\n'
            f'{pad}<ul><li><span class="status {css}">{badge}</span> {text}</li></ul>')


# GitHub Pages serves 404.html for a miss at any depth, so it is the one page whose own URL is not
# fixed. Every link on it was relative, which is correct for a root page and wrong for this one: at
# /products/typo the browser resolved css/styles.css against /products/ and the branded 404 arrived
# unstyled, with every nav link pointing one directory too deep. Root-absolute URLs are depth-proof.
#
# Done as a pass over the finished page rather than by special-casing root() and prefix(), because
# the head, the body, the nav and the footer are written by four different things and this catches
# all four. Anything already absolute, a fragment, a mail link or a data URI is left alone.
ABSOLUTE = ("http://", "https://", "//", "#", "mailto:", "tel:", "data:", "/")
_URL_RE = re.compile(r'(\b(?:href|src)=")([^"]+)"')


def absolutise(src: str) -> str:
    """Rewrite every relative href/src to a root-absolute one."""
    def one(m):
        url = m.group(2)
        if url.startswith(ABSOLUTE):
            return m.group(0)
        return f'{m.group(1)}/{url}"'
    return _URL_RE.sub(one, src)


# The comparison table on products/index.html names every product in a cell of its own, and those
# cells carried a hand-typed availability badge — one of them, wrong: PosturePortal was tagged "Soon"
# when PRODUCTS has it "In dev", while three equally unreleased products carried nothing at all. This
# is the span PCARD_RE goes out of its way not to overwrite, so it was the one badge on the page with
# nothing keeping it true. Now it is derived from the same row as the nav badge, the card badge and
# the Status line.
#
# Only the unreleased ones are badged. A "Built" tag on four of eight rows is noise; the absence of a
# badge is the signal, and the paragraph under the table says so.
TCELL_RE = re.compile(
    r'(<td><a href="([a-z]+\.html)">[A-Za-z]+</a>)(?:\s*<span class="status [a-z]+">[^<]*</span>)?</td>')


def table_status(m: "re.Match") -> str:
    """Stamp the availability badge into a comparison-table product cell."""
    label = next((lab for href, _n, _t, lab in PRODUCTS if m.group(2) == href), None)
    if label is None:
        return f'{m.group(1)}</td>'
    css, badge = CARD_STATUS[label]
    return f'{m.group(1)} <span class="status {css}">{badge}</span></td>'


def prefix(rel: str) -> str:
    """How a page at `rel` reaches products/."""
    d = os.path.dirname(rel)
    if d == "products":
        return ""
    return "../products/" if d else "products/"


def root(rel: str) -> str:
    """How a page at `rel` reaches the site root."""
    return "../" if os.path.dirname(rel) else ""


def company(pad: str, up: str) -> str:
    out = [f'{pad}<h2>Company</h2>', f'{pad}<ul>']
    for href, name in COMPANY:
        out.append(f'{pad}  <li><a href="{up}{href}">{name}</a></li>')
    out.append(f'{pad}</ul>')
    return "\n".join(out)


def compare(pad: str, up: str) -> str:
    out = [f'{pad}<h2>Compare</h2>', f'{pad}<ul>']
    for href, name in COMPARE:
        out.append(f'{pad}  <li><a href="{up}{href}">{name}</a></li>')
    out.append(f'{pad}</ul>')
    return "\n".join(out)


def trust(pad: str, up: str) -> str:
    out = [f'{pad}<h2>Trust</h2>', f'{pad}<ul>']
    for href, name in TRUST:
        out.append(f'{pad}  <li><a href="{up}{href}">{name}</a></li>')
    out.append(f'{pad}</ul>')
    return "\n".join(out)


def elsewhere(pad: str) -> str:
    """No `up` argument: these are absolute URLs and take no depth prefix."""
    out = [f'{pad}<h2>Elsewhere</h2>', f'{pad}<ul>']
    for href, name in ELSEWHERE:
        out.append(f'{pad}  <li><a href="{href}">{name}</a></li>')
    out.append(f'{pad}</ul>')
    return "\n".join(out)


def pricing_sub(pad: str, up: str) -> str:
    out = [f'{pad}<ul class="subnav">']
    for href, name in PRICING_SUB:
        out.append(f'{pad}  <li><a href="{up}{href}">{name}</a></li>')
    out.append(f'{pad}</ul>')
    return "\n".join(out)


def navlinks(pad: str, pre: str, up: str) -> str:
    """The whole nav, submenus included, at this page's depth."""
    out = [f'{pad}<ul class="nav-links" id="nav-links">']
    for href, label, kind in NAV:
        if kind is None:
            out.append(f'{pad}  <li><a href="{up}{href}">{label}</a></li>')
            continue
        out.append(f'{pad}  <li class="has-sub"><a href="{up}{href}">{label}</a>')
        out.append(subnav(pad + "    ", pre) if kind == "products" else pricing_sub(pad + "    ", up))
        out.append(f'{pad}  </li>')
    out.append(f'{pad}</ul>')
    out.append(pad[:-2] + "</nav>")
    return "\n".join(out)


def subnav(pad: str, pre: str) -> str:
    out = [f'{pad}<ul class="subnav">']
    for href, name, tone, label in PRODUCTS:
        tag = f'<span class="soon-tag">{label}</span>' if label else ""
        out.append(f'{pad}  <li><a href="{pre}{href}">'
                   f'<span class="dot tone-{tone[4:]}"></span>{name}{tag}</a></li>')
    out.append(f'{pad}</ul>')
    return "\n".join(out)


def footer(pad: str, pre: str) -> str:
    out = [f'{pad}<h2>Products</h2>', f'{pad}<ul>']
    for href, name, _tone, _label in PRODUCTS:
        out.append(f'{pad}  <li><a href="{pre}{href}">{name}</a></li>')
    out.append(f'{pad}</ul>')
    return "\n".join(out)


def main() -> None:
    changed = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if not d.startswith((".", "assets", "css", "js", "tools"))]
        for fn in sorted(filenames):
            if not fn.endswith(".html"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            src = open(path, encoding="utf-8").read()
            pre = prefix(rel)

            up = root(rel)

            out = NAVLINKS.sub(lambda m: navlinks(m.group(1), pre, up), src)

            # A product page's Status line is the same fact as its nav badge, so it is rendered from
            # the same row rather than kept in step by hand. Since 2026-08-23 all eight products have
            # a page, unreleased ones included, so this fires for every one of them — and the four
            # that cannot be bought also get the state-note banner below, from the same row.
            if rel.startswith("products/"):
                label = next((lab for href, _n, _t, lab in PRODUCTS if rel == f"products/{href}"), "__none__")
                if label != "__none__":
                    out = STATUS_RE.sub(lambda m: status_block(m.group(1), label), out)
                    tone = next(t for h, _n, t, _l in PRODUCTS if rel == f"products/{h}")
                    out = STATE_RE.sub(lambda m: state_note(m.group(1), label, tone), out)
            out = add_skip(out)
            out = CONTACT_FORM_RE.sub(stamp_contact, out)
            out = lazy_footer(out)
            out = name_tables(out)
            out = PCARD_RE.sub(card_badge, out)

            if rel == "products/index.html":
                out = TCELL_RE.sub(table_status, out)
            out = FOOTER.sub(lambda m: footer(m.group(1), pre), out)
            out = COMPANY_RE.sub(lambda m: company(m.group(1), up), out)
            out = COMPARE_RE.sub(lambda m: compare(m.group(1), up), out)
            out = TRUST_RE.sub(lambda m: trust(m.group(1), up), out)
            out = ELSEWHERE_RE.sub(lambda m: elsewhere(m.group(1)), out)

            if rel == "404.html":
                out = absolutise(out)

            if out != src:
                open(path, "w", encoding="utf-8", newline="\n").write(out)
                changed += 1
                print(f"  {rel}")
    print(f"nav rewritten in {changed} pages")


if __name__ == "__main__":
    main()
