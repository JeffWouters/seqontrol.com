#!/usr/bin/env python3
"""Pre-deploy checks for SeQontrol.com. Exits non-zero on any failure.

Four groups, all of which have caught a real regression at least once:

  links     every internal href/src resolves to a file that exists
  seo       titles, descriptions, canonicals, Open Graph, valid JSON-LD
  markup    tags balance, no duplicate ids, no malformed attributes
  a11y      lang, single h1, no skipped heading levels, alt text, labels,
            landmarks, th scope, keyboard-reachable scroll boxes
  content   the editorial rules the site is committed to — no prices, no
            customer references, no CIS framework names, no re-consent overclaim

Run: python tools/verify.py
"""
from __future__ import annotations

import datetime
import html
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = sorted(
    os.path.join(dp, f)
    for dp, _, fns in os.walk(ROOT)
    for f in fns
    if f.endswith(".html") and ".git" not in dp
)

failures: list[str] = []


def fail(page: str, msg: str) -> None:
    failures.append(f"{os.path.relpath(page, ROOT)}: {msg}")


# --------------------------------------------------------------------- links

def check_links(page: str, src: str) -> None:
    for url in re.findall(r'(?:href|src)="([^"]+)"', src):
        if url.startswith(("http://", "https://", "mailto:", "//", "#", "data:")):
            continue
        target = os.path.join(os.path.dirname(page), url.split("#")[0])
        if not os.path.exists(target):
            fail(page, f"broken link -> {url}")


# -------------------------------------------------------------------- markup

PAIRED = ("div", "table", "section", "article", "ul", "ol", "li", "button", "nav",
          "th", "td", "tr", "thead", "tbody", "aside", "form", "main", "header",
          "footer", "p", "span", "a", "h1", "h2", "h3", "h4", "picture")


def check_markup(page: str, src: str) -> None:
    for tag in PAIRED:
        opened = len(re.findall(rf"<{tag}[ >]", src))
        closed = len(re.findall(rf"</{tag}>", src))
        if opened != closed:
            fail(page, f"<{tag}> unbalanced: {opened} open, {closed} close")

    # the class of bug a naive regex edit introduces: an attribute injected into
    # a tag name, e.g. <thead> becoming <th scope="col"ead>. Note alt="" is
    # legitimate (decorative images) and must not trip this.
    for bad in ('scope="col"ead', '<th scope="col"e', 'scope="col"scope'):
        if bad in src:
            fail(page, f"malformed markup: {bad!r}")
    if re.search(r'<[a-z]+[^>]*"[a-z]+>', src):
        fail(page, "attribute value runs into a tag name")


# ---------------------------------------------------------------------- a11y

class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[int] = []
        self.ids: list[str] = []
        self.labels: set[str] = set()
        self.fields: list[tuple[str, str | None, bool]] = []
        self.img_no_alt = 0
        self.landmarks: set[str] = set()
        self.th = 0
        self.th_scoped = 0
        self.scroll = 0
        self.scroll_reachable = 0
        self.link_text: list[str] = []
        self.unnamed_links = 0
        self._in_a = False
        self._a_buf: list[str] = []
        self._a_named = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(a["id"])
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.headings.append(int(tag[1]))
        if tag == "img" and "alt" not in a:
            self.img_no_alt += 1
        if tag == "a" and a.get("href"):
            self._in_a = True
            self._a_buf = []
            self._a_named = bool(a.get("aria-label") or a.get("aria-labelledby"))
        # An image inside a link supplies that link's name when it carries alt text. The brand
        # lockup relies on exactly this: a decorative symbol with alt="" beside a wordmark with
        # alt="SeQontrol".
        if tag == "img" and self._in_a and a.get("alt", "").strip():
            self._a_named = True
        if tag == "label" and a.get("for"):
            self.labels.add(a["for"])
        if tag in ("input", "select", "textarea"):
            if a.get("type") == "hidden":
                return
            self.fields.append(
                (tag, a.get("id"), bool(a.get("aria-label") or a.get("aria-labelledby"))))
        if tag in ("main", "header", "footer", "nav", "aside"):
            self.landmarks.add(tag)
        if tag == "th":
            self.th += 1
            self.th_scoped += bool(a.get("scope"))
        if tag == "div" and "table-scroll" in a.get("class", ""):
            self.scroll += 1
            self.scroll_reachable += a.get("tabindex") is not None

    # There was no handle_endtag, so _in_a was only ever cleared by the first text node that
    # followed an <a>. An element-only anchor - the brand lockup, which contains two <img> and no
    # text - therefore stayed armed and captured the next text node in the DOCUMENT: feeding real
    # about.html markup produced link_text starting ['Skip to content', 'Menu', ...], attributing
    # the nav toggle's "Menu" to the brand link. The vague-link-text gate below was measuring
    # strings that mostly did not come from links at all, on all 28 pages.
    def handle_endtag(self, tag):
        if tag == "a" and self._in_a:
            text = " ".join(self._a_buf).strip()
            if text:
                self.link_text.append(text)
            elif not self._a_named:
                # No text, no alt, no aria-label: a link a screen reader announces as its bare URL.
                self.unnamed_links += 1
            self._in_a = False

    def handle_data(self, data):
        # Accumulate rather than take the first node: a link whose text is split by a <span> or an
        # <em> was previously judged on its first fragment alone.
        if self._in_a and data.strip():
            self._a_buf.append(data.strip())


def check_a11y(page: str, src: str) -> None:
    p = Page()
    p.feed(src)

    if "<html lang=" not in src:
        fail(page, "no lang on <html>")
    if src.count("<title>") != 1:
        fail(page, "expected exactly one <title>")

    if p.headings.count(1) != 1:
        fail(page, f"expected exactly one h1, found {p.headings.count(1)}")
    prev = 0
    for level in p.headings:
        if prev and level > prev + 1:
            fail(page, f"heading order jumps h{prev} -> h{level}")
        prev = level

    dupes = sorted({i for i in p.ids if p.ids.count(i) > 1})
    if dupes:
        fail(page, f"duplicate ids: {dupes}")
    if p.img_no_alt:
        fail(page, f"{p.img_no_alt} <img> without alt")
    for tag, fid, aria in p.fields:
        if not aria and (not fid or fid not in p.labels):
            fail(page, f"unlabelled <{tag}> id={fid}")
    for landmark in ("main", "header", "footer", "nav"):
        if landmark not in p.landmarks:
            fail(page, f"missing <{landmark}> landmark")
    if p.th and p.th_scoped < p.th:
        fail(page, f"{p.th - p.th_scoped} <th> without scope")
    if p.scroll != p.scroll_reachable:
        fail(page, f"{p.scroll - p.scroll_reachable} scroll box(es) not keyboard reachable")
    vague = [t for t in p.link_text if t.lower() in
             ("here", "click here", "read more", "more", "link", "this")]
    if vague:
        fail(page, f"vague link text: {vague}")
    if p.unnamed_links:
        fail(page, f"{p.unnamed_links} link(s) with no text, no image alt and no aria-label")


# ------------------------------------------------------------------- content

# Each rule is a decision made deliberately; see README "Content rules".
CONTENT_RULES = [
    (r"\bCIS\b|CIS-[A-Z]", "CIS framework reference (site names other frameworks only)"),
    # Prices are published deliberately, and only where a buyer goes looking
    # for them. Everywhere else a figure is a leak — a number in a product
    # page or the home hero ages badly and contradicts the two pages that
    # are maintained. PRICE_PAGES below is the allowlist.
    (r"\$\s?\d", "a price outside the pages that carry pricing"),
    (r"\b\d+\s?%\s?(off|discount)", "a discount percentage outside the pages that carry pricing"),
    # A percentage off IS a price, and it was never exempted on the pricing
    # pages when they started carrying figures. The cost of that was invisible:
    # the volume bands got written as "less 10 per cent" -- which reads just as
    # easily as "less THAN 10 per cent" -- because that is the phrasing that got
    # past this line. A guard that quietly degrades the copy it exists to protect
    # is worse than no guard, so it is now scoped like the price rule it belongs
    # with: allowed on the two maintained pricing pages, refused everywhere else.
    (r"testimonial|customer logo|reference customer|pre-revenue|no customers",
     "a customer reference or a statement about their absence"),
    # The consent overclaim has now come back twice, each time in a phrasing the
    # previous rule did not match. Consent is PER PRODUCT: each product has its
    # own Entra app, verified in AppHost.cs, Connectors/Program.cs and Dredd's
    # GraphDirectoryRefResolver. So this matches the *shape* of the claim rather
    # than the wording that happened to be used last time.
    (r"consents? once|one Entra app(?! per product)|single Entra app"
     r"|one consent|consent covers (every|all)|covers every product's"
     r"|never asks (them |the admin )?for new permissions"
     r"|not (another|a second) trip through onboarding|without re-onboarding"
     r"|no second consent|share one connection|same connection",
     "the consent overclaim — each product has its own Entra app and its own "
     "consent (see README, and the code references in the rule above)"),
    # Four products write into the customer's tenant: Security's
    # RemediationEngine, ConditionalAccess's PolicyWriteBackService, MailTrust's
    # DnsAutomationService and ShareCare's remediation. "Read-only" is true of a
    # scan, of the Visibility tier and of PosturePortal — never of the platform.
    (r"app-only and read-only|platform is read-only|everything is read-only"
     r"|entirely read-only|wholly read-only",
     "a platform-wide read-only claim — four products write to the tenant; "
     "scope it to a scan, to the Visibility tier, or to PosturePortal"),
]


# The ONE page allowed to carry figures. licensing.html used to be the second;
# it was merged into pricing on 2026-08-19, which is one fewer place to drift.
PRICE_PAGES = {"pricing.html"}

# Which CONTENT_RULES state a FIGURE rather than a claim, and are therefore
# allowed on those two pages. Held as indexes rather than sniffed from the
# pattern text: "does it start with a dollar sign" stopped describing the rule
# the moment a second money rule existed, and the second one went unexempted
# for exactly that reason.
PRICE_RULES = {1, 2}   # the $-figure rule and the discount-percentage rule


def check_content(page: str, src: str) -> None:
    rel = os.path.relpath(page, ROOT).replace(os.sep, "/")
    text = re.sub(r"<[^>]+>", " ", src)
    for i, (pattern, why) in enumerate(CONTENT_RULES):
        if i in PRICE_RULES and rel in PRICE_PAGES:
            continue
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            fail(page, f"content rule: {why} — found {m.group(0)!r}")


# ------------------------------------------------------------------------ seo

# 404.html is deliberately noindex, with no canonical and no Open Graph
# identity: a soft-404 in an index helps nobody.
SEO_EXEMPT = {"404.html"}

# Redirect stubs are not pages: they exist so an obvious URL resolves. They are
# noindex, canonical to their target, and carry no chrome — so the page-shaped
# checks below would only ever produce noise.
# Pages kept only to redirect. They are exempt from the a11y, SEO and content checks because they
# are not pages anyone should read - they must simply carry a refresh and a noindex, which is what
# is checked instead.
#
# products/coming.html held all four unreleased products behind anchors until 2026-08-23. Each has
# its own page now, but that URL was in the sitemap and half the site linked to its anchors, so it
# redirects rather than 404s. A meta refresh is the only option available: GitHub Pages serves no
# custom headers, so there is no 301.
REDIRECT_STUBS = {"products/coming.html"}

# 60 is the usual guidance, but the real constraint is pixel width (~600px), so
# a character or two either side is noise. The cap exists to catch titles that
# are genuinely too long, not to force a rewrite of a title someone chose.
TITLE_MAX = 62

_titles: dict[str, str] = {}
_descs: dict[str, str] = {}


def check_seo(page: str, src: str) -> None:
    rel = os.path.relpath(page, ROOT).replace(os.sep, "/")

    m = re.search(r"<title>(.*?)</title>", src, re.S)
    # Measure what a person sees, not the source: "&amp;" is one character on
    # screen and five in the file.
    title = html.unescape(m.group(1).strip()) if m else ""
    if not title:
        fail(page, "no <title>")
    elif len(title) > TITLE_MAX:
        fail(page, f"title is {len(title)} chars (max {TITLE_MAX}, else it truncates in results)")
    if title in _titles and _titles[title] != rel:
        fail(page, f"duplicate <title>, also on {_titles[title]}")
    _titles.setdefault(title, rel)

    d = re.search(r'<meta name="description" content="([^"]*)"', src)
    desc = d.group(1) if d else ""
    if not desc:
        fail(page, "no meta description")
    elif rel not in SEO_EXEMPT and not (110 <= len(desc) <= 160):
        fail(page, f"meta description is {len(desc)} chars (want 110-160)")
    if desc in _descs and _descs[desc] != rel:
        fail(page, f"duplicate meta description, also on {_descs[desc]}")
    _descs.setdefault(desc, rel)

    if rel in SEO_EXEMPT:
        if 'name="robots"' not in src or "noindex" not in src:
            fail(page, "expected a noindex robots meta")
        return

    canon = re.search(r'<link rel="canonical" href="([^"]+)"', src)
    if not canon:
        fail(page, "no canonical link")
    else:
        expected = "https://seqontrol.com/" + ("" if rel == "index.html" else
                                               rel[:-len("index.html")] if rel.endswith("/index.html") else rel)
        if canon.group(1) != expected:
            fail(page, f"canonical is {canon.group(1)}, expected {expected}")

    for prop in ("og:title", "og:description", "og:url", "og:image", "og:type", "og:site_name"):
        if f'property="{prop}"' not in src:
            fail(page, f"missing {prop}")

    og_url = re.search(r'<meta property="og:url" content="([^"]+)"', src)
    if canon and og_url and canon.group(1) != og_url.group(1):
        fail(page, "og:url does not match canonical")

    for block in re.findall(r'<script type="application/ld\+json">([\s\S]*?)</script>', src):
        try:
            json.loads(block)
        except json.JSONDecodeError as exc:
            fail(page, f"invalid JSON-LD: {exc}")


# A <source srcset> that points at a missing file fails silently: the browser just falls back to the
# <img>, the page looks right, and the 69% saving quietly stops happening. Cheap to check, invisible
# to catch any other way.
def check_srcset(page: str, src: str) -> None:
    base = os.path.dirname(page)
    for m in re.finditer(r'<source[^>]*srcset="([^"]+)"', src):
        ref = m.group(1).split()[0]
        if ref.startswith(("http:", "https:", "data:")):
            continue
        if not os.path.exists(os.path.normpath(os.path.join(base, ref))):
            fail(page, f"<source srcset> points at a missing file: {ref}")


# Head tags that must appear exactly once. build_seo.py rebuilds all of these on every run, and it
# strips before it reinserts - except it forgot the CSP, so ten pipeline runs left ten identical
# policies in the head of every hand-written page. Nothing broke, which is why it survived: duplicate
# metadata is invisible in a browser and invisible in a diff you are not looking at. Counting is
# cheap and catches the whole family, not just the one that went wrong.
SINGLETONS = (
    ('http-equiv="Content-Security-Policy"', "content security policy"),
    ('rel="canonical"', "canonical link"),
    ("<title>", "title"),
    ('name="description"', "meta description"),
    ('property="og:title"', "og:title"),
    ('name="twitter:card"', "twitter:card"),
)


# Of the six needles above, four already have an existence check in check_seo: title, description,
# canonical and og:title. These two do not, so absence was invisible - and one of them is the site's
# entire security policy, since GitHub Pages serves no headers to carry it instead. A check that only
# ever fires on n > 1 catches a generator that appends and misses a generator that stops emitting.
MUST_EXIST = ('http-equiv="Content-Security-Policy"', 'name="twitter:card"')

# Which of those a noindex page is allowed to omit. This was written as `needle != MUST_EXIST[0]`,
# i.e. "the CSP is the one that is never exempt" encoded as "the CSP is listed first". Reorder the
# tuple and 404.html starts failing for a missing twitter:card while a deleted CSP goes unnoticed;
# add a third needle and it is silently exempt too. Name the thing instead of indexing it.
SOCIAL_ONLY = {'name="twitter:card"'}


def check_singletons(page: str, src: str) -> None:
    head = src[:src.index("</head>")] if "</head>" in src else src
    for needle, label in SINGLETONS:
        n = head.count(needle)
        if n > 1:
            fail(page, f"{label} appears {n} times in <head>; a generator is appending instead of replacing")
        elif n == 0 and needle in MUST_EXIST:
            # A noindex page carries no social card on purpose - 404.html is deliberately absent
            # from the sitemap, Open Graph and Twitter metadata, because a soft 404 in an index
            # helps nobody. It still needs its CSP: it is the page an attacker probes first.
            if 'name="robots"' in head and "noindex" in head and needle in SOCIAL_ONLY:
                continue
            fail(page, f"{label} is missing from <head>")


# ------------------------------------------------------- availability grouping

# build_nav.py generates each product card's badge, so a badge can no longer disagree with PRODUCTS.
# What it cannot see is the HEADING a card is filed under. On 2026-08-21 index.html grouped Dredd and
# PosturePortal - both "In dev" - beneath "Built, and not released yet", and PosturePortal carried a
# hand-typed "In dev" tag while sitting under that heading. The badge and the heading are the same
# fact stated twice, so they get checked against each other.
AVAIL_HEADINGS = {
    "Available today":              "Built",
    "Built, and not released yet":  "Coming soon",
    "Still in development":         "Under development",
}
# Tolerant of an extra class and of markup or entities inside the heading. Matching only
# class="avail-head" exactly meant `class="avail-head tight"` dropped the heading from the split
# and its cards stopped being checked SILENTLY, which is the worst failure mode a gate can have.
AVAIL_SPLIT_RE = re.compile(r'<h3[^>]*class="[^"]*\bavail-head\b[^"]*"[^>]*>(.*?)</h3>', re.S)

# </?article, for the same reason as build_nav.PCARD_RE - and it matters more here. Unbounded,
# a card with no status span was silently SKIPPED and the following card swallowed into its
# match, so a mis-badged card could be reported under its innocent neighbour's name.
AVAIL_CARD_RE = re.compile(
    r'<article class="pcard tone-([a-z]+)">(?:(?!</?article).)*?<span class="status [a-z]+">([^<]*)</span>', re.S)

# Counted separately so a card with no badge at all is reported rather than passed over.
AVAIL_OPEN_RE = re.compile(r'<article class="pcard tone-([a-z]+)">')

# The groups live inside the .suite block. Without an end boundary the final chunk ran to </html>,
# so every product card lower down the page was judged against the last heading - a false deploy
# block on correct markup, at exactly the spot a card used to sit before it was moved.
#
# Found by counting nested <div>, not by matching indentation: the first attempt bounded on
# "\n      </div>" and silently overshot, because .suite closes at eight spaces and something after
# it closes at six. Indentation is not structure.
DIV_RE = re.compile(r"<div\b|</div>")


def suite_scope(src: str) -> str:
    """The .suite block, or the whole page when there is not one."""
    start = src.find('<div class="suite">')
    if start < 0:
        return src
    depth = 0
    for m in DIV_RE.finditer(src, start):
        depth += 1 if m.group(0) != "</div>" else -1
        if depth == 0:
            return src[start:m.end()]
    return src[start:]


def check_availability(page: str, src: str) -> None:
    if "avail-head" not in src:
        return
    parts = AVAIL_SPLIT_RE.split(suite_scope(src))
    if len(parts) < 3:
        fail(page, "avail-head is present but no availability heading could be read from it")
        return
    # split() yields [before, heading, chunk, heading, chunk, ...]
    for raw, chunk in zip(parts[1::2], parts[2::2]):
        heading = html.unescape(re.sub(r"<[^>]*>", "", raw)).strip()
        heading = " ".join(heading.split())
        expected = AVAIL_HEADINGS.get(heading)
        if expected is None:
            fail(page, f"unknown availability heading {heading!r}; add it to AVAIL_HEADINGS")
            continue
        badged = AVAIL_CARD_RE.findall(chunk)
        opened = AVAIL_OPEN_RE.findall(chunk)
        for tone in opened:
            if tone not in [t for t, _ in badged]:
                fail(page, f"product card tone-{tone} under \"{heading}\" has no status badge")
        for tone, badge in badged:
            if badge.strip() != expected:
                fail(page, f'product card tone-{tone} is badged "{badge.strip()}" but sits under '
                           f'"{heading}", which claims "{expected}"')


# ---------------------------------------------------- unfilled generator output

# The pipeline has one hard ordering dependency: build_legal.py stamps <!--CAPS:key--> markers into
# pricing.html and build_licensing.py fills them. README documents it. Nothing enforced it - running
# the pipeline while skipping build_licensing left pricing.html with seven literal markers and half
# its capability matrices gone, and verify.py printed "all checks passed" and exited 0. The site's
# only page carrying figures would have deployed gutted.
#
# check_scripts() below looks for the same class of leftover, but only ever opens js/site.js, and
# check_content strips comments before it scans - so between them the HTML was never examined.
# An allowlist, like FORMAT_KEYS below, not a wildcard. The pattern used to be any shouty word
# followed by a colon, which matches ordinary authoring comments: `<!-- NOTE:` and `<!-- TODO:`
# both failed the gate, with a message blaming a skipped pipeline step. The site's existing
# `<!-- TO ADD:` and `<!-- FORM ENDPOINT:` comments escaped only by being two words.
#
# .*? with re.S rather than [^>]*, so a marker whose payload contains > is still caught.
MARKER_NAMES = ("CAPS",)
MARKER_RE = re.compile(r"<!--\s*(?:" + "|".join(MARKER_NAMES) + r")\s*:.*?-->", re.S)

# The keys build_legal.build() passes to str.format(). If one of these survives into shipped HTML the
# substitution did not happen, which is how "mailto:{contact}" reached production in js/site.js.
FORMAT_KEYS = ("contact", "operator", "entity", "kvk", "address", "address_html")
FORMAT_RE = re.compile(r"\{(" + "|".join(FORMAT_KEYS) + r")\}")


def check_markers(page: str, src: str) -> None:
    for m in sorted(set(MARKER_RE.findall(src))):
        fail(page, f"unfilled generator marker {m!r}: a pipeline step was skipped or failed")
    # Ignore anything inside a script block - JSON-LD and site.js legitimately contain braces.
    text = re.sub(r"<script[^>]*>.*?</script>", "", src, flags=re.S)
    for name in sorted(set(FORMAT_RE.findall(text))):
        fail(page, f"unsubstituted template placeholder {{{name}}} in shipped HTML")


# ------------------------------------------------------- the script bundle

# On 2026-08-21 the contact-form handler moved out of six generated inline <script> blocks and into
# the static js/site.js. It took two pieces of Python with it, and both survived review because a
# static file is never re-read by the generator that used to fix it up:
#
#   '{contact}'  was a .format() placeholder. Nothing substitutes it in a .js file, so every
#                fallback mailto pointed at the literal address "{contact}".
#   '\n'        was Python's escaping level. In JavaScript a doubled backslash is a LITERAL
#                backslash, so composed email bodies arrived as one line with visible \n markers.
#
# Both were silent: no console error, no failed build, just a dead contact form on the only
# conversion path the site has. These two checks are cheap and catch the whole class.
BACKSLASH = chr(92)
PLACEHOLDER_RE = re.compile(r"\{[a-z_][a-z0-9_]*\}")
COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


def check_scripts() -> None:
    path = os.path.join(ROOT, "js", "site.js")
    if not os.path.exists(path):
        fail("js/site.js", "missing: every page loads it")
        return
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    code = COMMENT_RE.sub("", src)   # comments may legitimately quote either pattern

    for name in sorted(set(PLACEHOLDER_RE.findall(code))):
        fail("js/site.js", f"unsubstituted template placeholder {name} in shipped JavaScript")

    for esc in ("n", "t", "r"):
        if BACKSLASH + BACKSLASH + esc in code:
            fail("js/site.js",
                 f"doubled backslash before '{esc}': in JavaScript that is a literal backslash, "
                 "not an escape. Python escaping that came along from a generated inline script.")


# The form's fallback path composes a mailto from data-contact. Without it the address is empty and
# the submit button silently does nothing useful, which is the failure this whole section exists to
# prevent - so it is checked on the page, not just in the script.
def check_form(page: str, src: str) -> None:
    if 'id="contact-form"' not in src:
        return
    m = re.search(r'<form id="contact-form"[^>]*>', src)
    if not m or 'data-contact="' not in m.group(0):
        fail(page, "contact form has no data-contact; the mailto fallback would have no address")
    elif '@' not in re.search(r'data-contact="([^"]*)"', m.group(0)).group(1):
        fail(page, "data-contact does not look like an email address")


# ------------------------------------------------------------------- sitemap

# The CI reproducibility check cannot police sitemap.xml, because its <lastmod> values come from
# `git log -1` per file and therefore differ either side of a commit: generated before committing
# they carry the PREVIOUS commit's date, and regenerated in CI they carry the new one. That only
# agrees when both happen on the same calendar day, which is why it passed all through 21 August and
# would have failed on the 23rd. deploy.yml excludes the file from that diff for exactly that reason.
#
# So the sitemap needs its own check, and the date is not the part worth checking anyway. The part
# that can genuinely go wrong is COVERAGE: a page added to META and missing from the sitemap, or a
# sitemap entry for a page that no longer exists. That is checked here, once, against the same META
# the generator builds it from.
def check_sitemap() -> None:
    path = os.path.join(ROOT, "sitemap.xml")
    if not os.path.exists(path):
        fail("sitemap.xml", "missing")
        return
    with open(path, encoding="utf-8") as fh:
        xml = fh.read()

    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from build_seo import META, canonical_for  # noqa: E402

    listed = set(re.findall(r"<loc>(.*?)</loc>", xml))
    expected = {canonical_for(rel) for rel in META}

    for url in sorted(expected - listed):
        fail("sitemap.xml", f"page is in build_seo.META but not in the sitemap: {url}")
    for url in sorted(listed - expected):
        fail("sitemap.xml", f"sitemap lists a URL that build_seo.META does not cover: {url}")

    for rel in sorted(META):
        if not os.path.exists(os.path.join(ROOT, rel.replace("/", os.sep))):
            fail("sitemap.xml", f"build_seo.META names a page that does not exist: {rel}")


# ------------------------------------------------------------ security.txt

# RFC 9116 section 2.5. Anything outside this set is an extension field, which the spec permits and
# no consumer understands, so in practice it is a typo.
SECURITY_FIELDS = {"acknowledgments", "canonical", "contact", "encryption",
                   "expires", "hiring", "policy", "preferred-languages"}

# How close to Expires this is still willing to ship. An expired security.txt is worse than none:
# RFC 9116 tells a researcher not to trust one. The failure is silent — nothing about the file
# changes on the day it dies — so the build has to be what notices.
SECURITY_RENEW_DAYS = 30


def check_security_txt() -> None:
    """The file exists, parses, and has not quietly expired.

    verify.py globs *.html, so until now it had never opened this file at all — which is how the
    site came to serve a 404 at the one path RFC 9116 names without anything going red. The deploy
    half of that was upload-pages-artifact dropping dotfiles; this half is that nothing was reading
    the file even locally.

    Worth more here than on most sites: WebScan sells a scan that checks for security.txt, and
    seqontrol.com failing its own product's check is the kind of thing a prospect finds first.
    """
    rel = os.path.join(".well-known", "security.txt")
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        fail(rel, "missing — RFC 9116 names this exact path")
        return

    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    fields: dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.startswith("#"):
            continue
        if ":" not in line:
            fail(rel, f"line {number} is neither blank, a comment, nor a field: {line!r}")
            continue
        name, _, value = line.partition(":")
        # The grammar is "field-name ':' SP value" — exactly one space, nothing leading. Parsers
        # that follow it literally drop anything else.
        if name != name.strip() or not value.startswith(" ") or value.startswith("  "):
            fail(rel, f"line {number} does not match the RFC 9116 grammar: {line!r}")
        key = name.strip().lower()
        if key not in SECURITY_FIELDS:
            fail(rel, f'unrecognised field "{key}"')
        fields[key] = value.strip()

    for required in ("contact", "expires"):
        if required not in fields:
            fail(rel, f"has no {required.title()} field, which RFC 9116 requires")

    canonical = fields.get("canonical")
    if canonical and not canonical.endswith("/.well-known/security.txt"):
        fail(rel, f"Canonical points at {canonical}, not the path this file is served from")

    raw = fields.get("expires")
    if raw:
        try:
            when = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            fail(rel, f"Expires is not an ISO 8601 timestamp: {raw!r}")
            return
        now = datetime.datetime.now(datetime.timezone.utc)
        days = (when - now).days
        if days < 0:
            fail(rel, f"expired {abs(days)} days ago; RFC 9116 tells researchers not to trust it")
        elif days < SECURITY_RENEW_DAYS:
            fail(rel, f"expires in {days} days — renew it before it stops being trusted")
        elif days > 366:
            fail(rel, f"expires in {days} days; RFC 9116 recommends under a year")


# --------------------------------------------------------------------- main

def main() -> int:
    if not PAGES:
        print("no pages found", file=sys.stderr)
        return 1

    for page in PAGES:
        with open(page, encoding="utf-8") as fh:
            src = fh.read()
        rel = os.path.relpath(page, ROOT).replace(os.sep, "/")
        check_links(page, src)
        check_markup(page, src)
        if rel in REDIRECT_STUBS:
            if 'http-equiv="refresh"' not in src or "noindex" not in src:
                fail(page, "redirect stub must carry a refresh and noindex")
            continue
        check_a11y(page, src)
        check_content(page, src)
        check_seo(page, src)
        check_form(page, src)
        check_srcset(page, src)
        check_singletons(page, src)
        check_markers(page, src)
        check_availability(page, src)

    check_scripts()
    check_sitemap()
    check_security_txt()

    print(f"checked {len(PAGES)} pages")
    if failures:
        print(f"\n{len(failures)} failure(s):\n")
        for f in failures:
            print(f"  {f}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
