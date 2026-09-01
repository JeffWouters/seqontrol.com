#!/usr/bin/env bash
#
# Check that the deployed site actually serves what the build produced.
#
# This exists because of a real failure. upload-pages-artifact excludes hidden files unless told
# otherwise, so /.well-known/security.txt and /.nojekyll were 404 in production from launch while
# the build, verify.py and the deploy all reported success. Nothing in CI looked at the deployed
# site, so the only thing standing between that and forever was somebody checking by hand.
#
# verify.py cannot catch this class. It reads the source tree — the files were present and valid
# there the whole time. Everything below is checked over HTTP against the live origin, after the
# deploy, which is the only place a bug between "committed" and "served" is visible.
#
# Usage:  tools/smoke_test.sh [base-url]     (default https://seqontrol.com)

set -uo pipefail

SITE="${1:-https://seqontrol.com}"
ATTEMPTS="${SMOKE_ATTEMPTS:-10}"
PAUSE="${SMOKE_PAUSE:-15}"

failures=0
workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

# A Pages deploy is not instant at the edge, so a single miss proves nothing. Retry before believing
# a failure, and fail hard once the retries are spent.
fetch() {
    local path="$1" dest="$2" attempt=1
    while :; do
        if curl -fsSL --max-time 20 "$SITE$path" -o "$dest" 2>/dev/null; then
            return 0
        fi
        [ "$attempt" -ge "$ATTEMPTS" ] && return 1
        attempt=$((attempt + 1))
        sleep "$PAUSE"
    done
}

# A 200 is not enough. Pages answers a missing path with a styled 404 page, and a redirect stub is
# also a 200 with the wrong body, so every check asserts something that can only be in the real file.
check() {
    local path="$1" needle="$2" dest
    dest="$workdir/$(printf '%s' "$path" | tr -c 'a-zA-Z0-9' '_')"
    if ! fetch "$path" "$dest"; then
        printf '  FAIL  %s is not served (still failing after %s attempts)\n' "$path" "$ATTEMPTS"
        failures=$((failures + 1))
        return 1
    fi
    if ! grep -qF -- "$needle" "$dest"; then
        printf '  FAIL  %s is served but does not contain %s\n' "$path" "$needle"
        failures=$((failures + 1))
        return 1
    fi
    printf '  ok    %s\n' "$path"
    return 0
}

printf 'Smoke-testing %s\n\n' "$SITE"

# The one that actually broke, and the reason this file exists. RFC 9116 names
# /.well-known/security.txt as the location and there is no root copy of it here, so a scanner
# following the spec sees this or nothing. Checked first: it is the canary for the whole
# dotfile-stripping problem.
check /.well-known/security.txt 'Contact:'

# The other dotfile. It is empty, so a 200 is the whole test — but without it Pages runs Jekyll over
# the checkout and discards anything whose name begins with an underscore.
if fetch /.nojekyll "$workdir/nojekyll"; then
    printf '  ok    /.nojekyll\n'
else
    printf '  FAIL  /.nojekyll is not served, so Pages may be running Jekyll\n'
    failures=$((failures + 1))
fi

check /robots.txt   'Sitemap: '
check /sitemap.xml  '<urlset'

# The two assets, each by a token that only exists if the file arrived intact. A truncated
# stylesheet leaves an unstyled site that answers 200 to everything else.
check /css/styles.css 'state-note'
check /js/site.js     'contact-form'

# Every page in the deployed sitemap, asserted on carrying its own CSP meta tag and a title. The CSP
# is delivered by meta because Pages serves no headers, so it is content: if a page loses it, no
# response header replaces it and nothing else would notice.
if fetch /sitemap.xml "$workdir/sm.xml"; then
    grep -o '<loc>[^<]*</loc>' "$workdir/sm.xml" \
        | sed -e 's|<loc>||' -e 's|</loc>||' > "$workdir/urls.txt"
    while read -r url; do
        [ -z "$url" ] && continue
        path="${url#https://seqontrol.com}"
        [ -z "$path" ] && path=/
        dest="$workdir/page$(printf '%s' "$path" | tr -c 'a-zA-Z0-9' '_')"
        if ! fetch "$path" "$dest"; then
            printf '  FAIL  %s is in the sitemap but is not served\n' "$path"
            failures=$((failures + 1))
            continue
        fi
        if ! grep -qi '<title>' "$dest"; then
            printf '  FAIL  %s is served but has no <title>; it is not the page that was built\n' "$path"
            failures=$((failures + 1))
            continue
        fi
        if ! grep -qF 'Content-Security-Policy' "$dest"; then
            printf '  FAIL  %s is served without its Content-Security-Policy meta tag\n' "$path"
            failures=$((failures + 1))
            continue
        fi
        printf '  ok    %s\n' "$path"
    done < "$workdir/urls.txt"
else
    printf '  FAIL  /sitemap.xml is not served, so page coverage could not be checked\n'
    failures=$((failures + 1))
fi

# The retired products page redirects rather than 404s, because it was in the sitemap for months and
# half the site linked to its anchors. A meta refresh is the only redirect Pages allows.
check /products/coming.html 'http-equiv="refresh"'

printf '\n'
if [ "$failures" -gt 0 ]; then
    printf '%s check(s) failed. The deploy reported success but the site is not serving what was built.\n' "$failures"
    exit 1
fi
printf 'All checks passed.\n'
