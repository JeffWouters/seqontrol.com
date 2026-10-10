#!/usr/bin/env python3
"""Apply per-page SEO metadata: titles, descriptions, canonicals, Open Graph,
Twitter cards and JSON-LD. Also regenerates sitemap.xml.

Titles and descriptions are hand-written per page and live here rather than
being derived from the copy — generated ones read like generated ones. Titles
lead with what someone would search for and end with the brand, if it fits at all; they are kept
under 60 characters and descriptions between 110 and 160 so neither is
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
        "Microsoft 365 exposure, posture and DMARC for MSPs | SeQontrol",
        "See what your Microsoft 365 tenants over-share, how their posture scores and who can spoof "
        "their domains, for one estate or a whole client book.",
        None),
    "platform.html": (
        "One platform under every product | SeQontrol",
        "One tenancy model, one findings store and a hash-chained audit trail — with a separate, "
        "scoped Entra app and consent for each product.",
        "Platform"),
    "for-msps.html": (
        "Microsoft 365 security for MSPs: every client, one console",
        "One console across every client tenant: exposure, posture, email authentication and "
        "evidence, with capacity pooled across the book and partner margin built in.",
        "For MSPs"),
    "contact.html": (
        "Contact SeQontrol: talk to the people who built it",
        "Book a walkthrough, request a scoped assessment, or get a quote against your actual "
        "estate. You get a reply from the people who built it.",
        "Contact"),
    "guides/index.html": (
        "Microsoft 365 security guides: Copilot, DMARC, audit evidence",
        "Practical guides on Copilot exposure, DMARC enforcement and compliance evidence — written to "
        "be useful whether or not you ever buy anything.",
        "Guides"),
    "guides/what-copilot-can-reach.html": (
        "What Microsoft 365 Copilot can reach, and how to check",
        "Copilot surfaces anything a user can already open. What that means in practice, and how to "
        "find your real blast radius before you roll it out.",
        "What Copilot can reach"),
    "guides/dmarc-without-breaking-mail.html": (
        "DMARC from p=none to p=reject without breaking email",
        "How to get a domain from p=none to p=reject without dropping legitimate mail: sender "
        "inventory, staged policy, and the mistakes that stall most DMARC projects.",
        "DMARC without breaking mail"),
    "guides/evidence-auditors-accept.html": (
        "Microsoft 365 compliance evidence auditors actually accept",
        "Why screenshots are tolerated rather than trusted, what continuous control evidence looks "
        "like, and which controls can never be automated by any tool.",
        "Evidence auditors accept"),
    "pricing.html": (
        "SeQontrol pricing: per user, per domain, MSP partner rates",
        "Every published SeQontrol price: per user, per site, per domain or per tenant, with the "
        "volume bands, the provider rates and what is never metered.",
        "Pricing"),
    "spoofing-report.html": (
        "Free DMARC and email spoofing check | SeQontrol",
        "A free check of your domain's email authentication: SPF, DKIM, DMARC, BIMI and MTA-STS, plus "
        "every source currently sending mail as you.",
        "Free spoofing check"),
    "vs-cipp.html": (
        "CIPP vs SeQontrol: keep CIPP, add evidence and external scans",
        "CIPP manages Microsoft 365 tenants and is free. SeQontrol produces control-tagged evidence. "
        "The honest split for providers already running it.",
        "Comparison"),
    "vs-m365-governance.html": (
        "Syskit, CoreView, AvePoint, Varonis vs SeQontrol",
        "How SeQontrol compares with Microsoft 365 permission and governance specialists, and when "
        "one of those is the better buy.",
        "Comparison"),
    "vs-grc-platforms.html": (
        "Vanta, Drata, Secureframe vs SeQontrol for Microsoft 365",
        "How SeQontrol compares with questionnaire-first GRC platforms on Microsoft 365 control "
        "evidence, and where those platforms are the better choice.",
        "vs GRC platforms"),
    "vs-secure-score.html": (
        "Is Microsoft Secure Score enough? Native M365 vs SeQontrol",
        "How SeQontrol differs from Microsoft Secure Score and native Microsoft 365 reporting, and "
        "when the native tools are enough on their own.",
        "vs Secure Score"),
    "exposure-report.html": (
        "Free Microsoft 365 Copilot oversharing report | SeQontrol",
        "A free, scoped scan of your Microsoft 365 tenant: what is shared externally, what is "
        "over-shared internally, and exactly what to revoke first.",
        "Free exposure report"),
    "limits.html": (
        "What SeQontrol does not do: every limit, stated up front",
        "The planes we detect but do not fix yet, what is not on sale yet, where the "
        "Microsoft-first scope ends, and why readiness is not an audit opinion.",
        "Limits"),
    "about.html": (
        "About SeQontrol: who builds it and why",
        "Who builds SeQontrol, why a Microsoft 365 security and compliance platform was worth "
        "building, and what we will and will not claim about it.",
        "About"),
    "privacy.html": (
        "SeQontrol privacy: what we collect and why",
        "What SeQontrol collects from this website and from a connected tenant, why, how long it "
        "is kept, and who to contact about it.",
        "Privacy"),
    "terms.html": (
        "SeQontrol terms: the plain version",
        "The terms covering use of the SeQontrol website and, in outline, the service — written to "
        "be read rather than to be scrolled past.",
        "Terms"),
    "security.html": (
        "SeQontrol security: what we do with your tenant access",
        "The access SeQontrol asks for, what it does with it, how the audit trail works, and how "
        "to report a vulnerability.",
        "Security"),
    "surface-report.html": (
        "Free website security scan: TLS, headers, DNS | SeQontrol",
        "A free grade of your public web surface: TLS, HTTP headers, cookies, DNS, content and "
        "infrastructure, each failure with the standard it breaks and the fix.",
        "Free surface scan"),
    "products/index.html": (
        "Products and prices: Microsoft 365 security | SeQontrol",
        "Four Microsoft 365 security products you can run today and four on the way: what each "
        "answers, whether it writes to your tenant, and what it costs.",
        "Products"),
    "products/sharecare.html": (
        "ShareCare: Microsoft 365 oversharing and Copilot exposure",
        "See what Microsoft 365 over-shares, externally and to Copilot, across every tenant you "
        "manage — then remediate it safely, with a grace window and undo.",
        "ShareCare"),
    "products/securityportal.html": (
        "SecurityPortal: Microsoft 365 and Entra posture, scored",
        "Continuous Microsoft 365 and Entra security posture on a ladder you climb with scan "
        "evidence, every finding tagged to the control it proves.",
        "SecurityPortal"),
    "products/conditionalaccessportal.html": (
        "ConditionalAccessPortal: Conditional Access paths, coming soon",
        "What your Conditional Access policies actually let through: every policy inventoried, the "
        "access paths mapped, each edge labelled by the authority behind it.",
        "ConditionalAccessPortal"),
    "products/complianceportal.html": (
        "CompliancePortal: Microsoft 365 control evidence (coming soon)",
        "Controls proven by scans, not screenshots: findings your other products already produce, "
        "mapped onto the frameworks you are assessed against and kept current.",
        "CompliancePortal"),
    "products/postureportal.html": (
        "PosturePortal: one posture board per tenant (in development)",
        "The read-only board that answers \u201chow are we doing\u201d without opening every product: "
        "findings, risk and coverage per tenant and across a whole fleet.",
        "PosturePortal"),
    "products/dredd.html": (
        "Dredd: configuration drift governance (in development)",
        "Configuration governance rather than posture scoring: not \u201cthis is unwise\u201d but "
        "\u201cthis is not what you approved\u201d, with two answers \u2014 revert it, or ratify it.",
        "Dredd"),
    "products/webscan.html": (
        "WebScan: free website security grading, from TLS to DNS",
        "Grade the public face of every domain you own — TLS, headers, cookies, DNS, content and "
        "infrastructure — against the standards that define it. Free to run.",
        "WebScan"),
    "products/mailtrust.html": (
        "MailTrust: DMARC enforcement for every domain you manage",
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
#   ANALYTICS = ('<script defer data-domain="seqontrol.com" '
#                'src="https://cdn.example/analytics@1.2.3/script.js" '
#                'integrity="sha384-<digest of that exact file>" '
#                'crossorigin="anonymous"></script>')
#
# A script from another host must carry integrity= and crossorigin=, and
# tools/verify.py fails the build when it does not (README, "Third-party
# code"). That rules out a URL whose content changes in place: self-host such a
# script under js/ instead. The CSP below also has to allow the host, or the
# browser refuses the script whatever its hash.
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


def breadcrumb_ld(label: str, url: str, in_products: bool, in_guides: bool = False) -> str:
    items = [('Home', SITE + '/')]
    if in_products and label != "Products":
        items.append(("Products", f"{SITE}/products/"))
    # A guide's visible breadcrumb reads Guides, so its structured one has to pass through Guides too;
    # it used to jump from Home straight to the guide.
    if in_guides and label != "Guides":
        items.append(("Guides", f"{SITE}/guides/"))
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
def form_origin() -> str:
    """The origin the forms post to, or '' while they still fall back to email.

    Imported here rather than at the top: build_legal imports this module, so a top-level import
    would be circular whenever build_seo runs as the script.
    """
    from urllib.parse import urlsplit
    from build_legal import FORM_ENDPOINT
    if not FORM_ENDPOINT:
        return ""
    parts = urlsplit(FORM_ENDPOINT)
    return f"{parts.scheme}://{parts.netloc}"


# connect-src and form-action name the form backend's origin, and only once FORM_ENDPOINT is set:
# site.js fetches it, and a browser without JavaScript posts the form to it directly. form-action is
# otherwise left out, as before, because it does not fall back to default-src and 'self' alone would
# change nothing a reader can see.
def _csp() -> str:
    origin = form_origin()
    extra = f" {origin}" if origin else ""
    form_action = f"form-action 'self'{extra}; " if origin else ""
    return ('<meta http-equiv="Content-Security-Policy" content="'
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            f"connect-src 'self'{extra}; "
            f"{form_action}"
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
        _csp(),
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
        ld.append(breadcrumb_ld(crumb, url, in_products, rel.startswith("guides/")))
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
    src = src.replace("<head>", "<head>\n" + _csp(), 1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(src)


if __name__ == "__main__":
    for rel in META:
        apply(rel)
    extra = csp_only_pages()
    for rel in extra:
        apply_csp_only(rel)
    sitemap()
    print(f"metadata applied to {len(META)} pages, CSP to {len(META) + len(extra)}; sitemap regenerated")
