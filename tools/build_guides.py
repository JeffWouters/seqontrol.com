#!/usr/bin/env python3
"""Build the guides: an index plus long-form pages that answer the questions
buyers actually search for.

These are the only asset on the site that compounds. Every other page has to
convert the traffic it is given; these earn traffic. Each one ends in the free
assessment that matches it, so a reader who came for an answer leaves with an
offer rather than a nav bar.

Written to be useful whether or not the reader ever buys — a guide that only
makes sense as a sales pitch does neither job.

Run: python tools/build_guides.py
"""
from __future__ import annotations

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _chrome import SOURCE, chrome  # noqa: E402
from build_seo import META  # noqa: E402
from build_legal import SIGNUP  # noqa: E402


def seo(spec: dict) -> tuple[str, str]:
    """(title, description) for a guide, from the one place build_seo will not overwrite."""
    rel = "guides/" + spec.get("slug", "index") + ".html"
    if rel not in META:
        raise SystemExit(f"build_guides: {rel} is not in build_seo.META, so it would ship untitled")
    return META[rel][0], META[rel][1]


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "guides")

GUIDES = [
    dict(
        slug="what-copilot-can-reach",
        eyebrow="Guide",
        h1="What Copilot can actually reach in Microsoft 365",
        lede="Copilot does not break permissions. It obeys them — which is exactly the problem, "
             "because most tenants have no idea what their permissions currently allow.",
        offer=("exposure-report.html", "Get a free exposure report",
               "Find out what Copilot can reach in your own tenant."),
        body="""
      <h2>The rule, stated once</h2>
      <p>Copilot can surface, summarise and cite <strong>anything the person asking could already open
        themselves</strong>. It adds no access. It removes the friction that used to hide access nobody
        had audited.</p>
      <p>That distinction matters, because it means a Copilot rollout does not create a new security
        problem. It reveals one you already had, instantly, to every employee at once.</p>

      <h2>Where the exposure actually comes from</h2>
      <p>In practice, four patterns account for most of what surprises people.</p>
      <h3>1. Organisation-wide sharing links</h3>
      <p>A "people in your organisation" link is a transferable key. Creating one does not open the file to
        everyone &mdash; but everyone it reaches can open it, and once they have, Copilot can surface it to
        them. Links sent by email or in a Teams chat are redeemed automatically for up to a hundred
        recipients, links get forwarded, and unless an expiration policy is set they do not expire. Ten
        years of them accumulate, and nobody can say who already holds which.</p>
      <h3>2. Company-wide groups used as convenience</h3>
      <p>"Everyone except external users" started as a shortcut for one intranet page. It is now attached
        to sites nobody remembers granting. It is a common cause of a Copilot answer that contains something
        a colleague should not have seen.</p>
      <h3>3. Inherited permissions on old sites</h3>
      <p>A site created from a template in 2019 inherits an access model designed for a team that no
        longer exists. Nobody checks, because nothing surfaced it — until something did.</p>
      <h3>4. Personal OneDrive sprawl</h3>
      <p>People store things in OneDrive precisely because it feels private, then share a folder once to
        collaborate on one file. The folder stays shared.</p>

      <h2>Why native reporting does not answer this</h2>
      <p>SharePoint Advanced Management's data access governance reports flag broad sharing per site, and
        they are worth running. Sharing information is also retrievable per workload, in separate reports.
        What none of them answers easily is the question you actually need answered: <em>for this person,
        what would Copilot be able to reach, and which of that is sensitive?</em> And each answers it one
        tenant at a time.</p>
      <p>That requires joining the sharing surface to the permission model to the sensitivity of what sits
        behind it — across SharePoint, OneDrive, Teams and the groups underpinning all three. It is a
        crawl, not a report.</p>

      <h2>What to do before you roll out</h2>
      <ol>
        <li><strong>Inventory the sharing surface</strong> across every workload, not one at a time.</li>
        <li><strong>Find the org-wide links and company-wide groups</strong> first. They are the highest
          blast radius per item and usually the easiest to fix.</li>
        <li><strong>Score by sensitivity, not count.</strong> Four hundred shared lunch menus do not
          matter. One shared HR folder does.</li>
        <li><strong>Fix the top of the list, then re-run.</strong> Sharing sprawl regenerates; a one-off
          clean-up decays within months.</li>
        <li><strong>Keep the evidence.</strong> The scan that proves you fixed it is the same artefact
          your auditor wants next quarter.</li>
      </ol>
      <p><a href="products/sharecare.html">ShareCare</a> runs this crawl across SharePoint, OneDrive, Teams and
        the groups behind them, scores it by sensitivity and blast radius, and keeps the history.</p>

      <h2>The uncomfortable part</h2>
      <p>Restricting Copilot tenant-wide — turning off search scope, delaying the rollout — treats the
        symptom and costs you the value you paid for. The exposure was there before Copilot and will
        outlast it. The links, the stale guests and the company-wide groups are a data-access problem
        that happens to have become visible.</p>
"""),

    dict(
        slug="dmarc-without-breaking-mail",
        eyebrow="Guide",
        h1="Getting to DMARC enforcement without breaking your mail",
        lede="Many domains that publish DMARC never get past p=none, which monitors and blocks nothing. The reason is not "
             "ignorance — it is that enforcing without an inventory is genuinely dangerous.",
        offer=("spoofing-report.html", "Check my domain, free",
               "See your current posture and who is sending as you."),
        body="""
      <h2>Why so many domains stop at monitoring</h2>
      <p>Publishing <code>p=none</code> is safe and takes ten minutes. Publishing <code>p=reject</code>
        tells the world to throw away mail that fails authentication — and if you have missed a
        legitimate sender, you have just silently deleted your own invoices, your CRM notifications or
        your payroll provider's mail.</p>
      <p>So people publish <code>p=none</code>, collect reports nobody reads, and stop. The domain stays
        spoofable, which is the thing DMARC existed to fix.</p>

      <h2>The step everyone skips</h2>
      <p><strong>Inventory every sender before you touch the policy.</strong> Not the senders you think
        you have — the ones actually sending. In a typical organisation that list includes several
        systems nobody in IT remembers procuring: a marketing tool, a survey platform, an ancient
        on-premises scanner, a payroll system, and at least one thing a department bought on a card.</p>
      <p>That list only exists in DMARC aggregate reports. You publish <code>p=none</code> with a
        reporting address, wait for real traffic, and read what comes back. Two to four weeks of reports
        beats any amount of asking around.</p>

      <h2>A staged rollout that does not bite</h2>
      <ol>
        <li><strong>Publish <code>p=none</code> with aggregate reporting</strong> to a mailbox you will
          actually process. Nothing changes for anyone.</li>
        <li><strong>Collect for two to four weeks.</strong> Longer if you have monthly batch processes —
          the payroll run you miss is the one that hurts.</li>
        <li><strong>Authenticate the legitimate senders.</strong> Add them to SPF where the record has
          room, and prefer DKIM signing — SPF has a hard limit of ten DNS lookups and large estates hit
          it constantly.</li>
        <li><strong>Move to <code>p=quarantine</code> with a percentage.</strong> Start at
          <code>pct=10</code>. Failures go to junk rather than nowhere, so a mistake is recoverable and
          visible.</li>
        <li><strong>Raise the percentage as the reports stay clean</strong>, then move to
          <code>p=reject</code>.</li>
        <li><strong>Keep watching.</strong> New senders appear whenever someone buys something. A domain
          that reached enforcement and stopped being monitored drifts back into breakage. Keeping that watch
          across every domain, and writing the record changes for supported DNS providers, is what
          <a href="products/mailtrust.html">MailTrust</a> does.</li>
      </ol>

      <h2>Three mistakes worth avoiding</h2>
      <ul>
        <li><strong>Blowing the SPF lookup limit.</strong> Ten DNS lookups, including nested includes.
          Past that, SPF fails permanently and mail that should pass does not.</li>
        <li><strong>Forgetting subdomains.</strong> A policy on the organisational domain does not
          protect subdomains unless you set <code>sp=</code> — and attackers know this.</li>
        <li><strong>Treating it as a project.</strong> It is a state to hold, not a task to close.</li>
      </ul>

      <h2>Why it is worth finishing</h2>
      <p>Major mailbox providers now require DMARC for bulk senders. Brand indicators in the inbox need
        enforcement. Cyber-insurance questionnaires ask. And unauthenticated domains remain one of the
        cheapest attacks available to anyone targeting your customers or your finance team.</p>
"""),

    dict(
        slug="evidence-auditors-accept",
        eyebrow="Guide",
        h1="Evidence auditors accept, and evidence they merely tolerate",
        lede="A screenshot proves a setting was correct on the day somebody remembered to take it. "
             "Most compliance evidence is exactly that, and everyone involved knows it.",
        offer=("exposure-report.html", "See what your tenant could already prove",
               "Start with a free assessment and find out what evidence you already have."),
        body="""
      <h2>The problem with the screenshot</h2>
      <p>The standard artefact in most compliance programmes is an image of a configuration screen,
        pasted into a document, dated by whoever took it. It shows one setting, at one moment, as
        rendered to one person — and it is trivially staged, accidentally or otherwise.</p>
      <p>Auditors accept them because the alternative has historically been nothing. That is tolerance,
        not confidence, and it is why the same control gets re-evidenced every single year.</p>

      <h2>What better evidence has</h2>
      <ul>
        <li><strong>It is reproducible.</strong> Anyone with access can re-run it and get the same
          answer, rather than trusting an image.</li>
        <li><strong>It covers a period, not an instant.</strong> "This held every day for twelve months"
          is a different claim from "this was true in March".</li>
        <li><strong>It knows what it could not check.</strong> Evidence that reports "not assessed" where
          it lacked access is more credible than evidence that quietly reports a pass.</li>
        <li><strong>It is tamper-evident.</strong> A record that can be shown not to have been edited
          after the fact is worth more than one that merely has not been.</li>
        <li><strong>It maps to the control</strong>, not to a product feature — so it can satisfy
          overlapping requirements in several frameworks at once.</li>
      </ul>

      <h2>What cannot be automated, however good the tool</h2>
      <p>This is where most compliance vendors get vague, so plainly: a large share of any framework is
        not technical and never will be. Board oversight. Whether people took the training and understood
        it. Whether your risk assessment reflects reality. Physical security. Whether the vendor review
        actually happened or a box was ticked.</p>
      <p>For a sense of scale, from our own control catalogue: GDPR maps to 91 controls, of which roughly 2 can be
        proved from configuration. It is a process regime with a technical footnote, and any tool
        claiming to make you GDPR compliant is selling you something that does not exist.</p>
      <p>Conversely, ISO 27001 and cloud-specific baselines sit near half automatable, because they are
        written about systems. Knowing which half you are looking at is most of the skill.</p>

      <h2>A practical split</h2>
      <ol>
        <li><strong>Automate everything that lives in configuration</strong>, and re-run it continuously
          rather than annually.</li>
        <li><strong>Attest the rest deliberately</strong>, with a named owner and an expiry date, so an
          attestation cannot outlive its truth.</li>
        <li><strong>Never let a gap score as a pass.</strong> A control you could not assess is a control
          you do not have evidence for, and recording it as green is how programmes rot.</li>
        <li><strong>Keep the security finding visible after the waiver.</strong> Waiving a control
          changes the report; it does not change the estate.</li>
      </ol>

      <h2>The test to apply</h2>
      <p>For any control in your programme, ask: <em>if my auditor asked me to demonstrate this right
        now, live, could I?</em> If the answer is "I would have to go and take a screenshot", that
        control is evidenced by memory and goodwill rather than by proof.</p>
"""),
]

INDEX = dict(
    eyebrow="Guides",
    h1="Microsoft 365 security guides",
    lede="What we have learned building this, written to be useful on its own &mdash; for admins, and for "
         "providers running the same checks across many tenants. No gates, no forms in the middle, no email "
         "required to read the good part.",
)




def depth_fix(html: str) -> str:
    """Chrome is lifted from a root page; guides sit in /guides/."""
    for a, b in (('href="index.html"', 'href="../index.html"'),
                 ('src="assets/', 'src="../assets/'),
                 ('href="assets/', 'href="../assets/'),
                 ('href="favicon.ico"', 'href="../favicon.ico"'),
                 ('href="css/', 'href="../css/'),
                 ('src="js/', 'src="../js/')):
        html = html.replace(a, b)
    for page in ("platform", "products/index", "licensing", "pricing", "for-msps", "contact",
                 "exposure-report", "spoofing-report", "limits", "security", "privacy", "terms",
                 "about", "vs-grc-platforms", "vs-secure-score"):
        html = html.replace(f'href="{page}.html"', f'href="../{page}.html"')
    html = html.replace('href="products/', 'href="../products/')
    html = html.replace('href="../../products/', 'href="../products/')
    return html


BAND_LINE = {
    "exposure-report.html": "Sign up and connect your own tenant, or ask for the free exposure report and "
                            "a person will run it with you.",
    "spoofing-report.html": "Sign up and connect a tenant when you are ready, or start with the free domain "
                            "check, which reads only what your DNS already publishes.",
}


def page(spec, body_html, offer=None) -> str:
    head_open, after_head, footer = chrome()
    # Every guide, and the index, ends on one closing band: sign up, or the free check that fits the
    # guide. It sits after the article, never inside it, so "no forms in the middle" stays true.
    # It replaced an in-body offer box that only ever offered the free report.
    if offer:
        href, label, line = offer
    else:
        href, label, line = ("spoofing-report.html", "Scan a domain first",
                             "Try any of it on your own estate")
    band = (
        '  <section class="cta">\n    <div class="wrap">\n'
        f'      <h2>{line}</h2>\n'
        f'      <p>{BAND_LINE[href]}</p>\n'
        '      <div class="btn-row">\n'
        f'        <a class="btn btn-primary" href="{SIGNUP}">Sign up</a>\n'
        f'        <a class="btn btn-ghost" href="../{href}">{label}</a>\n'
        '      </div>\n    </div>\n  </section>\n\n')
    html = (
        head_open
        # From build_seo.META, not from this file's own copy. build_seo.apply() overwrites both on
        # every run, so a title authored here was decorative at best and misleading at worst - two
        # of the guides' copies had already drifted out of agreement with what actually ships.
        + f"<title>{seo(spec)[0]}</title>\n"
        + f'<meta name="description" content="{seo(spec)[1]}">\n'
        + '<link rel="stylesheet" href="../css/styles.css">\n'
        + after_head
        + '<main id="main">\n\n'
        + '  <section class="hero">\n    <div class="wrap wrap-narrow">\n'
        # Not href="index.html". depth_fix() rewrites that exact string to ../index.html for the
        # brand link in the chrome, and it cannot tell the two apart - so this breadcrumb read
        # "Guides" while pointing at the site homepage, contradicting its own BreadcrumbList JSON-LD.
        # verify.py could not catch it either: ../index.html exists, so the link check was happy.
        # The sentinel survives depth_fix untouched and is resolved below, after it has run.
        + '      <p class="breadcrumb"><a href="__GUIDES_INDEX__">Guides</a></p>\n'
        + f'      <span class="eyebrow">{spec["eyebrow"]}</span>\n'
        + f'      <h1>{spec["h1"]}</h1>\n'
        + f'      <p class="lede">{spec["lede"]}</p>\n'
        + "    </div>\n  </section>\n\n"
        + '  <section>\n    <div class="wrap wrap-narrow">\n'
        + body_html
        + "    </div>\n  </section>\n\n"
        + band
        + "</main>\n\n"
        + footer
        + '<script src="../js/site.js"></script>\n</body>\n</html>\n'
    )
    # Resolve the breadcrumb after depth_fix, never before. A guide sits in /guides/, so its link
    # to the guides index is a plain sibling reference.
    return depth_fix(html).replace("__GUIDES_INDEX__", "index.html")


def build():
    os.makedirs(OUT, exist_ok=True)
    cards = []
    for g in GUIDES:
        io.open(os.path.join(OUT, g["slug"] + ".html"), "w", encoding="utf-8").write(
            page(g, g["body"], g["offer"]))
        cards.append(
            f'        <article class="card">\n'
            f'          <h2><a href="{g["slug"]}.html">{g["h1"]}</a></h2>\n'
            f'          <p>{g["lede"]}</p>\n'
            f'        </article>')
        print("wrote guides/" + g["slug"] + ".html")

    body = ('      <div class="grid grid-2">\n' + "\n".join(cards) + "\n      </div>\n")
    idx = page(INDEX, body)
    # The index does not get a breadcrumb to itself. This used to match the pre-depth_fix string and
    # so removed nothing at all, leaving guides/index.html with a "Guides" crumb pointing at the site
    # homepage. Asserting turns the next silent mismatch into a failed build instead of a live page.
    crumb = '<p class="breadcrumb"><a href="index.html">Guides</a></p>\n      '
    if crumb not in idx:
        raise SystemExit("build_guides: breadcrumb markup changed; the index strip no longer matches")
    idx = idx.replace(crumb, "")
    io.open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(idx)
    print("wrote guides/index.html")


if __name__ == "__main__":
    build()
