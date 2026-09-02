#!/usr/bin/env python3
"""Generate the trust pages: privacy, terms and security.

Chrome (head, header, footer) is lifted from an existing page so these never
drift from the rest of the site. Only the <main> differs.

FACTS THIS SCRIPT DOES NOT KNOW — fill them in before relying on these pages:
  · the VAT number, if one is issued (the KvK number is recorded below)
  · the subprocessor list beyond Azure itself — the hosting region IS recorded (West Europe)
  · retention periods for product data, if they differ from what is stated
Everything else here is either verifiable from the platform code or is a
commitment the site already makes elsewhere.

REVIEWED BY A LAWYER, 2026-08-19. That is a fact about the text as it stood on
that date, so a later edit to the wording below is unreviewed again until
somebody says otherwise — which is worth knowing before treating a change here
as cosmetic.

AND THE WORDING LIVES HERE, NOT IN THE HTML. privacy.html, terms.html and
security.html are OUTPUT: this script rewrites them whole on every run, so an
edit made directly to a generated page survives until the next build and then
vanishes without a trace. Any correction — a lawyer's, anyone's — has to land in
this file to exist at all.

Run: python tools/build_legal.py
"""
from __future__ import annotations

import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _chrome import SOURCE, chrome  # noqa: E402
from build_seo import META  # noqa: E402
from build_frameworks import FRAMEWORK_COUNT  # noqa: E402


# "twenty-three regimes" is FRAMEWORK_COUNT minus the one the buyer actually wants. Spelled out
# because it reads as prose, derived because a literal here drifts the moment a framework is added.
_WORDS = {21: "twenty-one", 22: "twenty-two", 23: "twenty-three", 24: "twenty-four",
          25: "twenty-five", 26: "twenty-six", 27: "twenty-seven"}
OTHER_FRAMEWORKS = _WORDS.get(FRAMEWORK_COUNT - 1, str(FRAMEWORK_COUNT - 1))


def seo_title(rel: str) -> str:
    """The page title build_seo will apply. Emitted here so the intermediate file is never wrong."""
    if rel not in META:
        raise SystemExit(f"build_legal: {rel} is not in build_seo.META, so it would ship untitled")
    return META[rel][0]


def seo_desc(rel: str) -> str:
    return META[rel][1]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OPERATOR = 'JeffOps'
CONTACT = 'jeff@jeffops.com'

# The registered entity. Named in full on privacy and terms because both are
# agreements with somebody — a policy that will not say who is bound by it is
# not one — and because the GDPR requires a controller's identity and address.
ENTITY = 'JeffOps'
ADDRESS_LINES = ['Hermesburg 29', '3437 HG Nieuwegein', 'The Netherlands']
KVK = '99353946'
ADDRESS_INLINE = ', '.join(ADDRESS_LINES)

# A page with form=<button label> gets the request form inlined. It lives here
# rather than being pasted into the HTML, because this script regenerates those
# files — anything added to the output by hand is wiped on the next run.
FORM = '''
      <!-- FORM ENDPOINT: paste the URL into BOTH action and data-endpoint.
           With it set the form posts normally and works without JavaScript;
           left empty it falls back to composing a mailto, which can fail
           silently on webmail — see README. -->
      <form id="contact-form" method="post" action="" data-endpoint="" novalidate>
        <input type="hidden" id="cf-topic" name="topic" value="{topic}">
        <div class="field">
          <label for="cf-name">Name</label>
          <input id="cf-name" name="name" type="text" autocomplete="name" required>
        </div>
        <div class="field">
          <label for="cf-email">Work email</label>
          <input id="cf-email" name="email" type="email" autocomplete="email" required>
          <p class="hint">So we can reply. Nothing else is done with it.</p>
        </div>
        <div class="field">
          <label for="cf-org">Organisation</label>
          <input id="cf-org" name="org" type="text" autocomplete="organization">
        </div>
        <div class="field">
          <label for="cf-estate">{estate_label}</label>
          <input id="cf-estate" name="estate" type="text" placeholder="{estate_hint}">
        </div>
        <div class="field">
          <label for="cf-message">Anything we should know?</label>
          <textarea id="cf-message" name="message" rows="4"></textarea>
        </div>
        <button class="btn btn-primary" type="submit" id="cf-submit">{button}</button>
        <p class="hint" id="cf-status" role="status" aria-live="polite"></p>
        <p class="hint">Or email <a href="mailto:{contact}">{contact}</a> directly.</p>
      </form>

      <div class="note plain" id="cf-fallback" hidden>
        <h2>If your mail client did not open</h2>
        <p>Some browsers and webmail setups cannot hand off to a mail app. Nothing is lost — copy
          the message below and send it to <a href="mailto:{contact}">{contact}</a>.</p>
        <label class="sr-only" for="cf-copy">Your message, ready to copy</label>
        <textarea id="cf-copy" rows="9" readonly
                  style="width:100%;font-family:var(--mono);font-size:.85rem"></textarea>
        <p class="mb0"><button class="btn btn-ghost" type="button" id="cf-copy-btn">Copy message</button></p>
      </div>

      <div class="note plain" id="cf-thanks" hidden>
        <h2>Request sent</h2>
        <p class="mb0">It landed. You will get a reply from a person, usually the same working day.</p>
      </div>
'''

FORM_SCRIPT = '''
'''

PAGES = {
    "pricing.html": dict(
        eyebrow="Pricing",
        h1="What sets your number",
        lede="ShareCare is listed in full. Everything else is quoted, and this page says which is "
             "which — plus every factor that moves the number, so you can size it before you ask.",
        form=dict(topic="Pricing for my estate",
                  button="Get a real number",
                  estate_label="Your estate",
                  estate_hint="e.g. 150 users, 2 domains — or 60 managed tenants"),
        body="""
      <h2>What each product counts</h2>
      <p>Every product is priced on the thing that actually drives its cost and its value to you. Those are not
        the same unit, and forcing them into one would misprice most of the portfolio.</p>
      <p><strong>Four of these are available today</strong> &mdash; ShareCare, SecurityPortal, WebScan and
        MailTrust. ConditionalAccessPortal and CompliancePortal are built and close but not released; their
        prices are published so the number is settled before they ship rather than negotiated after. Dredd and
        PosturePortal are further out, and neither carries a list price.</p>
      <div class="table-wrap table-scroll" tabindex="0">
        <table>
          <thead><tr><th scope="col">Product</th><th scope="col">Priced on</th></tr></thead>
          <tbody>
            <tr><th scope="row">ShareCare</th><td>Microsoft 365 users</td></tr>
            <tr><th scope="row">SecurityPortal</th><td>Users, at a lower rate with any ShareCare tier &middot; $50 monthly tenant minimum</td></tr>
            <tr><th scope="row">ConditionalAccessPortal</th><td>Users, on the same terms as SecurityPortal</td></tr>
            <tr><th scope="row">WebScan</th><td>Monitored sites &middot; free on every tenant</td></tr>
            <tr><th scope="row">MailTrust</th><td>Sending domains; parked domains at a lower rate, five included with each</td></tr>
            <tr><th scope="row">CompliancePortal</th><td>Per tenant, banded by how many frameworks are in scope</td></tr>
            <tr><th scope="row">Dredd</th><td>Monitored configuration scope &mdash; quoted, not listed</td></tr>
            <tr><th scope="row">PosturePortal</th><td>Not yet priced &mdash; still in development</td></tr>
          </tbody>
        </table>
      </div>

<section>
    <div class="wrap">
      <div class="section-head">
        <span class="eyebrow">License flavours</span>
        <h2>See it. Govern it. Act on it.</h2>
        <p>Each tier contains the one below. Moving up is an entitlement change, not a migration or a
           reinstall — the capability is already in the product, waiting to be switched on.</p>
      </div>

      <div class="flavours">
        <div class="flavour">
          <div class="tier">Tier 1 · Visibility</div>
          <h3>See it</h3>
          <div class="verb">Know what is actually there</div>
          <ul class="checklist">
            <li><strong>Continuous inventory</strong> of the estate the product covers</li>
            <li><strong>Risk scoring and findings</strong>, deduplicated and tracked over time</li>
            <li><strong>Reporting and export</strong>, including scheduled reports</li>
            <li><strong>Daily scheduled scans</strong>, plus on-demand scans whenever you want one</li>
            <li>Strictly <strong>read-only</strong> — nothing is written to your tenant on this tier</li>
          </ul>
        </div>

        <div class="flavour featured">
          <span class="badge-top">Most common</span>
          <div class="tier">Tier 2 · Governance</div>
          <h3>Govern it</h3>
          <div class="verb">Decide, record and prove</div>
          <ul class="checklist">
            <li>Everything in <strong>Visibility</strong></li>
            <li><strong>Scheduled scans every six hours</strong></li>
            <li><strong>Policies and campaigns</strong> — including owner-delegated access reviews</li>
            <li><strong>Approvals</strong> and four-eyes sign-off on sensitive actions</li>
            <li><strong>Waivers and risk acceptance</strong> with mandatory expiry, so an exception cannot quietly become permanent</li>
            <li><strong>Evidence packs</strong> and the tamper-evident trail behind them</li>
            <li><strong>Fleet views</strong> across every tenant or domain you manage</li>
          </ul>
        </div>

        <div class="flavour">
          <div class="tier">Tier 3 · Automation</div>
          <h3>Act on it</h3>
          <div class="verb">Let it fix things</div>
          <ul class="checklist">
            <li>Everything in <strong>Governance</strong></li>
            <li><strong>Hourly scheduled scans</strong> — the tightest loop between a change and its finding</li>
            <li><strong>Automated remediation and write-back</strong> into the customer's tenant or DNS</li>
            <li><strong>Simulate, then execute</strong> — with a grace window and undo where the plane supports it</li>
            <li><strong>Two independent gates:</strong> the license entitlement <em>and</em> the connector's own remediation consent. Either one off means nothing is written</li>
          </ul>
        </div>
      </div>

      <div class="note scope">
        <h3>Why the top tier is separate</h3>
        <p class="mb0">Tiers 1 and 2 read and record. Tier 3 changes your production tenant. That is a difference in
          kind, not degree, so it is a distinct purchase and a distinct consent — and it stays revocable without
          losing the visibility and evidence you already paid for.</p>
      </div>

      <div class="note plain">
        <h3>Cadence is a tier feature. Looking is not.</h3>
        <p>The tiers set how often a scan runs <em>on a schedule</em> — daily, every six hours, hourly. They never
          limit how often you may look: an <strong>on-demand scan is available on every tier</strong>, at any time,
          as many times as you need. Nothing about an incident should require a purchase order.</p>
        <p class="mb0">The distinction matters and it is deliberate. Continuous scanning is the cost we carry on
          your behalf, and tighter cadence genuinely costs more to run — so a tighter loop between a change and its
          finding is something you buy. But charging <em>per scan</em> would teach you to look less often, which is
          the one behaviour this product exists to prevent. A floor on automatic frequency does the opposite: every
          tier still sees everything, and the higher tiers see it sooner.</p>
      </div>
    </div>
  </section>

      <h2 id="figures" style="margin-top:3rem">The figures, product by product</h2>
      <p>Pick the one you are buying. Everything that applies to the whole account &mdash; the floor, the
        volume bands, and what does and does not move your number &mdash; is below, outside the tabs, because
        it applies whichever you pick.</p>

      <div data-tabs class="tabs-v">
        <div class="tablist" role="tablist" aria-label="Products">
          <button type="button" role="tab" id="tab-sharecare" aria-controls="panel-sharecare" aria-selected="true" tabindex="0" class="tone-sharecare">ShareCare</button>
          <button type="button" role="tab" id="tab-security" aria-controls="panel-security" aria-selected="false" tabindex="-1" class="tone-security">SecurityPortal</button>
          <button type="button" role="tab" id="tab-condaccess" aria-controls="panel-condaccess" aria-selected="false" tabindex="-1" class="tone-condaccess">ConditionalAccessPortal</button>
          <button type="button" role="tab" id="tab-webscan" aria-controls="panel-webscan" aria-selected="false" tabindex="-1" class="tone-webscan">WebScan</button>
          <button type="button" role="tab" id="tab-mailtrust" aria-controls="panel-mailtrust" aria-selected="false" tabindex="-1" class="tone-mailtrust">MailTrust</button>
          <button type="button" role="tab" id="tab-compliance" aria-controls="panel-compliance" aria-selected="false" tabindex="-1" class="tone-compliance">CompliancePortal</button>
          <button type="button" role="tab" id="tab-quoted" aria-controls="panel-quoted" aria-selected="false" tabindex="-1" class="tone-soon">Quoted and unpriced</button>
        </div>
      <div class="product-licence tone-sharecare" role="tabpanel" id="panel-sharecare" aria-labelledby="tab-sharecare" tabindex="0">
        <header>
          <h3>ShareCare</h3>
          <p class="counted">Per Microsoft 365 user, per month</p>
        </header>
        <div class="table-wrap table-scroll" tabindex="0">
          <table class="matrix">
            <thead>
              <tr><th scope="col">&nbsp;</th><th class="tier-head" scope="col">Visibility<small>see it</small></th><th class="tier-head" scope="col">Governance<small>govern it</small></th><th class="tier-head" scope="col">Automation<small>act on it</small></th></tr>
            </thead>
            <tbody>
              <tr><th scope="row">List</th><td>$2</td><td>$4</td><td>$6.50</td></tr>
              <tr><th scope="row">100 users</th><td>$200</td><td>$400</td><td>$650</td></tr>
              <tr><th scope="row">250 users, 10% off</th><td>$450</td><td>$900</td><td>$1,462.50</td></tr>
              <tr><th scope="row">1,000 users, 20% off</th><td>$1,600</td><td>$3,200</td><td>$5,200</td></tr>
            </tbody>
          </table>
        </div>
        <p class="small dim">Volume: 10% off above 100 users, 20% above 500, 30% above 2,000. The discount applies to the whole bill, not just the users past the threshold.</p>
        <ul class="tier-lines">
          <li><b>Visibility</b> — Read-only inventory of sharing and permissions, with risk scoring, findings history, fleet view and daily scheduled scans.</li>
          <li><b>Governance</b> — Adds oversharing and advanced detections, policies, access reviews, approvals, waivers, evidence packs, and six-hourly scans.</li>
          <li><b>Automation</b> — Adds hourly scans plus OneDrive permission and sharing-link write-back with undo, requiring a separate connector remediation consent.</li>
        </ul>
        <p class="after">There is no seat minimum and no platform floor: a twelve-person company pays for twelve people, and nothing is added on top. What each tier unlocks is on the.</p>
<!--CAPS:sharecare-->
      </div>
      <div class="product-licence tone-security" role="tabpanel" id="panel-security" aria-labelledby="tab-security" tabindex="0">
        <header>
          <h3>SecurityPortal</h3>
          <p class="counted">Per user, per month</p>
        </header>
        <p><strong>$1.50 per user with any ShareCare tier</strong>, which is the usual case, or <strong>$3.50 standalone.</strong> Same denominator as ShareCare, so it adds to an existing line rather than starting a new negotiation.</p>
        <div class="note plain">
          <h3>A $50 monthly minimum per tenant</h3>
          <p class="mb0">Charged greater-of, and it exists because roughly half of what this product checks does not shrink with headcount. A 20-seat tenant has about as many Conditional Access policies, app registrations and configuration settings as a 2,000-seat one, and every one of them is evaluated either way. Per-user alone would price a full posture scan of a small tenant at thirty dollars. The floor bites below 34 users; above that the per-user arithmetic is the whole bill.</p>
        </div>
        <p class="after"><b>What you get</b> — read-only Microsoft 365 and Entra posture scans, on demand or daily, with findings history across managed tenants..</p>
<!--CAPS:securityportal-->
      </div>
      <div class="product-licence tone-condaccess" role="tabpanel" id="panel-condaccess" aria-labelledby="tab-condaccess" tabindex="0">
        <header>
          <h3>ConditionalAccessPortal</h3>
          <p class="counted">Per user, per month &middot; <strong>not released yet</strong></p>
        </header>
<p>On the same denominator and the same <strong>$50 monthly tenant minimum</strong> as SecurityPortal, because it answers the same question about the same estate.</p>
        <div class="table-wrap table-scroll" tabindex="0">
          <table class="matrix">
            <thead>
              <tr><th scope="col">&nbsp;</th><th class="tier-head" scope="col">Visibility<small>see it</small></th><th class="tier-head" scope="col">Governance<small>govern it</small></th><th class="tier-head" scope="col">Automation<small>act on it</small></th></tr>
            </thead>
            <tbody>
              <tr><th scope="row">Per user, per month</th><td>$0.60</td><td>$1.00</td><td>$1.50</td></tr>
              <tr><th scope="row">Monthly minimum per tenant, greater-of</th><td>$50</td><td>$50</td><td>$50</td></tr>
            </tbody>
          </table>
        </div>
        <ul class="tier-lines">
          <li><b>Visibility</b> &mdash; Read-only inventory of every Conditional Access policy, and the access map: which endpoints reach which resources, through which policies, and where a path is allowed or blocked.</li>
          <li><b>Governance</b> &mdash; Adds baseline coverage gaps, and policy-as-code drift detection: connect a Git repository of policy, compare it against the live tenant on a schedule, and see field by field where the tenant has moved. Adds capture in the other direction too &mdash; take a tenant&rsquo;s live policy set into the repository as a pull request somebody reviews.</li>
          <li><b>Automation</b> &mdash; Adds approval-gated write-back: enable, disable or move a policy to report-only in your tenant, and deploy the repository&rsquo;s policy to it. Every change needs an approval from somebody other than the person who requested it, and a separate connector consent.</li>
        </ul>
<!--CAPS:condaccess-->
        <p class="after"><strong>Governance reads, Automation writes, and the line between them is the whole ladder.</strong> Everything on Governance &mdash; the baselines, the repository comparison, the schedule, even the capture &mdash; leaves your directory exactly as it found it. Capture writes only to your Git repository, on a new branch, as a pull request somebody has to merge; it never pushes to the branch we read. Automation is the one rung that changes your tenant, and even there the deliberate decision is per change, not per contract: a deployment is approved by somebody other than the person who requested it, and nothing is written without a separate connector consent you grant yourself. Nothing is ever deleted &mdash; a policy your tenant has and the repository does not is reported, never removed.</p>
        <p class="after"><strong>Not released yet.</strong> Built, running and close &mdash; the price is published so it is not a surprise when it ships, not because you can buy it today. <a href="products/conditionalaccessportal.html">What it does, and what it does not</a>.</p>
      </div>
      <div class="product-licence tone-webscan" role="tabpanel" id="panel-webscan" aria-labelledby="tab-webscan" tabindex="0">
        <header>
          <h3>WebScan</h3>
          <p class="counted">Per monitored site, per month</p>
        </header>
        <div class="table-wrap table-scroll" tabindex="0">
          <table class="matrix">
            <thead>
              <tr><th scope="col">&nbsp;</th><th class="tier-head" scope="col">Free<small>on every tenant</small></th><th class="tier-head" scope="col">Pro<small>kept and scheduled</small></th></tr>
            </thead>
            <tbody>
              <tr><th scope="row">List</th><td>$0</td><td>$20</td></tr>
              <tr><th scope="row">5 sites</th><td>$0</td><td>$100</td></tr>
              <tr><th scope="row">25 sites</th><td>$0</td><td>$500</td></tr>
            </tbody>
          </table>
        </div>
        <p class="small dim">One paid licence, not a ladder &mdash; keeping a scan and scheduling it were separate tiers, and that sold a distinction nobody makes: a saved site nobody re-scans is a stale record, and a schedule that keeps nothing is a cron job with no output.</p>
        <ul class="tier-lines">
          <li><b>Free</b> — The complete check set on demand, graded with references and fixes — nothing kept once you close the page.</li>
          <li><b>Pro</b> — Keeps results, history and audit trail, scans on a schedule, and alerts on expiry, new assets and regressions.</li>
        </ul>
        <div class="note plain">
          <h3>WebScan is priced on its own</h3>
          <p class="mb0">A tenant that arrived through a free scan is one we would not otherwise have, and putting a minimum in front of them would eat the funnel it sits downstream of. Nothing is added when a second product applies from that point.</p>
        </div>
        <div class="note plain">
          <h3>Discovered subdomains are free, and stay free until you say otherwise</h3>
          <p class="mb0">Pro looks for hostnames under a site you already pay for and lists what it finds &mdash; the
            name, whether it still resolves, where it last pointed. That costs nothing and is never billed, however
            many turn up. They are listed, not scanned. Promoting one to a monitored site is a button you press, and
            only then does it get the full check suite and only then does it count. Nothing here can raise your bill
            on its own, which is deliberate: an estate that grows on a timer would be an invoice that grows on a
            timer. Coverage is partial and improving &mdash; the <a href="limits.html">limits page</a> says how.</p>
        </div>
        <p class="after">Scanning is never counted &mdash; only sites you chose to keep, once per billing period each, however often they run..</p>
<!--CAPS:webscan-->
      </div>
      <div class="product-licence tone-mailtrust" role="tabpanel" id="panel-mailtrust" aria-labelledby="tab-mailtrust" tabindex="0">
        <header>
          <h3>MailTrust</h3>
          <p class="counted">Per domain, per month</p>
        </header>
        <div class="table-wrap table-scroll" tabindex="0">
          <table class="matrix">
            <thead>
              <tr><th scope="col">&nbsp;</th><th class="tier-head" scope="col">Visibility<small>see it</small></th><th class="tier-head" scope="col">Governance<small>govern it</small></th><th class="tier-head" scope="col">Automation<small>act on it</small></th></tr>
            </thead>
            <tbody>
              <tr><th scope="row">Sending domain</th><td>$15</td><td>$30</td><td>$40</td></tr>
              <tr><th scope="row">Parked domain</th><td>$3</td><td>$3</td><td>$3</td></tr>
              <tr><th scope="row">3 sending, 40 parked</th><td>$120</td><td>$165</td><td>$195</td></tr>
            </tbody>
          </table>
        </div>
        <p class="small dim">Five parked domains included with every sending domain &mdash; the example above prices the remaining 25.</p>
        <ul class="tier-lines">
          <li><b>Visibility</b> — Daily and on-demand scans of SPF, DKIM, DMARC, BIMI and MTA-STS, plus DMARC aggregate report ingestion.</li>
          <li><b>Governance</b> — Adds guided staged rollout toward enforcement, deliverability and authentication alerting, multi-domain fleet view, and six-hourly scans.</li>
          <li><b>Automation</b> — Adds hourly scans; DNS write-back, on separate connector consent, live for Azure DNS and DNSimple only.</li>
        </ul>
        <div class="note plain">
          <h3>Why a parked domain costs $3 and not $15</h3>
          <p>Most organisations own far more domains than they send from: acquisitions, retired brands, defensive and typo registrations. Those are exactly the ones worth spoofing &mdash; no real mail flows, so nothing breaks and nobody notices.</p>
          <p class="mb0">Charging full rate for them makes the rational decision <em>protect fewer domains</em>, which is the behaviour this product exists to prevent. The classification is measured, not asserted: a domain is parked when it has produced no DMARC report volume and no DKIM signing for a full period, and it reclassifies itself the moment you start sending from it.</p>
        </div>
        <h4 style="margin-top:2rem">If you are a provider: partner rates</h4>
        <p>The list price above is a retail price, and a provider is not a retail buyer. MSP-focused DMARC platforms sell partners a wholesale rate precisely because the partner does the onboarding, the sender inventory and the support conversation, then sets their own retail. Charging a reseller list would ask them to buy at several times what a competitor charges them, which is not a price either.</p>
        <div class="table-wrap table-scroll" tabindex="0">
          <table class="matrix">
            <thead>
              <tr><th scope="col">&nbsp;</th><th class="tier-head" scope="col">Visibility<small>see it</small></th><th class="tier-head" scope="col">Governance<small>govern it</small></th><th class="tier-head" scope="col">Automation<small>act on it</small></th></tr>
            </thead>
            <tbody>
              <tr><th scope="row">Sending domain, across your whole book</th><td>$5</td><td>$10</td><td>$13</td></tr>
              <tr><th scope="row">Parked domain</th><td>$1</td><td>$1</td><td>$1</td></tr>
            </tbody>
          </table>
        </div>
        <p class="small dim">A third of list, rounded to the dollar. Minimum ten managed tenants, on a provider agreement &mdash; the same bar as pooled compliance, and for the same reason: below it the arithmetic stops describing wholesale and starts describing a discount. Five parked domains still included with every sending domain, and domains pool across your managed tenants.</p>
        <div class="note plain">
          <h3>What that comes to</h3>
          <p class="mb0">Sixty clients averaging three sending domains each is 180 domains. On Governance that is <strong>$1,800 a month</strong> against $5,400 at list. Resold at a typical managed-DMARC rate it is the highest-margin line in the stack &mdash; which is the point: you are buying the platform, not the retail price of it.</p>
        </div>
        <div class="note honest">
          <h3>What Automation writes, and where it does not</h3>
          <p class="mb0">DNS write-back is live for <strong>Azure DNS and DNSimple</strong>. Anywhere else, Automation gives you a staged rollout and the exact records to apply yourself &mdash; guidance, not automation. That is why the tier is $40 rather than the $50 the capability would be worth if it wrote everywhere. Cloudflare and Route 53 are next, and the price moves when they ship, not before.</p>
        </div>
<!--CAPS:mailtrust-->
      </div>
      <div class="product-licence tone-compliance" role="tabpanel" id="panel-compliance" aria-labelledby="tab-compliance" tabindex="0">
        <header>
          <h3>CompliancePortal</h3>
          <p class="counted">Per tenant, per month &middot; banded by frameworks in scope &middot; <strong>not released yet</strong></p>
        </header>
        <div class="table-wrap table-scroll" tabindex="0">
          <table class="matrix">
            <thead>
              <tr><th scope="col">&nbsp;</th><th class="tier-head" scope="col">1 framework<small>single regime</small></th><th class="tier-head" scope="col">3 frameworks<small>the usual mix</small></th><th class="tier-head" scope="col">Unlimited<small>every regime</small></th></tr>
            </thead>
            <tbody>
              <tr><th scope="row">Evidence</th><td>$300</td><td>$600</td><td>$900</td></tr>
              <tr><th scope="row">Attested</th><td>$450</td><td>$900</td><td>$1,350</td></tr>
            </tbody>
          </table>
        </div>
        <p class="small dim">Priced per tenant rather than per user, because a framework is the same amount of work to prove whether you have forty people or four hundred.</p>
        <ul class="tier-lines">
          <li><b>Evidence</b> — On-demand assessments run automated probes; crosswalked results populate the evidence repository, with time-boxed auditor access.</li>
          <li><b>Attested</b> — Adds attestation and sign-off with four-eyes and expiry, automated evidence capture, control ownership and remediation tasks.</li>
        </ul>
        <div class="note plain">
          <h3>Two questions, two axes</h3>
          <p>How many frameworks you need is <strong>scope</strong>. Whether you want sign-off and automatic capture is <strong>depth</strong>. Those used to share one number, which meant a company doing SOC 2 alone had to buy every framework in the catalogue to reach attestation &mdash; paying for {others} regimes it would never open, to get one capability.</p>
          <p class="mb0"><strong>Evidence</strong> is the catalogue, the crosswalk, automated probes, assessments, the evidence repository and time-boxed auditor access. <strong>Attested</strong> adds attestation and sign-off with four-eyes and expiry, control ownership, and automated evidence capture &mdash; at half again the band price, whichever band you are on.</p>
        </div>
        <h4 style="margin-top:2rem">If you are a provider: pooled framework licences</h4>
        <p>Per-tenant compliance pricing does not survive a fleet. Sixty clients on the entry band would be $18,000 a month, which is not a price, it is a decline. So for providers the two cost drivers are separated and charged for individually.</p>
        <div class="table-wrap table-scroll" tabindex="0">
          <table class="matrix">
            <thead>
              <tr><th scope="col">&nbsp;</th><th class="tier-head" scope="col">Price<small>per month</small></th></tr>
            </thead>
            <tbody>
              <tr><th scope="row">Framework licence, across your whole book</th><td>$750</td></tr>
              <tr><th scope="row">&mdash; or every framework, across your whole book</th><td>$3,000</td></tr>
              <tr><th scope="row">Per managed tenant &mdash; Evidence</th><td>$50</td></tr>
              <tr><th scope="row">Per managed tenant &mdash; Attested</th><td>$75</td></tr>
              <tr><th scope="row">Retention</th><td>36 months included &middot; 84 months +$10 / tenant</td></tr>
            </tbody>
          </table>
        </div>
        <p class="small dim">Minimum ten managed tenants, on a provider agreement. Below that the arithmetic stops describing pooling and starts describing a discount.</p>
        <div class="note plain">
          <h3>What that comes to</h3>
          <p class="mb0">Sixty tenants on one framework with sign-off: $750 + 60 &times; $75 = <strong>$5,250 a month</strong>, about $88 a client. Thirty tenants on two frameworks without sign-off: $1,500 + 30 &times; $50 = <strong>$3,000</strong>, $100 a client. Compare the first with the $27,000 the same book would cost at per-tenant rates &mdash; that gap is not a discount, it is what happens when you stop charging sixty times for one crosswalk.</p>
        </div>
        <div class="note honest">
          <h3>Two things this page will not pretend about</h3>
          <p><strong>Provider-scoped licences are not built.</strong> Entitlements in this platform resolve per tenant. A licence saying "this provider may assess SOC 2 against any client in its book" is granted at the provider and enforced at the tenant, and that shape does not exist in the catalogue today. The prices above are what you will be quoted; the gate behind them is work in progress.</p>
          <p class="mb0"><strong>Assessments do not run on a schedule yet.</strong> You raise one when you want one. What <em>is</em> continuous is the evidence underneath &mdash; SecurityPortal, ShareCare, WebScan and MailTrust scan on their own schedules, and their control-tagged findings are what an assessment reuses.</p>
        </div>
<!--CAPS:complianceportal-->
      </div>
      <div class="product-licence tone-soon" role="tabpanel" id="panel-quoted" aria-labelledby="tab-quoted" tabindex="0">
        <header>
          <h3>Dredd and PosturePortal</h3>
          <p class="counted">One quoted, one not yet priced</p>
        </header>
        <p><strong><a href="products/dredd.html">Dredd</a> is still in development, and quoted rather than listed when it lands.</strong> Its unit is monitored configuration scope, which is the metric this model understands least, and it is being set against real estates rather than guessed.</p>
        <p><strong><a href="products/postureportal.html">PosturePortal</a> carries no price at all</strong>, because it is still in development. It will not be a separate line when it arrives &mdash; it connects to nothing and reads the shared findings store &mdash; but exactly how it is packaged is unsettled, and a price against something still being built is how a price list stops being worth reading.</p>
        <p class="after">Everything else on this page is listed in full.</p>
<!--CAPS:dredd,postureportal-->
      </div>
      </div>

      <h2 style="margin-top:3rem">What you pay for</h2>
      <p><strong>There is no platform minimum.</strong> You pay for the products you hold, in the unit each one
        counts, at any size. The tenancy, auth, audit trail, findings store, reporting and scheduling that every
        product runs on are included rather than charged separately. A 30-user tenant on ShareCare Visibility
        computes $60 and pays $60.</p>

      <h2>What moves the number</h2>
      <ul>
        <li><strong>Which tier you buy.</strong> Each product tab above lists what its tiers include.</li>
        <li><strong>How big the estate is</strong>, in the unit that product counts.</li>
        <li><strong>Whether you are a provider.</strong> Users, sites and domains pool across managed tenants,
          compliance frameworks are licensed once across the book, and the per-tenant floor applies as
          greater-of rather than added on top.</li>
      </ul>

      <h2>Your own tenant, if you are a partner</h2>
      <p><strong>$50 a month, every product, every tier, on the tenant you run your own business from.</strong>
        The same estate computes somewhere between $260 and $640 at list, so this is not a discount and is not
        described as one &mdash; it is deliberately below what a tenant costs to run, which means it costs us money and
        is meant to.</p>
      <p>The reasoning is plain enough to publish: a provider who runs this on themselves every day can
        demonstrate it from a live tenant instead of a slide, and will find our mistakes before your clients
        do. That is worth more to us than the margin on one small tenant.</p>
      <ul>
        <li>Your <strong>own</strong> tenant &mdash; the domain on your provider agreement, checked against it.</li>
        <li>Requires an active provider agreement. It is a partner benefit, not a tier to sign up for.</li>
        <li>Everything included, up to 50 users. Past that it becomes ordinary pricing, because past that you
          are not a small business running a tool, you are an estate using one.</li>
        <li>Not for client tenants, and not resellable. Client tenants are priced as client tenants.</li>
      </ul>

<section class="band">
    <div class="wrap">
      <div class="section-head">
        <span class="eyebrow">How metering works</span>
        <h2>We meter the estate, never the activity</h2>
        <p>The rule we hold ourselves to: <strong>never meter the thing we want you to do more of.</strong>
          Metered scanning teaches you to scan less, discover less and get less value — and then to conclude the
          product never found anything.</p>
      </div>

      <div class="grid grid-3">
        <article class="card">
          <h3>Never per scan</h3>
          <p>Scan hourly or nightly; it costs the same. Per-scan pricing would make you widen your schedule to
             save money, which defeats the entire point of continuous assurance.</p>
        </article>
        <article class="card">
          <h3>Never per finding</h3>
          <p>"The worse your posture, the more you pay to learn about it" is the most perverse metric in this
             category. Findings are free. Fixing is free.</p>
        </article>
        <article class="card">
          <h3>Estate, not effort</h3>
          <p>Users, domains, tenants or monitored scope — depending on the product. Each one correlates with our
             cost and your value, and each is a number you already know at quote time.</p>
        </article>
      </div>

      <h3 style="margin-top:2.6rem">Enforcement: two different failures, two different behaviours</h3>
      <div class="table-wrap table-scroll" tabindex="0">
        <table>
          <thead>
            <tr><th scope="col">Situation</th><th scope="col">What happens</th><th scope="col">Why</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>Not entitled to a product or capability</td>
              <td>The capability is refused outright</td>
              <td>An entitlement is a capability gate. If you have not bought write-back, nothing writes back.</td>
            </tr>
            <tr>
              <td>Over your unit count</td>
              <td>Warning at 100%, a banner at 110%, trued up on the next invoice</td>
              <td>Units are a commercial measurement, not a kill switch. Growing past your estimate is a billing conversation.</td>
            </tr>
            <tr>
              <td>Drifting over it quietly</td>
              <td>We review overage monthly and come to you</td>
              <td>A soft cap only works if somebody reads it. The review is ours to run, so the first you hear of a mismatch is a conversation — not a surprise line on a renewal.</td>
            </tr>
            <tr>
              <td>Any commercial dispute at all</td>
              <td>Your scans keep running</td>
              <td>Hard-capping a security scan mid-incident is a security failure. We do not do it.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 style="margin-top:2.6rem">Where allowances genuinely apply</h3>
      <p class="muted">Two things carry a real external cost per use, are optional, and are bursty. They get an
        included allowance rather than being folded into the base price. Everything else — scans, remediation
        actions, findings, evidence exports — is uncapped.</p>
      <div class="table-wrap table-scroll" tabindex="0">
        <table>
          <thead><tr><th scope="col">Allowance</th><th scope="col">Included</th><th scope="col">Beyond that</th></tr></thead>
          <tbody>
            <tr><td>Deliverability tests</td><td>50 per month, per domain</td><td>Charged per test — we send and receive real mail</td></tr>
            <tr><td>DMARC aggregate report volume</td><td>An allowance per domain, sized to normal sending volume</td><td>Additional blocks — ingesting, parsing and storing reports scales with how much mail you send, not with how many domains you have</td></tr>
            <tr><td>AI remediation guidance and report narratives</td><td>Fair use</td><td>Add-on packs — there is a real per-call model cost</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>

      <h2 id="never">What never moves it</h2>
      <p><strong>How many products you take.</strong> There is no suite discount. Each product is priced on
        its own and adding one costs what that product costs — no bundle, no package, no number that only
        appears if you buy everything. What running more than one does get you is structural rather than
        promotional: one tenancy, one identity, one audit trail across the account, and findings that
        land somewhere they are already useful.</p>
      <p>How often you scan, how many findings you have, how much you remediate, or how much evidence you
        export. None of those are metered, deliberately — charging for them would teach you to look less
        often, which is the one behaviour this product exists to prevent.</p>
      <p><strong>Nor does how you pay.</strong> A year costs twelve months. Annual and monthly are a
        cash-flow decision, not a lever: there is no discount for committing and no penalty for not. If you
        would rather pay yearly because it is one invoice instead of twelve, do that — it will not change
        the number, and nobody here will pretend it should.</p>
      <p><a href="products/webscan.html">WebScan</a> takes that further: every tenant scans at no cost,
        indefinitely, one URL at a time. The licence buys what happens <em>after</em> the scan — the history,
        the schedule, the audit trail and the evidence. A scan you do not keep cannot prove anything, and the
        one you do keep is the one we charge for.</p>

      <h2 id="request">Get a number</h2>
      <p>Tell us the size of the estate. You will get a real figure back, not a discovery call.</p>
"""),

    "spoofing-report.html": dict(
        eyebrow="Free assessment",
        h1="Find out who is sending email as your domain",
        lede="A free check of SPF, DKIM, DMARC, BIMI and MTA-STS — and, once reports are flowing, a list "
             "of every source sending mail as you. No tenant access required.",
        form=dict(topic="Free spoofing / DMARC check",
                  button="Check my domain",
                  estate_label="Domain",
                  estate_hint="yourcompany.com — or several, comma separated"),
        body="""
      <h2>What you get back</h2>
      <ul>
        <li><strong>Your posture, record by record</strong> — what SPF actually authorises, whether DKIM is
          signing, what your DMARC policy does today, and whether MTA-STS and BIMI are in play.</li>
        <li><strong>Whether you can be spoofed right now</strong>, stated plainly rather than as a score.
          Most domains sit at <code>p=none</code>, which monitors and blocks nothing.</li>
        <li><strong>Every sender using your domain</strong> — from real DMARC aggregate reports once
          collection is running. Legitimate services you had forgotten about, and anyone else.</li>
        <li><strong>A staged path to enforcement</strong> that will not drop the mail your business depends
          on, which is the actual reason most DMARC projects stall at monitoring.</li>
      </ul>

      <h2>The easiest one to start with</h2>
      <p>It needs no access to your tenant. Email authentication is published in public DNS, so the first
        pass costs you nothing but the domain name. The sender inventory needs a mailbox to receive DMARC
        reports — we will tell you exactly how to point them at it.</p>

      <h2>Why now</h2>
      <p>Major mailbox providers now require DMARC for bulk senders, inbox brand indicators require
        enforcement, and business email compromise remains among the most expensive attacks in circulation.
        Reaching <code>p=reject</code> is the proven defence; doing it without breaking legitimate mail is
        the hard part, and it is what this is designed around.</p>

      <h2>If you want it continuously</h2>
      <p>That is <a href="products/mailtrust.html">MailTrust</a> — across one domain or every domain your
        clients own, writing the DNS records itself for supported providers rather than handing you a
        ticket for another team.</p>

      <h2 id="request">Check my domain</h2>
      <p>Send the domain name. A person replies, usually the same working day.</p>
"""),

    "surface-report.html": dict(
        eyebrow="Free assessment",
        h1="Find out what your attacker sees first",
        lede="A free grade of your public surface — TLS, HTTP headers, cookies, DNS, content and "
             "infrastructure — with the standard behind every failure and the fix next to it. No tenant, "
             "no consent, no onboarding.",
        form=dict(topic="Free public surface scan",
                  button="Scan my site",
                  estate_label="Site",
                  estate_hint="https://yourcompany.com — or several, comma separated"),
        body="""
      <h2>The one you can start with today</h2>
      <p>Every other assessment on this site needs an administrator to consent to something. This one does
        not. WebScan reads what any anonymous visitor can read, so there is nothing to install, nothing to
        approve, and no reason to involve anyone before you know whether there is a problem.</p>
      <p>Send a URL. You get the grade back, usually the same working day.</p>

      <h2>What you get back</h2>
      <ul>
        <li><strong>A grade, and the four counts behind it</strong> — passed, failed, not assessed and not
          applicable, kept apart so a low score can be read rather than argued with.</li>
        <li><strong>Every failure with the standard it breaks.</strong> Not "the scanner says so" but the
          RFC number, which is what turns a finding into a change request somebody approves.</li>
        <li><strong>Why it matters, then the fix</strong>, on each one — in the words you would use to
          justify the work to whoever has to schedule it.</li>
        <li><strong>The hosts you did not send us.</strong> Discovery looks for the subdomains and assets
          attached to the name you gave, which is usually where the surprise is.</li>
        <li><strong>What could not be assessed</strong>, said out loud. A check we could not run is never
          quietly counted as a pass.</li>
      </ul>

      <h2>And it stays free</h2>
      <p>This is not a sample of a paid product. <a href="products/webscan.html">WebScan</a>'s free tier
        runs the complete check set and shows every result — one URL at a time, for as long as you keep the
        tenant and with no expiry date on it. Nothing is held back from the check set. What it does not do is
        remember, and remembering is the whole of the paid product.</p>
      <p>What the free tier does not do is <em>remember</em>. Nothing is written down when the scan
        finishes — so there is no history, no trend, no schedule, no alert when a passing check regresses,
        and no evidence to hand an auditor. That is the whole of what the licence buys, and it is also why
        the free tier can be free: a free scan is a short-lived function with no storage behind it.</p>

      <div class="note honest">
        <h2>What this is not</h2>
        <p class="mb0">Not a penetration test. It grades configuration against published standards; as it
          stands it does not attempt exploitation and cannot see anything behind a login. It requests pages
          and reads DNS the way any visitor does — no fuzzing, no load, and it never writes anywhere. Active
          testing and authenticated scanning are on the
          <a href="products/webscan.html#roadmap">WebScan roadmap</a>; the free scan will stay
          unauthenticated and non-intrusive either way, so it is always safe to point at anything you
          own.</p>
      </div>

      <h2 id="request">Scan my site</h2>
      <p>Send a URL. No tenant, no consent, no call first.</p>
"""),

    "vs-cipp.html": dict(
        eyebrow="Comparison",
        h1="SeQontrol and CIPP",
        lede="Most providers we speak to already run CIPP, and should keep running it. Here is what it "
             "does that we do not, and the one thing it was never built to do.",
        body="""
      <h2>Keep it</h2>
      <p>That is the recommendation, not a courtesy. <strong>CIPP is free, open source, and running in
        production at thousands of providers</strong>, and on multi-tenant administration it does things
        this platform does not attempt: standards deployment across a book, GDAP management, identity
        lifecycle, offboarding, licence juggling, the daily operational surface of running Microsoft 365
        for other people.</p>
      <p>If your problem is "I need to administer sixty tenants without sixty browser tabs", that is
        CIPP, it costs nothing, and nothing here replaces it. A provider running both is the normal case
        rather than an awkward one.</p>

      <h2>What it was not built to do</h2>
      <p><strong>Produce evidence.</strong> CIPP tells you what a tenant looks like now and lets you change
        it. What it does not do &mdash; and does not claim to &mdash; is retain a control-tagged record that a
        control held over a period, with the exceptions named, time-boxed and attributable to whoever
        accepted them.</p>
      <p>That distinction does not matter until somebody asks. Then it is the only thing that matters: a
        cyber-insurance renewal, a client's customer sending a security questionnaire, an auditor asking
        how you know MFA was enforced in March rather than today. A management plane answers "what is it
        now". An assurance layer answers "what was it, and can you prove it".</p>

      <h2>The other two differences, stated plainly</h2>
      <p><strong>Outside-in.</strong> CIPP works through the tenant. Roughly half of what gets a client
        breached is not in the tenant at all &mdash; an expiring certificate, a spoofable domain, a forgotten
        subdomain pointing at a service somebody else now controls. Those need scanning from outside, with
        no credential, and that is a different kind of tool.</p>
      <p class="mb0"><strong>Who carries the risk.</strong> CIPP runs with your credentials in your Azure
        subscription, which is exactly right for a management plane and is also a security engineering job
        you now own: the app registrations, the secret rotation, the upgrade path, the blast radius. That
        is a reasonable trade for free. It is worth being deliberate that you have made it.</p>

      <h2>What we will not claim</h2>
      <p>We are not cheaper than free, and we will not pretend the comparison is close on that axis. We do
        not do tenant administration, and adding it would make us worse at the thing we are for.</p>
      <p class="mb0">And we will not tell you CIPP is risky, insecure or unprofessional. It is none of
        those, it is maintained by people who know this platform properly, and a provider running it is
        making a defensible engineering decision. We are asking for the budget line next to it, not
        instead of it.</p>
"""),

    "vs-m365-governance.html": dict(
        eyebrow="Comparison",
        h1="SeQontrol and the Microsoft 365 governance tools",
        lede="Syskit Point, CoreView, AvePoint and Varonis all report on Microsoft 365 permissions and "
             "sharing. Here is the honest split, including where they are the better buy.",
        body="""
      <h2>What they are better at</h2>
      <p>Said first, because it is true and because you will find it out anyway. These are mature,
        focused products with years of work in them, and on the specific job of <em>administering</em>
        a Microsoft 365 estate they go deeper than we do: workspace lifecycle and provisioning,
        access reviews as a recurring process, content-level data classification, bulk permission
        surgery on a large SharePoint estate.</p>
      <p><strong>If your problem is "we have one large tenant and need to run permissions as an
        ongoing administrative discipline", buy one of those.</strong> That is what they are for, and
        the entry price on a per-seat basis is genuinely lower than ours. We would rather say that
        here than have you discover it after a trial.</p>

      <h2>What we are better at</h2>
      <p><strong>Producing evidence rather than a report.</strong> A permission report tells you what
        is true today. What an auditor, an insurer or a customer questionnaire wants is that a control
        held over a period, at control granularity, with the exceptions named and time-boxed. Our
        findings are written to a shared store already tagged to the controls they prove, so a
        ShareCare scan becomes CompliancePortal evidence with no export and no second integration.</p>
      <p><strong>Breadth on one connection.</strong> Sharing is one surface. The same estate also has
        Conditional Access coverage, application consents, email authentication and a public web
        surface — and those live in four different tools, or in one platform with one onboarding, one
        audit trail and one bill.</p>
      <p><strong>Small tenants, and a lot of them.</strong> This is the sharpest split. The
        governance specialists start at a hundred-seat minimum or an enterprise contract; the average
        tenant a provider manages is nowhere near that. If your book is sixty clients of twenty-odd
        users, most of this category cannot sell to you at all, and the ones that can are priced for a
        single large estate rather than a fleet of small ones.</p>

      <h2>On price, plainly</h2>
      <p>Per seat, on the permissions job alone, the specialists are cheaper. We are not going to
        pretend the arithmetic says otherwise, and if permissions reporting on one large tenant is the
        entire requirement, that is the honest recommendation.</p>
      <p>The comparison changes when the requirement is three or four of those surfaces plus evidence
        that survives an audit, or when it is a fleet rather than a tenant. Then you are comparing one
        platform against three products and an integration project, and the per-seat line stops being
        the number that decides it. <a href="pricing.html">The figures are published in full</a>;
        work it out against your own estate rather than ours.</p>

      <h2>What we will not claim</h2>
      <p>We do not do content classification, and we do not read your documents — SeQontrol records
        that a file is shared with an external address, never what is in it. If your requirement is
        finding regulated data inside files, that is a data-security product and we are not one.</p>
      <p class="mb0">We do not do workspace provisioning, lifecycle or recurring access-review
        workflow. Those are administration, we are assurance, and a product that claimed both would be
        worse at each.</p>
"""),

    "vs-grc-platforms.html": dict(
        eyebrow="Comparison",
        h1="SeQontrol and the GRC platforms",
        lede="Vanta, Drata, Secureframe and their peers do something we deliberately do not. Here is "
             "the honest split, including the cases where you should pick them.",
        body="""
      <h2>What they are better at</h2>
      <p>Said first, because it is true. Automated GRC platforms have spent years on the parts of
        compliance that are workflow: policy management, employee onboarding and training records,
        vendor reviews, questionnaire handling, and — importantly — established relationships with
        auditors who already know their evidence format.</p>
      <p><strong>If your problem is "we need to run a SOC 2 programme and we have no process yet",
        buy one of those.</strong> We are not a substitute for it and pretending otherwise would waste
        your money.</p>

      <h2>What we are better at</h2>
      <p>Proving the technical controls, at control granularity, on a Microsoft 365 estate.</p>
      <p>A GRC platform generally establishes that a control exists by asking you, or by a shallow
        integration check. SeQontrol establishes it by scanning: external sharing containment,
        Conditional Access coverage, MFA enforcement including the exclusions, application permissions
        that are actually unused, email authentication posture. The finding and the evidence are the
        same record, and you can re-run it.</p>
      <p>The second difference is fleet economics. If you manage many client tenants, per-tenant GRC
        licensing prices the work out of existence. This platform was built provider-first.</p>

      <h2>They are often complementary</h2>
      <p>The common shape: a GRC platform runs the programme, and SeQontrol feeds it the technical
        control evidence it cannot produce itself. If that is your situation, say so on the first call
        and we will scope for it rather than argue for replacement.</p>

      <div class="note scope">
        <h2>What we will not claim</h2>
        <p class="mb0">We do not give you an audit opinion, an auditor relationship, or the process
          half of a compliance programme. <a href="limits.html">The full list of what we do not do</a>
          is published, and this is on it.</p>
      </div>
"""),

    "vs-secure-score.html": dict(
        eyebrow="Comparison",
        h1="SeQontrol and Microsoft's native tooling",
        lede="Secure Score, Purview and SharePoint Advanced Management already ship with your "
             "licence. Here is what they cover, and the specific gaps that made this worth building.",
        body="""
      <h2>When native is enough</h2>
      <p>One tenant, one administrator, no external reporting obligation and no Copilot rollout
        pending: Secure Score plus the native reports will tell you most of what you need, and they
        cost nothing extra. <strong>Start there.</strong> A tool you already own and will actually
        check beats one you buy and ignore.</p>

      <h2>The four gaps</h2>
      <ul>
        <li><strong>One number, not a control.</strong> Secure Score gives a figure per tenant. It
          does not tell an auditor which control held, or produce evidence that it held over a
          period.</li>
        <li><strong>Per workload, per tenant.</strong> Sharing sits in one report, identity in
          another, mail flow in a third — and none of them span the clients a provider manages.</li>
        <li><strong>No outside-in view.</strong> Nothing native scans your public web and domain
          surface, which is where a good deal of exposure actually lives — that is
          <a href="products/webscan.html">WebScan</a>, and running it costs nothing.</li>
        <li><strong>Reporting, not remediation, and no memory.</strong> Native reports show a state.
          They do not stage a fix with a grace window and an undo, and they do not keep a
          tamper-evident record of what changed and who approved it.</li>
      </ul>

      <h2>The honest overlap</h2>
      <p>Microsoft improves this surface constantly, and some of what SeQontrol does today will be
        native eventually. The parts we expect to keep mattering are the ones native tooling is
        structurally unlikely to build: cross-tenant fleet economics, and turning a security finding
        into portable compliance evidence.</p>
      <p>We license per estate, so if Microsoft ships something that replaces a piece of this, you
        are free to stop paying for that piece.</p>
"""),

    "exposure-report.html": dict(
        eyebrow="Free assessment",
        h1="See what Copilot can reach in your tenant",
        form=dict(topic="Free exposure report",
                  button="Request my exposure report",
                  estate_label="Tenant size",
                  estate_hint="e.g. 150 users, ~4 TB in SharePoint"),
        lede="A scoped scan, a scored list of what is actually exposed, and a remediation order. "
             "Free, read-only, and useful whether or not you buy anything afterwards.",
        body="""
      <h2>What you get back</h2>
      <ul>
        <li><strong>Every external share, listed and scored</strong> — anonymous links, links that
          allow editing, guests who have not signed in for months, and the resources each can reach.</li>
        <li><strong>The internal over-exposure</strong> — organisation-wide links and company-wide
          groups such as "Everyone except external users". These are the patterns that make Copilot
          surface far more than anyone intended, and they are invisible in native reports.</li>
        <li><strong>Risky grants beyond files</strong> — over-permissioned OAuth applications, and
          mail forwarding to domains nobody in your organisation owns.</li>
        <li><strong>A remediation order</strong> — not a CSV of everything, but what to revoke first,
          ranked by sensitivity and blast radius, with the ones that are safe to automate marked.</li>
      </ul>

      <h2>What it costs, and what it does not</h2>
      <p>Nothing. No card, no trial that converts into a subscription, no contract. If the report
        tells you your estate is in good shape, that is a perfectly good outcome and we will say so.</p>
      <p><strong>The catch, stated plainly:</strong> we do this because a scored list of your own
        exposure is a better argument for the product than any page on this site. If it is not
        compelling, you will not buy, and that is fair.</p>

      <h2>What it touches</h2>
      <ul>
        <li><strong>Read-only, app-only.</strong> Application permissions through Microsoft Graph — not
          a user's session, no agent to install, no disruption to anybody working.</li>
        <li><strong>Metadata, not content.</strong> We read who can reach what. We do not read your
          documents or your mail.</li>
        <li><strong>Nothing is changed.</strong> Remediation needs a separate consent that this
          assessment does not ask for and does not use.</li>
        <li><strong>You can revoke it the moment the report lands</strong>, and the findings you have
          been given remain yours.</li>
      </ul>

      <h2>How it runs</h2>
      <ol>
        <li>You tell us the tenant and roughly how big it is.</li>
        <li>We agree the scope and a date before anything connects.</li>
        <li>An administrator grants read-only consent to the Entra application for the product being
          assessed — scoped to that product, and nothing else.</li>
        <li>The crawl runs. Large estates are swept in stages so nothing is throttled.</li>
        <li>You get the report, and a walkthrough of it if you want one.</li>
      </ol>

      <h2>Managing many tenants?</h2>
      <p>The provider version ranks your worst clients against each other, so the conversation you
        have with them is specific rather than general.
        <a href="for-msps.html">More on the provider model</a>.</p>

      <h2 id="request">Ask for the report</h2>
      <p>Tell us the tenant size and we will come back with a scope and a date. A person replies,
        usually the same working day.</p>
"""),

    "limits.html": dict(
        eyebrow="Straight answers",
        h1="What SeQontrol does not do",
        lede="Every limit worth knowing, in one place — including the ones a sales call would "
             "normally leave until month two.",
        body="""
      <p>Security software is bought on trust, and trust does not survive a discovered exaggeration.
        So here is the unflattering version, in one place, rather than scattered through the pages
        that are trying to persuade you.</p>

<div class="note honest">
        <h2>Every product asks for its own consent</h2>
        <p>There is no single grant that switches the platform on. Each product that reads your tenant has
          its own Entra application and its own admin consent, scoped to that product's permissions &mdash; so
          adding a product means going back to an administrator, not flipping a switch. The upside is real:
          nothing inherits permissions it has no use for. But if you were told this was a one-consent
          platform, it is not, and you would have found out during onboarding.</p>
        <p>Two products sit outside that shape. <a href="products/webscan.html">WebScan</a> asks for nothing
          at all &mdash; no tenant, no consent, no agent &mdash; because it works from outside.
          <a href="products/postureportal.html">PosturePortal</a> connects to nothing of its own; it reads
          what the other products already wrote.</p>
        <p class="mb0">Revoking a product's admin consent revokes exactly one product's Graph access. It does
          not touch the grants sitting beside it: the Exchange management role, the Azure reader assignment,
          the Power Platform service principal registration and each DNS provider's OAuth authorisation are
          separate authorities and have to be removed separately. Write-back is a separate opt-in again, and
          Exchange admin, Power Platform, Azure and DNS each need their own one-time setup &mdash; and for
          DNS, in-product write-back is live for Azure DNS and DNSimple only, with every other provider
          getting guided manual steps. The <a href="platform.html">platform page lists every step</a>.</p>
      </div>

<div class="note honest">
        <h2>Some planes detect but do not (yet?) fix</h2>
        <p>Where one of our products remediates a plane app-only, it does. Exchange forwarding, SharePoint
          site roles, Power Platform and delegated-admin relationships are detected and reported rather than
          written back.</p>
        <p class="mb0">That is our gap, not Microsoft's, and this page used to say otherwise. Each of those
          planes has a documented application-only write path &mdash; certificate-based Exchange Online
          PowerShell, Sites.FullControl.All on the SharePoint admin APIs, a Power Platform service principal,
          DelegatedAdminRelationship.ReadWrite.All on Graph. In some cases we have not built the connector;
          in others we are unwilling to ask you for permission that broad in order to ship it. Either way the
          limit is ours to lift. When a product cannot safely act, it gives the precise reason rather than
          guessing or quietly failing.</p>
      </div>

<div class="note honest">
        <h2>Half the catalogue is not on sale yet</h2>
        <p>Four of the eight products run today: <a href="products/sharecare.html">ShareCare</a>,
          <a href="products/securityportal.html">SecurityPortal</a>,
          <a href="products/webscan.html">WebScan</a> and <a href="products/mailtrust.html">MailTrust</a>.
          <a href="products/conditionalaccessportal.html">ConditionalAccessPortal</a> and
          <a href="products/complianceportal.html">CompliancePortal</a> are built and running but not
          released. <a href="products/postureportal.html">PosturePortal</a> and
          <a href="products/dredd.html">Dredd</a> are still being written.</p>
        <p class="mb0">Two of them have no price. Dredd is quoted rather than listed, because its licence
          unit is still being set; PosturePortal carries no number at all. And nothing unreleased has a date
          &mdash; ask, and you get an honest read on where it stands rather than a quarter.</p>
      </div>

<div class="note honest">
        <h2>Subdomain discovery is not a complete estate</h2>
        <p>WebScan finds hostnames two ways, and only one of them is immediate. The names carried on the
          certificate your site serves at scan time are read straight away &mdash; though a wildcard
          certificate names a shape rather than hosts and yields nothing to enumerate, and a shared CDN or
          load-balancer certificate can carry names that are not yours.</p>
        <p>The rest come from public certificate transparency logs. We tail those logs from the day we add
          them rather than replaying their history, so we hold nothing logged before we started watching.
          That is our design and not a property of CT &mdash; the logs are append-only and can be read from
          their first entry &mdash; and it is a limit we could lift.</p>
        <p>Certificates reach the logs within hours of issuance, so the delay is not the log's, it is ours. A
          name we never saw reaches us at its next renewal: about ninety days on a Let's Encrypt default, and
          potentially the better part of a year on a longer-lived commercial certificate.</p>
        <p>We also do not follow every log that exists, and the set we do follow changes as the public logs
          themselves do &mdash; they are retired and replaced on a schedule the whole industry runs on. More
          to the point: <strong>a log starts counting for us on the day we add it.</strong> Adding one widens
          what we will see from that day forward; we do not go back and replay what it recorded before.</p>
        <p class="mb0">Which means an empty or short list is a statement about our coverage, not about your
          estate, and nothing in the product will present it as one. Read it as &ldquo;what we have seen so
          far&rdquo; and it is useful. Read it as &ldquo;what exists&rdquo; and it is wrong.</p>
      </div>

<div class="note honest">
        <h2>WebScan is not a penetration test</h2>
        <p class="mb0">It grades configuration against published standards, from outside, as any visitor
          would. It attempts no exploitation, runs no fuzzing, and sees nothing behind a login. Active
          testing and authenticated scanning are on the roadmap; until they ship, a clean grade says the
          outside is configured well, not that the application is safe.</p>
      </div>

<div class="note honest">
        <h2>We are Microsoft-first</h2>
        <p class="mb0">Microsoft 365 and Entra are the deep estate. Box sharing ships today with app-only
          revoke; Slack Connect is detect-only until the admin APIs exist to act on. Google Cloud and AWS are
          read-only connectors in CompliancePortal, which is built and running but not released yet.
          Everything else is roadmap, and we will not pretend otherwise on a sales call.</p>
      </div>

<div class="note honest">
        <h2>Readiness is not an audit opinion</h2>
        <p class="mb0">CompliancePortal &mdash; built and running, not released yet &mdash; turns the
          continuous evidence the scanning products already produce into readiness for the technical controls
          on the platforms we support. The evidence underneath is continuous; the assessments themselves run
          when you raise one, not on a schedule. Your auditor still signs the opinion, and the controls that
          live in people and process are still yours to run.</p>
      </div>

<div class="note honest">
        <h2>We have not written down our own assurance yet</h2>
        <p class="mb0">Product data lives in <a href="privacy.html">Microsoft Azure, West Europe</a>, and that
          much is published. What is not: a subprocessor list, retention defaults per data class, and whatever
          certifications we do or do not hold. If your procurement needs those before you can buy, ask early
          &mdash; the honest answer today is that they are not written down, and we would rather say so here
          than have you discover it in a security questionnaire.</p>
      </div>

      <h2>Why this page exists</h2>
      <p>Most vendors bury this and let you find out in month two. We would rather you knew before
        the first call, because every one of these limits is something you would eventually hit —
        and finding out late costs you more than it costs us.</p>
      <p>If one of them is a dealbreaker, tell us and we will say so plainly rather than sell around
        it. <a href="mailto:support@seqontrol.com?cc=jeff%2Bseqontrol%40jeffops.com&amp;subject=Feature%20request&amp;body=Hello%2C%0D%0A%0D%0AI%20have%20a%20question%20about%20something%20%3CProductName%3E%20doesn%27t%20do%20that%27s%20a%20deal%20breaker%20for%20us%2C%20because%20we%20need%20that%20functionality.">Ask the awkward question</a>.</p>
"""),

    "about.html": dict(
        eyebrow="About",
        h1="Why this exists",
        lede="SeQontrol is built by {operator} — a small team, working on the Microsoft 365 estate, "
             "shipping in public.",
        body="""
      <h2>The problem that started it</h2>
      <p>Every Microsoft 365 tenant accumulates access. A link shared with a supplier in 2019, a group
        that quietly means "everyone", an app somebody consented to once. None of it mattered much
        while it stayed obscure. Copilot ended that: anything a user can technically reach is now
        something an assistant will happily summarise and cite.</p>
      <p>The tooling that existed answered the wrong shape of question. Native reports are per-workload
        and per-tenant. GRC platforms take your word for the technical controls and spend their effort
        on questionnaires. Nothing joined "what is exposed" to "prove it stayed fixed" — and nothing at
        all was built for somebody managing forty tenants rather than one.</p>

      <h2>The bet</h2>
      <p>That the platform matters more than any single scanner. One findings store, one audit trail, one
        console — so a security finding becomes compliance evidence without a second integration, and so the
        tenth tenant costs no more thought than the first. Each product still asks for its own consent; what
        the platform saves you is everything after that.</p>
      <p>And that security sits above compliance. A waived control turns a report green without
        changing anything real; we would rather show you the finding that is still there.
        <a href="index.html#principle">The full argument is on the home page.</a></p>

      <h2>Who</h2>
      <p>{operator} is Jeff Wouters — writing, speaking and consulting on the Microsoft platform at
        <a href="https://jeffops.com">jeffops.com</a>, and building SeQontrol. If you email us, the
        reply comes from a person who worked on the thing you are asking about.</p>

      <h2>What we will not do</h2>
      <ul>
        <li><strong>Claim customers we do not have.</strong> There are no logos on this site because
          there is nothing to show yet, and inventing them would be a strange way to start a
          relationship built on trusting us with tenant access.</li>
        <li><strong>Fabricate a pass.</strong> A control we cannot assess is reported as "not
          assessed", never as green.</li>
        <li><strong>Oversell the roadmap.</strong> What is shipped is labelled shipped, and what is
          not is labelled coming soon, on the page where you would otherwise assume otherwise.</li>
      </ul>

      <!-- TO ADD: a photo, and a line of background if you want one. A named,
           visible founder is the strongest trust signal available before there
           are customers to reference. -->

      <h2>Talk to us</h2>
      <p>Ask a hard question — <a href="contact.html">the contact page</a> or
        <a href="mailto:{contact}">{contact}</a>. If SeQontrol is not a fit for you, we would rather
        say so early than sell you a year of it.</p>
"""),

    "privacy.html": dict(
        eyebrow="Privacy",
        h1="What we collect, and why",
        lede="Short, because there is not much of it. This covers the website; the second half "
             "covers what the product reads once a tenant is connected.",
        body="""
      <h2>Who is responsible</h2>
      <p>SeQontrol is operated by <strong>{entity}</strong>, {address}, registered with the Dutch
        Chamber of Commerce (KvK) under number <strong>{kvk}</strong>. For anything on this page,
        including a request to see or delete what we hold, write to
        <a href="mailto:{contact}">{contact}</a> and a person will answer.</p>
      <p>Where this policy says "we", it means that entity and nobody else. No data described here
        is sold, brokered, or handed to an advertising network.</p>

      <h2>This website</h2>
      <p>The site is static. It sets no cookies, runs no advertising or profiling scripts, and makes
        no third-party requests — no fonts, no CDN, no embedded video. Nothing about you is collected
        by visiting it.</p>
      <p>If you send the contact form, we receive what you typed: your name, email address, and
        whatever else you chose to add. We use it to reply to you and to keep track of the
        conversation. We do not sell it, share it for marketing, or add you to a list you did not ask
        for.</p>

      <h2>What the product reads</h2>
      <p>Once you connect a Microsoft 365 tenant, SeQontrol reads configuration and metadata through
        app-only Microsoft Graph permissions in order to produce findings. Concretely, that means
        things like sharing links, permission assignments, group memberships, application consents,
        Conditional Access policies and DNS records.</p>
      <p><strong>It is metadata about access, not the contents of your files.</strong> SeQontrol
        records that a document is shared with an external address; it does not read the document.</p>
      <p>Scanning is read-only. Anything that writes back to your tenant — revoking a permission,
        publishing a DNS record, restoring an approved configuration — requires a separate, explicit
        consent that is distinct from the read grant, and can be withdrawn without losing the
        findings and evidence you already hold.</p>

      <h2>Where it is kept</h2>
      <p>Everything SeQontrol stores about your tenant — findings, evidence, scan history and the
        audit trail — lives in <strong>Microsoft Azure, West Europe region</strong>, which is in the
        Netherlands. Same jurisdiction as the company that operates it. It is not replicated to a
        region outside the EU.</p>
      <p class="mb0">Two things that follow, and are worth being explicit about. Microsoft is
        therefore a processor for the hosting itself. And the data in your own Microsoft 365 tenant
        never moves — SeQontrol reads it where it already is; what lives in West Europe is the
        findings and evidence produced from that reading, not a copy of your estate.</p>

      <h2>How long it is kept</h2>
      <p>Findings and evidence are retained for the period your licence sets, because the value of
        compliance evidence is that it covers a period. The audit trail is hash-chained and
        append-only by design: entries are not edited or deleted, which is the property that makes it
        worth having.</p>
      <p>Contact-form correspondence is kept for as long as the conversation is useful, and deleted
        on request.</p>

      <h2>Your rights</h2>
      <p>You can ask what we hold about you, ask for it to be corrected, ask for it to be deleted, or
        object to it being processed. Email <a href="mailto:{contact}">{contact}</a> and you will get
        a reply from a person.</p>
      <p>Where SeQontrol processes data from your tenant, you are the controller and we act as
        processor on your instructions. A data processing agreement is available on request.</p>

      <h2>Changes</h2>
      <p>If this notice changes materially, the change is visible in the site's public commit
        history — the whole site is a public repository, which is a stronger guarantee than a
        "last updated" date we control.</p>
"""),

    "terms.html": dict(
        eyebrow="Terms",
        h1="Terms, in language you can actually check",
        lede="These cover the website. A signed agreement governs the service itself; ask and we "
             "will send it before you commit to anything.",
        body="""
      <h2>The website</h2>
      <p>You may read, quote and link to anything here. The words, the brand and the artwork belong
        to {operator}. The site's source is public and its licence sits in the repository.</p>
      <p>Everything on this site describing the product is written to be accurate at the time of
        writing, including the parts that say what the product does <em>not</em> do. Where something
        is not yet available it is labelled "coming soon", and where a capability is limited the
        limit is stated. If you find something on this site that is wrong, tell us and we will fix
        it — that is a commitment we would rather be held to than a disclaimer.</p>

      <h2>The service</h2>
      <p>Use of the platform is governed by a written agreement, not by this page. That agreement
        covers availability, support, liability, processing terms and termination. We will send it
        before you are asked to commit, not after.</p>
      <p>Two things worth stating plainly here, because they shape everything else:</p>
      <ul>
        <li><strong>SeQontrol provides readiness and evidence, not an audit opinion.</strong> Your
          auditor signs the opinion. Nothing produced here is a certification.</li>
        <li><strong>Remediation writes to your tenant only where you have separately consented.</strong>
          It restores an approved state or removes an identified exposure; it does not run arbitrary
          automation.</li>
      </ul>

      <h2>No warranty of a secure estate</h2>
      <p>SeQontrol reports what it can observe through the connections you grant it. It does not
        claim to find everything, and a clean report is not a guarantee that you are not exposed —
        a control that cannot be assessed is reported as "not assessed" rather than as a pass,
        precisely so that the gap is visible to you.</p>

      <h2>Who these terms are with</h2>
      <p>The other party to these terms is <strong>{entity}</strong>, registered with the Dutch
        Chamber of Commerce (KvK) under number <strong>{kvk}</strong>:</p>
      <p class="mb0">{address_html}</p>

      <h2>Governing law</h2>
      <p>Dutch law applies, and the courts of the Netherlands have jurisdiction. Stated because a
        contract that is silent on it leaves both sides guessing at the moment they can least afford
        to — not because anybody expects to use it.</p>

      <h2>Contact</h2>
      <p>Questions about these terms: <a href="mailto:{contact}">{contact}</a>.</p>
"""),

    "security.html": dict(
        eyebrow="Security",
        h1="What we do with the access you give us",
        lede="A new vendor asking to read your entire identity estate should expect hard questions. "
             "These are the answers, before you ask.",
        body="""
      <h2>The access we ask for</h2>
      <ul>
        <li><strong>App-only, and read-first.</strong> Scanning uses application permissions, not a
          user's session. There is no agent to install and no user-facing disruption.</li>
        <li><strong>Consent is per product, scoped and documented.</strong> Each product has its own
          Entra application, declaring only the permissions that product needs. Enabling a further product
          means a further admin consent — so nothing inherits permissions it has no use for, and revoking
          one product revokes exactly one.</li>
        <li><strong>Write access is separate.</strong> Remediation requires its own explicit consent
          on top of the read grant. Withdrawing it stops all write paths and leaves your findings and
          evidence intact.</li>
        <li><strong>Metadata, not content.</strong> We read who can reach what. We do not read your
          documents or your mail.</li>
      </ul>

      <h2>How the platform is built</h2>
      <ul>
        <li><strong>Tenant isolation.</strong> Each tenant owns its own connectors, findings,
          governance records and history. There is no shared tenant data. Templates may seed a
          tenant, but instantiated records belong to that tenant.</li>
        <li><strong>Tamper-evident audit.</strong> The audit trail is hash-chained, so a record that
          was altered after the fact can be shown to have been altered. Support access through
          impersonation is recorded in it like anything else.</li>
        <li><strong>An approval gate for providers.</strong> Where a managed service provider
          operates inside your tenant, you can require that their actions are approved first.</li>
        <li><strong>Nothing is overwritten.</strong> Controls, desired states, findings, remediations,
          approvals and waivers preserve their history. Governance decisions overlay the facts; they
          never rewrite them.</li>
        <li><strong>No fabricated passes.</strong> A control that cannot be assessed — no exported
          logs, an unsupported plane, a missing permission — is reported as "not assessed", with the
          reason. It is never scored green by default.</li>
      </ul>

      <h2>This website</h2>
      <p>Static files, served over HTTPS with HSTS via the host. No cookies, no third-party scripts,
        no external requests of any kind. The source is public, so any claim on this page can be
        checked against the code that makes it.</p>

      <h2>Reporting a vulnerability</h2>
      <p>Email <a href="mailto:{contact}">{contact}</a>. Include enough detail to reproduce the
        issue. We will acknowledge within two working days and keep you informed until it is
        resolved. We will not take legal action against anyone acting in good faith to find and
        report a problem, and we are happy to credit you unless you would rather we did not.</p>
      <p>Machine-readable contact details are published at
        <a href=".well-known/security.txt">/.well-known/security.txt</a>.</p>

      <!-- TO FILL IN before this page carries real weight:
             · hosting region(s) for product data
             · subprocessor list (hosting, mail, error reporting)
             · retention defaults per data class
             · certifications held, if any (say none rather than implying)  -->
"""),
}




def build(name: str, spec: dict) -> None:
    head_open, after_head, footer = chrome()

    # One dict, applied to every prose field rather than to `body` alone. It used to be inlined on
    # the body call only, while `lede` was interpolated raw further down - so about.html shipped the
    # literal text "SeQontrol is built by {operator}" to every visitor who opened it. A placeholder
    # is only substituted on the fields somebody remembered to substitute, which is not a property
    # worth relying on; both prose fields now go through the same substitution.
    fields = dict(contact=CONTACT, operator=OPERATOR, entity=ENTITY,
                  kvk=KVK, address=ADDRESS_INLINE,
                  address_html='<br>'.join(ADDRESS_LINES),
                  others=OTHER_FRAMEWORKS)
    body = spec["body"].format(**fields)
    spec = {**spec, "lede": spec["lede"].format(**fields)} if "lede" in spec else spec

    # An offer page carries its own form, so the ask sits where the intent is
    # rather than one click away on the contact page.
    if spec.get("form"):
        body += FORM.format(
            contact=CONTACT,
            topic=spec["form"]["topic"],
            button=spec["form"]["button"],
            estate_label=spec["form"]["estate_label"],
            estate_hint=spec["form"]["estate_hint"],
        )

    html = (
        head_open
        # Title and description come from build_seo.META, which is the only copy that survives:
        # build_seo.apply() rewrites both on every run regardless of what is emitted here. This file
        # used to carry its own title=/desc= for each page, and seven of them had silently drifted
        # out of agreement - editing one was a no-op, and one discarded description ran to 165
        # characters, over verify.py's own limit, escaping the gate only because it never shipped.
        + f"<title>{seo_title(name)}</title>\n"
        + f'<meta name="description" content="{seo_desc(name)}">\n'
        + '<link rel="stylesheet" href="css/styles.css">\n'
        + after_head
        + "<main id=\"main\">\n\n"
        + '  <section class="hero">\n    <div class="wrap wrap-narrow">\n'
        + f'      <span class="eyebrow">{spec["eyebrow"]}</span>\n'
        + f'      <h1>{spec["h1"]}</h1>\n'
        + f'      <p class="lede">{spec["lede"]}</p>\n'
        + "    </div>\n  </section>\n\n"
        + '  <section>\n    <div class="wrap wrap-narrow">\n'
        + body
        + "    </div>\n  </section>\n\n</main>\n\n"
        + footer
        + '<script src="js/site.js"></script>\n'
        + (FORM_SCRIPT.replace("{contact}", CONTACT) if spec.get("form") else "")
        + '</body>\n</html>\n'
    )
    path = os.path.join(ROOT, name)
    io.open(path, "w", encoding="utf-8").write(html)
    print("wrote", name)


SECURITY_TXT = f"""Contact: mailto:{CONTACT}
Expires: 2027-08-14T00:00:00.000Z
Preferred-Languages: en, nl
Canonical: https://seqontrol.com/.well-known/security.txt
Policy: https://seqontrol.com/security.html
"""

if __name__ == "__main__":
    for name, spec in PAGES.items():
        build(name, spec)
    d = os.path.join(ROOT, ".well-known")
    os.makedirs(d, exist_ok=True)
    io.open(os.path.join(d, "security.txt"), "w", encoding="utf-8").write(SECURITY_TXT)
    print("wrote .well-known/security.txt")
