#!/usr/bin/env python3
"""Apply per-page SEO metadata: titles, descriptions, canonicals, Open Graph,
Twitter cards and JSON-LD. Also regenerates sitemap.xml.

Titles and descriptions are hand-written per page and live here rather than
being derived from the copy — generated ones read like generated ones. Titles
are kept under 60 characters and descriptions between 110 and 160 so neither is
truncated in a result listing.

Run: python tools/build_seo.py
"""
from __future__ import annotations

import datetime
import glob
import io
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://seqontrol.com"

# page -> (title, description, breadcrumb label or None)
META = {
    "index.html": (
        "SeQontrol - Microsoft 365 - See what is over-shared",
        "ShareCare finds what Microsoft 365 over-shares, SecurityPortal scores your posture, "
        "CompliancePortal turns both into audit evidence, MailTrust stops spoofing.",
        None),
    "platform.html": (
        "SeQontrol - Platform - The layer under every product",
        "One tenancy model, one findings store and a hash-chained audit trail — with a separate, "
        "scoped Entra app and consent for each product.",
        "Platform"),
    "for-msps.html": (
        "SeQontrol - For MSPs - Every client or tenant, one screen",
        "Built provider-first: one console across every client tenant, pooled capacity, fleet "
        "benchmarking, and partner margin built into the plan.",
        "For MSPs"),
    "contact.html": (
        "SeQontrol - Contact - Talk to the people who built it",
        "Book a walkthrough, request a scoped assessment, or get a quote against your actual "
        "estate. You get a reply from the people who built it.",
        "Contact"),
    "guides/index.html": (
        "SeQontrol - Guides - Microsoft 365 security and compliance",
        "Practical guides on Copilot exposure, DMARC enforcement and compliance evidence — written to "
        "be useful whether or not you ever buy anything.",
        "Guides"),
    "guides/what-copilot-can-reach.html": (
        "SeQontrol - Guide - What Copilot can actually reach",
        "Copilot surfaces anything a user can already open. What that means in practice, and how to "
        "find your real blast radius before you roll it out.",
        "What Copilot can reach"),
    "guides/dmarc-without-breaking-mail.html": (
        "SeQontrol - Guide - DMARC without breaking mail",
        "How to get a domain from p=none to p=reject without dropping legitimate mail: sender "
        "inventory, staged policy, and the mistakes that stall most DMARC projects.",
        "DMARC without breaking mail"),
    "guides/evidence-auditors-accept.html": (
        "SeQontrol - Guide - Evidence auditors accept",
        "Why screenshots are tolerated rather than trusted, what continuous control evidence looks "
        "like, and which controls can never be automated by any tool.",
        "Evidence auditors accept"),
    "pricing.html": (
        "SeQontrol - Pricing - What sets your number",
        "Every product with a settled price, listed: per user, per site, per domain or per tenant, "
        "with the suite terms and the volume bands.",
        "Pricing"),
    "spoofing-report.html": (
        "SeQontrol - Free report - Who is sending as you",
        "A free check of your domain's email authentication: SPF, DKIM, DMARC, BIMI and MTA-STS, plus "
        "every source currently sending mail as you.",
        "Free spoofing check"),
    "vs-cipp.html": (
        "SeQontrol - vs CIPP - Where each one wins",
        "CIPP manages Microsoft 365 tenants and is free. SeQontrol produces control-tagged evidence. "
        "The honest split for providers already running it.",
        "Comparison"),
    "vs-m365-governance.html": (
        "SeQontrol - vs M365 governance tools",
        "How SeQontrol compares with Microsoft 365 permission and governance specialists, and when "
        "one of those is the better buy.",
        "Comparison"),
    "vs-grc-platforms.html": (
        "SeQontrol - vs GRC platforms - Where each one wins",
        "How SeQontrol compares with questionnaire-first GRC platforms on Microsoft 365 control "
        "evidence, and where those platforms are the better choice.",
        "vs GRC platforms"),
    "vs-secure-score.html": (
        "SeQontrol - vs Secure Score - What native tooling misses",
        "How SeQontrol differs from Microsoft Secure Score and native Microsoft 365 reporting, and "
        "when the native tools are enough on their own.",
        "vs Secure Score"),
    "exposure-report.html": (
        "SeQontrol - Free report - What Copilot can reach",
        "A free, scoped scan of your Microsoft 365 tenant: what is shared externally, what is "
        "over-shared internally, and exactly what to revoke first.",
        "Free exposure report"),
    "limits.html": (
        "SeQontrol - Limits - What this does not do",
        "The planes that detect but cannot (yet?) fix, where the Microsoft-first scope ends, and why "
        "readiness is not an audit opinion. Written down before you ask.",
        "Limits"),
    "about.html": (
        "SeQontrol - About - Why this exists",
        "Who builds SeQontrol, why a Microsoft 365 security and compliance platform was worth "
        "building, and what we will and will not claim about it.",
        "About"),
    "privacy.html": (
        "SeQontrol - Privacy - What we collect and why",
        "What SeQontrol collects from this website and from a connected tenant, why, how long it "
        "is kept, and who to contact about it.",
        "Privacy"),
    "terms.html": (
        "SeQontrol - Terms - The plain version",
        "The terms covering use of the SeQontrol website and, in outline, the service — written to "
        "be read rather than to be scrolled past.",
        "Terms"),
    "security.html": (
        "SeQontrol - Security - What we do with your access",
        "The access SeQontrol asks for, what it does with it, how the audit trail works, and how "
        "to report a vulnerability.",
        "Security"),
    "surface-report.html": (
        "SeQontrol - Free scan - Your public surface, graded",
        "A free grade of your public web surface: TLS, HTTP headers, cookies, DNS, content and "
        "infrastructure, each failure with the standard it breaks and the fix.",
        "Free surface scan"),
    "products/index.html": (
        "SeQontrol - Products - Each stands alone, all connect",
        "Eight products on one platform: ShareCare, SecurityPortal, WebScan, CompliancePortal, "
        "PosturePortal, MailTrust, Dredd and ConditionalAccessPortal.",
        "Products"),
    "products/sharecare.html": (
        "SeQontrol - ShareCare - Who can reach what, and why",
        "See what Microsoft 365 over-shares, externally and to Copilot, across every tenant you "
        "manage — then remediate it safely, with a grace window and undo.",
        "ShareCare"),
    "products/securityportal.html": (
        "SeQontrol - SecurityPortal - Posture that arrives as evidence",
        "Continuous Microsoft 365 and Entra security posture on a ladder you climb with scan "
        "evidence, every finding tagged to the control it proves.",
        "SecurityPortal"),
    "products/conditionalaccessportal.html": (
        "SeQontrol - ConditionalAccessPortal - Coming soon",
        "What your Conditional Access policies actually let through: every policy inventoried, the "
        "access paths mapped, each edge labelled by the authority behind it.",
        "ConditionalAccessPortal"),
    "products/complianceportal.html": (
        "SeQontrol - CompliancePortal - Coming soon",
        "Controls proven by scans, not screenshots: findings your other products already produce, "
        "mapped onto the frameworks you are assessed against and kept current.",
        "CompliancePortal"),
    "products/postureportal.html": (
        "SeQontrol - PosturePortal - In development",
        "The read-only board that answers \u201chow are we doing\u201d without opening five products: "
        "findings, risk and coverage per tenant and across a whole fleet.",
        "PosturePortal"),
    "products/dredd.html": (
        "SeQontrol - Dredd - In development",
        "Configuration governance rather than posture scoring: not \u201cthis is unwise\u201d but "
        "\u201cthis is not what you approved\u201d, with two answers \u2014 revert it, or ratify it.",
        "Dredd"),
    "products/webscan.html": (
        "SeQontrol - WebScan - What your attacker sees first",
        "Grade the public face of every domain you own — TLS, headers, cookies, DNS, content and "
        "infrastructure — against the standards that define it. Free to run.",
        "WebScan"),
    "products/mailtrust.html": (
        "SeQontrol - MailTrust - SPF, DKIM, DMARC and more, enforced",
        "Take every domain from DMARC monitoring to safe enforcement: real sender inventory, a "
        "staged rollout, and the DNS records written in-product.",
        "MailTrust"),
}

# ---------------------------------------------------------------- analytics
# Paste a single analytics snippet here and re-run to inject it into every
# page. Left empty, the site makes no third-party requests at all — which is
# the current state and a deliberate one.
#
# The site cannot be optimised while it is unmeasured, so this is meant to be
# filled in. Use something cookieless (Plausible, Fathom, GoatCounter) so the
# privacy notice stays short and no consent banner is needed. Example:
#
#   ANALYTICS = '<script defer data-domain="seqontrol.com" ' #               'src="https://plausible.io/js/script.js"></script>'
#
# If you add a script here, update privacy.html — it currently states that no
# third-party analytics run.
ANALYTICS = ""

PRODUCT_CATEGORY = "SecurityApplication"

ORG = """{
  "@context": "https://schema.org",
  "@type": "Organization",
  "@id": "https://seqontrol.com/#organization",
  "name": "SeQontrol",
  "url": "https://seqontrol.com/",
  "logo": "https://seqontrol.com/assets/seqontrol-symbol.png",
  "description": "A multi-tenant platform for Microsoft 365 security, compliance and configuration governance.",
  "parentOrganization": { "@type": "Organization", "name": "JeffOps", "url": "https://jeffops.com/" },
  "sameAs": ["https://jeffops.com/"]
}"""

WEBSITE = """{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "@id": "https://seqontrol.com/#website",
  "url": "https://seqontrol.com/",
  "name": "SeQontrol",
  "inLanguage": "en",
  "publisher": { "@id": "https://seqontrol.com/#organization" }
}"""


def canonical_for(rel: str) -> str:
    if rel == "index.html":
        return SITE + "/"
    if rel.endswith("/index.html"):
        return f"{SITE}/{rel[:-len('index.html')]}"
    return f"{SITE}/{rel}"


def software_ld(name: str, desc: str, url: str) -> str:
    return f"""{{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "{name}",
  "url": "{url}",
  "applicationCategory": "{PRODUCT_CATEGORY}",
  "applicationSubCategory": "Microsoft 365 security and compliance",
  "operatingSystem": "Web-based",
  "description": "{desc}",
  "isPartOf": {{ "@type": "SoftwareApplication", "name": "SeQontrol", "url": "https://seqontrol.com/" }},
  "publisher": {{ "@id": "https://seqontrol.com/#organization" }}
}}"""


def breadcrumb_ld(label: str, url: str, in_products: bool) -> str:
    items = [('Home', SITE + '/')]
    if in_products and label != "Products":
        items.append(("Products", f"{SITE}/products/"))
    items.append((label, url))
    listing = ",\n    ".join(
        f'{{ "@type": "ListItem", "position": {i}, "name": "{n}", "item": "{u}" }}'
        for i, (n, u) in enumerate(items, 1))
    return f"""{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {listing}
  ]
}}"""


def strip_existing(src: str) -> str:
    """Remove the metadata this script owns, so it can be re-run idempotently."""
    # The CSP is owned by this script too and has to be stripped like everything else. It was not,
    # so every run appended another copy to the ten hand-written pages in META. Generated pages hid
    # the bug: their whole head is rebuilt upstream, so they always looked correct. The re.sub has
    # no count, which makes the first run after this fix clean up the copies already on disk.
    src = re.sub(r'\n?<meta http-equiv="Content-Security-Policy"[^>]*>', "", src)
    src = re.sub(r'\n?<link rel="canonical"[^>]*>', "", src)
    src = re.sub(r'\n?<meta property="og:[^"]*"[^>]*>', "", src)
    src = re.sub(r'\n?<meta name="twitter:[^"]*"[^>]*>', "", src)
    src = re.sub(r'\n?<script type="application/ld\+json">[\s\S]*?</script>', "", src)
    return src


# A Content Security Policy, delivered by meta because GitHub Pages serves no custom headers.
#
# script-src can be 'self' with nothing else because this site loads exactly one script, from its own
# origin, and carries no inline blocks: the contact-form handler moved into js/site.js on 2026-08-21
# precisely so this line would not need 'unsafe-inline'. If an inline <script> ever comes back, this
# policy stops it running — which is the point, and is worth more than the convenience it costs.
#
# style-src DOES need 'unsafe-inline', and that is an honest weakness rather than an oversight: the
# pages carry ~380 inline style attributes. It is worth stating plainly that this half of the policy
# buys very little until those move into the stylesheet.
#
# frame-ancestors is deliberately absent: it is ignored in a meta policy and only works as a header,
# so writing it here would look like clickjacking protection the site does not have. The same is true
# of X-Frame-Options. Both need a real host to set them.
CSP = ('<meta http-equiv="Content-Security-Policy" content="'
       "default-src 'self'; "
       "script-src 'self'; "
       "style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; "
       "font-src 'self'; "
       "connect-src 'self'; "
       "base-uri 'self'; "
       "object-src 'none'"
       '">')


def apply(rel: str) -> None:
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    src = io.open(path, encoding="utf-8").read()
    title, desc, crumb = META[rel]
    url = canonical_for(rel)
    in_products = rel.startswith("products/")
    prefix = "../" if "/" in rel else ""

    src = strip_existing(src)
    src = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", src, count=1, flags=re.S)
    src = re.sub(r'<meta name="description" content="[^"]*">',
                 f'<meta name="description" content="{desc}">', src, count=1)

    blocks = [
        CSP,
        f'<link rel="canonical" href="{url}">',
        f'<meta property="og:type" content="{"website" if rel == "index.html" else "article"}">',
        f'<meta property="og:site_name" content="SeQontrol">',
        f'<meta property="og:locale" content="en">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:description" content="{desc}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{SITE}/assets/og-card.png">',
        f'<meta property="og:image:width" content="1200">',
        f'<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="SeQontrol — secure, compliant, confident">',
        f'<meta name="twitter:card" content="summary_large_image">',
    ]

    if ANALYTICS:
        blocks.append(ANALYTICS)

    ld = []
    if rel == "index.html":
        ld += [ORG, WEBSITE]
    if in_products and rel != "products/index.html":
        ld.append(software_ld(crumb, desc, url))
    if crumb:
        ld.append(breadcrumb_ld(crumb, url, in_products))
    for block in ld:
        blocks.append('<script type="application/ld+json">\n' + block + "\n</script>")

    marker = f'<link rel="stylesheet" href="{prefix}css/styles.css">'
    assert marker in src, rel
    src = src.replace(marker, "\n".join(blocks) + "\n" + marker, 1)
    io.open(path, "w", encoding="utf-8").write(src)


def last_modified(rel: str) -> str:
    """The date this page last actually changed, from git.

    It used to be datetime.date.today() for every URL, which had two costs. The honest one: the
    sitemap told crawlers that all 27 pages changed today, every single time the pipeline ran, which
    is precisely the signal <lastmod> exists to give and precisely the way to make it worthless. The
    practical one: it made the generator output differ on every run, so CI could not check that the
    committed HTML is what the generators actually produce - the check this unblocks.

    Falls back to today when git cannot answer: a shallow clone, an untracked new page, or no git at
    all. A slightly wrong date on one URL is better than a build that cannot run.
    """
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel],
                             cwd=ROOT, capture_output=True, text=True, timeout=10)
        stamp = out.stdout.strip()
        if out.returncode == 0 and len(stamp) == 10:
            return stamp
    except (OSError, subprocess.SubprocessError):
        pass
    return datetime.date.today().isoformat()


def sitemap() -> None:
    rows = []
    for rel, (_, _, _) in META.items():
        url = canonical_for(rel)
        priority = "1.0" if rel == "index.html" else (
            "0.9" if rel == "products/index.html" else "0.8")
        rows.append(f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{last_modified(rel)}</lastmod>\n"
                    f"    <changefreq>monthly</changefreq>\n    <priority>{priority}</priority>\n  </url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(rows) + "\n</urlset>\n")
    io.open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(xml)


def csp_only_pages() -> list[str]:
    """Pages on disk that META does not cover. Derived, not listed, so a new page cannot be added
    without a policy by simply not appearing in a hand-kept set."""
    out = []
    for pattern in ("*.html", "*/*.html"):
        for path in glob.glob(os.path.join(ROOT, pattern)):
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            if rel not in META:
                out.append(rel)
    return sorted(out)


def apply_csp_only(rel: str) -> None:
    """A page outside META still gets the policy.

    404.html carries no canonical, no Open Graph and no sitemap entry on purpose — a soft 404 in an
    index helps nobody. None of that is a reason to serve it without a CSP: it is the page an
    attacker probes first, precisely because it renders whatever path was requested.
    """
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    src = io.open(path, encoding="utf-8").read()
    src = re.sub(r'\s*<meta http-equiv="Content-Security-Policy"[^>]*>', "", src)
    src = src.replace("<head>", "<head>\n" + CSP, 1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(src)


if __name__ == "__main__":
    for rel in META:
        apply(rel)
    extra = csp_only_pages()
    for rel in extra:
        apply_csp_only(rel)
    sitemap()
    print(f"metadata applied to {len(META)} pages, CSP to {len(META) + len(extra)}; sitemap regenerated")
