"""Fill the capability matrices into the pricing page's product tabs.

MERGED INTO PRICING, 2026-08-19. This used to write its own page. Two pages then
answered one question between them — pricing said "how much", licensing said
"what you get" — and 71% of their combined 6,474 words was TWO TAB SETS over the
same seven products. A reader tabbed through all seven for a price, then through
all seven again for the capabilities, guided by cross-links each page put in
almost every panel. That is one page that had been cut in half.

build_legal.py now emits a <!--CAPS:key--> marker inside each pricing panel and
this fills it, so a product's price and its capability matrix are one destination.
The old "Terms that apply to the total" block is gone with the merge: platform
minimum, volume, annual-or-monthly and provider pooling are all stated on the
pricing page already, and stating them twice on ONE page would be obvious.

One tab per product; inside each, the technologies it covers and a capability
matrix. The ticks come from the seeded entitlement catalog (Billing's
CatalogSeeder), the technology lists from each product's own connectors and
business plan — not invented.

Markup ships with the tab strip hidden and every panel visible, so the content
survives with JavaScript off; site.js flips it into tabs.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_frameworks import FRAMEWORK_COUNT  # noqa: E402

# Derived from __file__ like every other GENERATOR. This was the absolute path
# r"Z:\Websites\SeQontrol.com\pricing.html", so anywhere but that one machine it either aborted or
# reached across and rewrote the Z: tree instead of the checkout it was invoked in. It owns every
# capability matrix and price cell on the only page carrying figures, and it was the last thing
# stopping the pipeline reproducing itself in CI.
#
# Not the last hardcoded Z: path in tools/, though - an earlier version of this comment claimed it
# was. extract_logo.py, make_icons.py and make_logo_variants.py each still pin ROOT to the absolute
# path. They are asset scripts nothing in the pipeline runs, so CI is unaffected, but the claim was
# wrong and worth correcting rather than leaving as a reason not to look.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "pricing.html")

Y = '<span class="tick" aria-hidden="true">&check;</span><span class="sr-only">Included</span>'
N = '<span class="no" aria-hidden="true">&mdash;</span><span class="sr-only">Not included</span>'

LADDER = [("Visibility", "see it"), ("Governance", "govern it"), ("Automation", "act on it")]
BANDS = [("1 framework", "single regime"), ("3 frameworks", "the usual mix"), ("Unlimited", "every regime")]
ONE = [("Included", "one tier")]
# Two licences, not a ladder. The free one runs everything and remembers
# nothing; Pro is the one that keeps and schedules. Splitting those apart sold
# a distinction no buyer makes.
KEPT = [("Free", "on every tenant"), ("Pro", "per monitored site")]


def rows(items, cols):
    out = []
    for item in items:
        if isinstance(item, str):
            out.append('              <tr class="group"><th colspan="%d" scope="colgroup">%s</th></tr>'
                       % (cols + 1, item))
            continue
        label, cells = item
        out.append('              <tr><th scope="row">%s</th>%s</tr>'
                   % (label, "".join("<td>%s</td>" % c for c in cells)))
    return "\n".join(out)


def table(cols, items, label="Licence comparison"):
    """label names the scrollable region. It is per product because all seven matrices used to
    announce themselves as "Licence comparison" - seven focus stops on one page with identical
    names and nothing to tell them apart."""
    head = "".join('<th class="tier-head" scope="col">%s<small>%s</small></th>' % (n, s) for n, s in cols)
    return ('        <div class="table-wrap table-scroll" tabindex="0" role="group"'
            ' aria-label="' + label + '">\n'
            '          <table class="matrix">\n'
            '            <thead>\n'
            '              <tr><th scope="col">Capability</th>%s</tr>\n'
            '            </thead>\n'
            '            <tbody>\n%s\n            </tbody>\n'
            '          </table>\n'
            '        </div>') % (head, rows(items, len(cols)))


def tech(groups):
    """groups: list of (label, [(name, supported_bool), ...])"""
    out = ['        <div class="tech">', '          <h4>Technologies covered</h4>']
    for label, items in groups:
        if label:
            out.append('          <span class="group-label">%s</span>' % label)
        tags = "".join(
            '<li class="tag %s">%s</li>' % ("on" if ok else "off", name) for name, ok in items)
        out.append('          <ul class="tags">%s</ul>' % tags)
    out.append('        </div>')
    return "\n".join(out)


# --------------------------------------------------------------- product data

PRODUCTS = [
    dict(
        key="sharecare", name="ShareCare", tone="--t-sharecare", status=None,
        counted="Counted per Microsoft 365 user &middot; no seat minimum &middot; $2 / $4 / $6.50 per user, per month",
        tech=[("Microsoft 365", [("SharePoint", 1), ("OneDrive", 1), ("Teams", 1),
                                 ("Entra ID app consents", 1), ("Exchange Online forwarding", 1),
                                 ("Power Platform", 1), ("Power BI", 1)]),
              ("Beyond Microsoft 365", [("Box", 1), ("Slack Connect", 1), ("Google Workspace — roadmap", 0)])],
        cols=LADDER,
        rows=["Price",
              ("Per Microsoft 365 user, per month", ["$2", "$4", "$6.50"]),
              ("At 100 users, per month", ["$200", "$400", "$650"]),
              "Cadence",
              ("On-demand scan, whenever you want one", [Y, Y, Y]),
              ("Scheduled scan cadence", ["Daily", "Every 6 hours", "Hourly"]),
              "Inventory and detection",
              ("Sharing and permission inventory across every connected plane", [Y, Y, Y]),
              ("Risk scoring by sensitivity, exposure and blast radius", [Y, Y, Y]),
              ("Findings history and reports", [Y, Y, Y]),
              ("Fleet view across managed tenants", [Y, Y, Y]),
              ("Oversharing detection — org-wide links and company-wide groups", [N, Y, Y]),
              ("Advanced detections — anonymous links, dormant guests, over-permissioned apps", [N, Y, Y]),
              "Governance",
              ("Policies", [N, Y, Y]),
              ("Owner-delegated access reviews and recertification", [N, Y, Y]),
              ("Approvals", [N, Y, Y]),
              ("Waivers and risk acceptance, with mandatory expiry", [N, Y, Y]),
              ("Evidence packs", [N, Y, Y]),
              "Write access",
              ("Automated remediation write-back, with grace window and undo", [N, N, Y])],
        note=("<strong>Estate size is a quote-time band, not a meter.</strong> The invoice stays on seats, but "
              "at quote time we ask roughly how large the SharePoint and OneDrive estate is — storage volume and "
              "site count. Almost every tenant sits in the standard band. A tenant whose estate is far larger "
              "than its seat count suggests — the 40-user firm with twelve terabytes — is banded accordingly, so "
              "it is priced for what it actually costs to crawl rather than discovering that later. Nothing about "
              "this is metered, gated or counted after the fact."),
        after=("Counted on users rather than on shares or resources — metering the resource count would punish "
               "the messiest estates, which are exactly the ones that need it most, and it could not be quoted "
               "before a discovery scan. Write-back is live for OneDrive permissions and sharing links; Exchange "
               "forwarding, SharePoint site roles, Power Platform and delegated-admin relationships are detected "
               "but not yet revoked app-only."),
    ),
    dict(
        key="securityportal", name="SecurityPortal", tone="--t-security", status=None,
        counted="$1.50 per user with any ShareCare tier &middot; $3.50 standalone &middot; $50 monthly tenant minimum",
        tech=[("Microsoft 365 and Entra", [("Conditional Access", 1), ("MFA enforcement", 1),
                                           ("Entra ID app permissions", 1), ("Sign-in risk signals", 1),
                                           ("Log Analytics (KQL checks)", 1)])],
        cols=ONE,
        rows=["Price",
              ("Per user, per month — with any ShareCare tier", ["$1.50"]),
              ("Per user, per month — standalone", ["$3.50"]),
              ("Monthly minimum per tenant, greater-of", ["$50"]),
              "Capability",
              ("On-demand scan, whenever you want one", [Y]),
              ("Scheduled scan cadence — daily", [Y]),
              ("Microsoft 365 and Entra posture — Conditional Access, MFA, app permissions", [Y]),
              ("Log-analytics checks, where activity logs are exported", [Y]),
              ("Posture ladder, advanced only by scan evidence", [Y]),
              ("Control-reference tags on every finding", [Y]),
              ("Findings history and reports", [Y]),
              ("Fleet-wide across managed tenants", [Y]),
              ("Write access to your tenant", [N])],
        after=("<strong>Why a per-tenant minimum on a per-user product.</strong> Roughly half of what this "
               "checks does not shrink with headcount — a 20-seat tenant has about as many Conditional Access "
               "policies, app registrations and configuration settings as a 2,000-seat one, and every one is "
               "evaluated either way. Per-user alone would price a full posture scan of a small tenant at "
               "thirty dollars. The floor bites below 34 users and does nothing above it.<br><br>"
               "One tier, not a ladder: SecurityPortal is scan-only, so there is no write access to sell on a "
               "higher tier. Remediation lives in the products built to write safely. The log-analytics checks "
               "need the tenant to export activity logs; without that export they report &ldquo;not "
               "assessed&rdquo; rather than a pass. The public web and domain surface is "
               "<a href=\"products/webscan.html\">WebScan</a>, licensed separately and free to run."),
    ),
    dict(
        # Restored 2026-08-21. This matrix was hand-written straight into pricing.html by the commit that
        # put Conditional Access back on three tiers, and the next generator run destroyed it — the exact
        # trap build_legal.py's own header warns about. It lives here now, so it survives a rebuild.
        key="condaccess", name="ConditionalAccessPortal", tone="--t-condaccess", status="Coming soon",
        counted="Per user, per month &middot; $50 monthly tenant minimum &middot; not released yet",
        tech=[("Microsoft 365 and Entra", [("Conditional Access policies", 1), ("Named locations", 1),
                                           ("Device filters", 1), ("Authentication strengths", 1)]),
              ("Policy as code", [("GitHub", 1), ("Azure DevOps", 1)])],
        cols=LADDER,
        rows=["Price",
              ("Per user, per month", ["$0.60", "$1.00", "$1.50"]),
              ("Monthly minimum per tenant, greater-of", ["$50", "$50", "$50"]),
              "Capability",
              ("Conditional Access policy inventory", [Y, Y, Y]),
              ("Access map &mdash; endpoints, policies, resources, allowed and blocked paths", [Y, Y, Y]),
              ("On-demand scan, fleet-wide across managed tenants", [Y, Y, Y]),
              ("Baseline coverage gaps", [N, Y, Y]),
              ("Policy-as-code drift detection &mdash; Git repository, GitHub or Azure DevOps", [N, Y, Y]),
              ("Scheduled repository-versus-tenant comparison, with history", [N, Y, Y]),
              ("Baseline capture &mdash; a tenant&rsquo;s live policy into the repository, as a pull request", [N, Y, Y]),
              ("Approval-gated policy write-back to your tenant", [N, N, Y]),
              ("Deploy repository policy into your tenant, approval-gated", [N, N, Y])],
    ),
    dict(
        key="webscan", name="WebScan", tone="--t-webscan", status=None,
        counted="Free on every tenant &middot; Pro $20 per monitored site, per month",
        tech=[("Discovery", [("Subdomain and asset discovery", 1),
                             ("Certificate transparency monitoring", 1)]),
              ("Transport", [("TLS versions and cipher suites", 1), ("Certificate chain and expiry", 1),
                             ("Client handshake simulation", 1), ("HSTS", 1),
                             ("IPv6 and protocol readiness", 1)]),
              ("HTTP", [("Security headers", 1), ("Cookie flags", 1), ("Redirect chain", 1)]),
              ("DNS", [("CAA", 1), ("DNSSEC", 1), ("Nameserver and record hygiene", 1)]),
              ("Content and infrastructure", [("Exposed paths and files", 1),
                                              ("Open ports and exposed services", 1),
                                              ("security.txt (RFC 9116)", 1),
                                              ("Server and technology disclosure", 1)])],
        cols=KEPT,
        rows=["Price",
              ("Per monitored site, per month", ["$0", "$20"]),
              ("Five sites", ["$0", "$100"]),
              "The scan itself",
              ("On-demand scan, whenever you want one", [Y, Y]),
              ("The complete check set", [Y, Y]),
              ("Scan a site you have not onboarded", [N, Y]),
              ("Subdomain and asset discovery", [Y, Y]),
              ("Certificate transparency lookup", [Y, Y]),
              ("Certificate expiry, checked on every scan", [Y, Y]),
              ("Graded score with the four result states kept apart", [Y, Y]),
              ("Standard and RFC references on every check", [Y, Y]),
              ("Why it matters, and the fix, on every failure", [Y, Y]),
              ("Sites you may keep", ["&mdash;", "Unlimited"]),
              "What happens afterwards",
              ("Results kept once you close the page", [N, Y]),
              ("Scan history and trend over time", [N, Y]),
              ("Findings, waivers and an audit trail", [N, Y]),
              ("Control-reference tags, feeding CompliancePortal as evidence", [N, Y]),
              ("Fleet view across sites and managed tenants", [N, Y]),
              "Watched on a clock, between scans",
              ("Certificate expiry warned before it lapses, not after", [N, Y]),
              ("Certificate transparency monitoring — alerting on new issuance", [N, Y]),
              ("Alerting when discovery turns up a new asset", [N, Y]),
              ("Alerting when a passing check regresses", [N, Y]),
              "Running without you",
              ("Scheduled scans, on a cadence you set", [N, Y]),
              "Write access",
              ("Write access to your DNS or web server", [N, N])],
        note=("<strong>Two licences, not a ladder, and the reason is that the ladder sold a distinction "
              "nobody makes.</strong> Keeping a scan and running it on a schedule were separate tiers; but a "
              "saved site nobody re-scans is a stale record, and a schedule that keeps nothing is a cron job "
              "with no output. Pro grants both.<br><br>"
              "<strong>The free tier is the whole scanner, and that is deliberate.</strong> Every check, the "
              "same severity-weighted score a paid run produces. What it does not do is remember: one URL at "
              "a time, fire and forget, nothing written down when the scan finishes. That is what makes it "
              "free to give away rather than a trial with an expiry date — and it is auto-granted to every "
              "tenant rather than sold."),
        after=("Counted per site rather than per domain, because a site is what gets scanned: one domain can "
               "front several, and each is its own configuration to grade. Nothing caps how many sites you "
               "may add; the count is trued up, never a hard stop.<br><br>"
               "<strong>Pro is $20 against a category that starts an order of magnitude higher.</strong> The "
               "nearest paid comparables run from roughly $60 per asset per month to several hundred, and "
               "they include active vulnerability testing that WebScan does not do. At the other end the free "
               "graders charge nothing and retain nothing. The gap between those two is where this sits, and "
               "it was empty.<br><br>"
               "WebScan never writes anywhere — DNS write-back belongs to MailTrust, which also owns SPF, "
               "DKIM and DMARC; those are mail authentication rather than web surface and are not duplicated "
               "here."),
    ),
    dict(
        key="complianceportal", name="CompliancePortal", tone="--t-compliance", status=None,
        counted="Counted per tenant &middot; $300 / $600 / $900 by frameworks &middot; Attested adds half again",
        tech=[("Microsoft", [("Entra ID", 1), ("Exchange Online", 1), ("SharePoint", 1), ("Teams", 1),
                             ("Intune", 1), ("Azure", 1), ("Purview", 1), ("Power Platform", 1), ("Power BI", 1)]),
              ("Other clouds", [("Google Cloud", 1), ("Amazon Web Services", 1)]),
              ("Engineering", [("GitHub", 1), ("Azure DevOps", 1)]),
              # A representative spread is listed rather than all of them; the count comes from
              # build_frameworks.FAMILIES, which is the catalogue, so the label cannot drift from
              # the list that defines it. It was a literal 24 sitting in a different file.
              (f"Frameworks — {FRAMEWORK_COUNT} in the catalog", [
                  ("SOC 2", 1), ("ISO 27001", 1), ("ISO 27002", 1), ("ISO 27017", 1),
                  ("ISO 27701", 1), ("NIST CSF", 1), ("PCI DSS", 1), ("HIPAA", 1),
                  ("GDPR", 1), ("NIS 2", 1), ("DORA", 1), ("FedRAMP", 1), ("CMMC", 1),
                  ("CSA STAR", 1), ("Essential Eight", 1), ("Cyber Essentials", 1),
                  ("NEN 7510", 1), ("MITRE ATT&amp;CK", 1), ("OWASP", 1),
                  ("A first-party set", 1)])],
        cols=BANDS,
        rows=["Price",
              ("Evidence — per tenant, per month", ["$300", "$600", "$900"]),
              ("Attested — per tenant, per month", ["$450", "$900", "$1,350"]),
              "In every band",
              ("On-demand assessment, whenever you want one", [Y, Y, Y]),
              ("Recurring scheduled assessments", [N, N, N]),
              ("Framework and benchmark catalog", [Y, Y, Y]),
              ("Multi-framework crosswalk — one piece of evidence, many controls", [Y, Y, Y]),
              ("Automated control probes across the connected planes", [Y, Y, Y]),
              ("Google Cloud and AWS coverage via read-only connectors", [Y, Y, Y]),
              ("Evidence reuse from SecurityPortal, ShareCare and MailTrust", [Y, Y, Y]),
              ("Assessment workflow and immutable snapshot trail", [Y, Y, Y]),
              ("Evidence repository and provided-by-client requests", [Y, Y, Y]),
              ("Time-boxed auditor access", [Y, Y, Y]),
              "Scales with the band",
              ("Frameworks in scope", ["1", "3", "Unlimited"]),
              ("Evidence retention", ["12 months", "36 months", "84 months"]),
              "Attested adds, at any band",
              ("Attestation and sign-off, with four-eyes and expiry", [Y, Y, Y]),
              ("Automated evidence capture", [Y, Y, Y]),
              ("Control ownership and remediation tasks", [Y, Y, Y])],
        after=("<strong>Two questions, two axes, so neither answer is bought to get the other.</strong> How many "
               "frameworks you need is scope. Whether you want sign-off and automatic capture is depth. Until "
               "now those shared one number, which meant a company doing SOC 2 alone had to buy every framework "
               "in the catalogue to reach attestation — paying for twenty-three regimes it would never open, to "
               "get one capability. Attested is half again the band price at any band instead.<br><br>"
               "<strong>Not called Automation, and not an accident.</strong> On the ladder products that word "
               "is the tier that writes to your tenant. CompliancePortal writes nothing — it maps, scores, "
               "evidences and attests. Automated evidence <em>capture</em> reads from the estate; it does not "
               "act on it.<br><br>"
               "<strong>Assessments do not yet run on a schedule.</strong> They are raised on demand and the "
               "product has no recurring cadence to sell, which is why that row is empty in all three bands "
               "rather than quietly ticked. What <em>is</em> continuous is the evidence underneath: "
               "SecurityPortal, ShareCare, WebScan and MailTrust scan on their own schedules, and their "
               "control-tagged findings are what an assessment reuses. The scope still holds either way — this "
               "proves the technical controls on the platforms SeQontrol connects to, not a whole-company "
               "compliance programme."),
    ),
    dict(
        key="postureportal", name="PosturePortal", tone="--t-posture", status="Coming soon",
        counted="Not yet priced &middot; still in development",
        tech=[("Reads from", [("ShareCare", 1), ("SecurityPortal", 1), ("WebScan", 1),
                              ("CompliancePortal", 1), ("MailTrust", 1), ("Dredd", 1),
                              ("Connector health", 1)])],
        cols=ONE,
        rows=[("Cross-product findings aggregation", [Y]),
              ("Posture scores, top risks and trends", [Y]),
              ("Connector health and coverage visibility", [Y]),
              ("Saved views and annotations", [Y]),
              ("Fleet overview across managed tenants", [Y]),
              ("Write access to your tenant", [N])],
        after=("<strong>Still in development, and deliberately not on the price list.</strong> PosturePortal "
               "connects to nothing itself — it reads the shared findings store — so it costs almost nothing to "
               "run and will not be sold as a separate line. Exactly how it is packaged is not settled, and "
               "putting a number against something still being built is how a price list stops being trusted. "
               "The capabilities below describe what it does; none of them is something you can buy today."),
    ),
    dict(
        key="mailtrust", name="MailTrust", tone="--t-mailtrust", status=None,
        counted="Counted per sending domain &middot; $15 / $30 / $40 &middot; parked domains $3",
        tech=[("Standards", [("SPF", 1), ("DKIM", 1), ("DMARC", 1), ("BIMI", 1), ("MTA-STS", 1)]),
              ("DNS write-back — live", [("Azure DNS", 1), ("DNSimple", 1)]),
              ("DNS write-back — not yet", [("Cloudflare", 0), ("Route 53", 0),
                                            ("Everything else — guided steps", 0)])],
        cols=LADDER,
        rows=["Price",
              ("Per sending domain, per month", ["$15", "$30", "$40"]),
              ("Per parked domain, per month", ["$3", "$3", "$3"]),
              ("Parked domains included, per sending domain", ["5", "5", "5"]),
              "Cadence",
              ("On-demand scan, whenever you want one", [Y, Y, Y]),
              ("Scheduled scan cadence", ["Daily", "Every 6 hours", "Hourly"]),
              "Assessment",
              ("SPF, DKIM, DMARC, BIMI and MTA-STS posture", [Y, Y, Y]),
              ("DMARC aggregate report ingestion and sender analysis", [Y, Y, Y]),
              ("Findings history and reports", [Y, Y, Y]),
              ("Unlimited domains on every tier", [Y, Y, Y]),
              ("Parked domains watched for silent record changes", [Y, Y, Y]),
              "Governance",
              ("Guided staged rollout toward enforcement", [N, Y, Y]),
              ("Deliverability and authentication alerting", [N, Y, Y]),
              ("Multi-domain fleet view", [N, Y, Y]),
              "Write access",
              ("DNS write-back for supported providers", [N, N, Y])],
        note=("<strong>A parked domain is not priced like a sending one.</strong> Most organisations own far "
              "more domains than they send from — acquisitions, retired brands, defensive and typo registrations "
              "— and those are exactly the ones worth spoofing, because no real mail flows so nothing breaks and "
              "nobody notices. Charging full rate for them would make the rational decision <em>protect fewer "
              "domains</em>, which is the behaviour this product exists to prevent. So a parked domain is $3, "
              "five come with every sending domain, and the classification is measured rather than asserted: a "
              "domain is parked when it has produced no DMARC report volume and no DKIM signing for a full "
              "period. Start sending from it and it reclassifies itself.<br><br>"
              "<strong>Report volume carries an allowance.</strong> Ingesting, parsing and storing DMARC "
              "aggregate reports is a real cost that scales with how much mail a domain sends, not with how many "
              "domains you have — so each domain includes an allowance sized to normal sending volume, and "
              "unusually high-volume domains buy additional blocks. Same test as the deliverability allowance: a "
              "genuine external cost, optional, and bursty. Posture, findings and reports stay uncapped."),
        after=("No tier caps how many domains you may add — the count is a commercial measurement, trued up on "
               "the next invoice, never a hard stop. Ingesting DMARC reports needs a mailbox to receive them; "
               "that is part of onboarding.<br><br><strong>Automation is priced at $40 rather than higher, and "
               "the reason is honest:</strong> DNS write-back is live for Azure DNS and DNSimple only. If your "
               "DNS is anywhere else, that tier gives you a staged rollout and guided records to apply "
               "yourself, not automation — so it is not priced as though it wrote them for you. Cloudflare and "
               "Route 53 are the next two, and the price goes up when they land rather than before."),
    ),
    dict(
        key="dredd", name="Dredd", tone="--t-dredd", status=None,
        counted="Counted per monitored configuration scope",
        tech=[("Control planes", [("Microsoft Entra ID", 1), ("Microsoft 365 tenant config — designed", 0),
                                  ("Intune — designed", 0)])],
        cols=None,
        rows=None,
        after=None,
        note=("<strong>Dredd runs; its licence shape is still being set.</strong> The product is built and the "
              "governance, remediation and bulk-heal paths are live — what is not settled is the unit it should "
              "be counted on. It is the metric we understand least, and rather than guess a shape and reprice "
              "it six months later, it is being set against real configuration scopes first. Ask and you will "
              "get a number. The full capability set is on the "
              "<a href=\"products/dredd.html\">Dredd section</a>."),
    ),
]

# ------------------------------------------------------------------ rendering

# The tab strip and panel wrappers used to be built here, when this file wrote its own page.
# The pricing page owns both since the 2026-08-19 merge, so that loop was building two lists
# nothing read. Removed rather than left commented: dead code that still runs is the kind that
# gets "fixed" years later by somebody who assumes it matters.

# The per-product bodies, keyed for injection. The tab strip, the panel wrapper and the header all
# belong to the pricing page now — this contributes only what goes INSIDE a panel.
BODIES = {}
for p in PRODUCTS:
    body = [tech(p["tech"])]
    if p["cols"]:
        body.append(table(p["cols"], p["rows"], label=f'{p["name"]} licence comparison'))
    if p.get("note"):
        body.append('        <div class="note plain" style="margin-top:0">\n'
                    '          <p class="mb0">%s</p>\n        </div>' % p["note"])
    if p.get("after"):
        body.append('        <p class="after">%s</p>' % p["after"])
    BODIES[p["key"]] = "\n".join(body)

NAMES = {q["key"]: q["name"] for q in PRODUCTS}


def fill(match):
    """One <!--CAPS:a,b--> marker becomes the capability block(s) for those products."""
    keys = [k for k in match.group(1).split(",") if k]
    out = []
    for k in keys:
        if k not in BODIES:
            raise SystemExit("build_licensing: no product named %r to fill a marker with" % k)
        # A panel holding two products (the quoted tab) has to say which matrix is whose.
        label = ("What the %s licence includes" % NAMES[k]) if len(keys) > 1 else "What the licence includes"
        out.append('        <h4 style="margin-top:2rem">%s</h4>\n%s' % (label, BODIES[k]))
    return "\n".join(out)


# Behind a __main__ guard, like every other generator here. This block used to run at import scope,
# which made `import build_licensing` rewrite pricing.html as a side effect - or kill the importing
# process outright, since the no-markers path raises SystemExit. Merely looking at this module's
# data from another script was enough to trigger it.
def main() -> None:
    s = io.open(PAGE, encoding="utf-8").read()
    before = s
    s, filled = re.subn(r'<!--CAPS:([a-z,]*)-->', fill, s)
    if filled == 0:
        raise SystemExit("build_licensing: no CAPS markers in pricing.html — run build_legal.py first")
    io.open(PAGE, "w", encoding="utf-8", newline="\n").write(s)
    print("capability blocks filled:", filled,
          "| matrices:", s.count('class="matrix"') - before.count('class="matrix"'))


if __name__ == "__main__":
    main()
