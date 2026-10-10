#!/usr/bin/env python3
"""The published list prices, as data, for the pages that quote them OUTSIDE pricing.html.

WHY THIS EXISTS. Until 2026-10-10 every figure lived on pricing.html and nowhere else, and verify.py
refused a price on any other page. The redesign puts a price next to each product - in the table on
products/index.html and in a tier block on the product's own page - because that is where a buyer
reading about a product asks what it costs.

A second page quoting a price is a second place for it to go stale, which is exactly what the old
rule prevented. So the product pages do not carry figures someone typed: build_prices.py renders
them from this module, and verify.py's check_prices fails the build if any figure here is not also
on pricing.html. Change a price in build_legal.py (pricing.html) and here in the same commit, or CI
stops you.

pricing.html itself is NOT generated from this module yet - its tables, worked bills and provider
rates are prose-heavy HTML inside build_legal.py. Moving them onto this data is the natural next
step; until then the check above is what keeps the two honest.

Figures are strings exactly as pricing.html prints them ("$6.50", "$1,350"), so the cross-check is a
plain substring test with no number formatting to disagree about.
"""
from __future__ import annotations

# key -> product page file (products/<file>), used to find the marker blocks.
PRODUCT_PAGES = {
    "sharecare":  "sharecare.html",
    "security":   "securityportal.html",
    "condaccess": "conditionalaccessportal.html",
    "webscan":    "webscan.html",
    "mailtrust":  "mailtrust.html",
    "compliance": "complianceportal.html",
    "dredd":      "dredd.html",
    "posture":    "postureportal.html",
}

# The one-cell summary used in the products/index.html table.
#   unit   - what is counted
#   rows   - (label, figure) pairs, figures exactly as on pricing.html
#   note   - one short line under the figures, or ""
SUMMARY = {
    "sharecare": {
        "unit": "per Microsoft 365 user / month",
        "rows": [("Visibility", "$2"), ("Governance", "$4"), ("Automation", "$6.50")],
        "note": "No seat minimum, no platform floor. Volume bands from 100 users.",
    },
    "security": {
        "unit": "per user / month &middot; one tier",
        "rows": [("With any ShareCare tier", "$1.50"), ("Standalone", "$3.50")],
        "note": "$50 monthly minimum per tenant, greater-of.",
    },
    "webscan": {
        "unit": "per monitored site / month",
        "rows": [("Free, on every tenant", "$0"), ("Pro", "$20")],
        "note": "Pro keeps results and history, schedules scans and alerts.",
    },
    "mailtrust": {
        "unit": "per sending domain / month",
        "rows": [("Visibility", "$15"), ("Governance", "$30"), ("Automation", "$40")],
        "note": "Five parked domains included per sending domain; more at $3.",
    },
    "condaccess": {
        "unit": "per user / month &middot; on release",
        "rows": [("Visibility", "$0.60"), ("Governance", "$1.00"), ("Automation", "$1.50")],
        "note": "$50 monthly minimum per tenant.",
    },
    "compliance": {
        "unit": "per tenant / month &middot; on release",
        "rows": [("1 framework", "$300"), ("3 frameworks", "$600"), ("Unlimited", "$900")],
        "note": "Evidence band. Attested, with sign-off, from $450.",
    },
    "dredd": {
        "unit": "in development",
        "rows": [],
        "note": "Quoted, not listed, once released.",
    },
    "posture": {
        "unit": "in development",
        "rows": [],
        "note": "Not priced while it is still being built.",
    },
}

# The tier cards on a product's own page. Only products whose page carries a
# <!--PRICE-TIERS:key--> block need an entry; build_prices.py says so if one is missing.
#   tiers  - (step label, tier name, figure, unit suffix, [what it adds])
#   volume - (lead-in, [(percentage, threshold)]) or None
#   foot   - one line under the cards
TIERS = {
    "sharecare": {
        "tiers": [
            ("Step 1 &middot; See it", "Visibility", "$2", "/user/mo", [
                "Read-only inventory of sharing and permissions",
                "Risk scoring and findings history",
                "Fleet view",
                "Daily scheduled scans",
            ]),
            ("Step 2 &middot; Govern it", "Governance", "$4", "/user/mo", [
                "Everything in Visibility",
                "Oversharing and advanced detections",
                "Policies, access reviews and approvals",
                "Waivers and evidence packs",
                "Six-hourly scans",
            ]),
            ("Step 3 &middot; Act on it", "Automation", "$6.50", "/user/mo", [
                "Everything in Governance",
                "Hourly scans",
                "OneDrive permission and sharing-link write-back, with undo",
                "Requires a separate connector remediation consent",
            ]),
        ],
        "volume": ("Volume discount on the whole bill",
                   [("10%", "above 100 users"), ("20%", "above 500"), ("30%", "above 2,000")]),
        "foot": "",
    },
}

