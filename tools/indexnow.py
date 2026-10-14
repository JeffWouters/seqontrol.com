#!/usr/bin/env python3
"""Tell search engines which pages changed, through IndexNow.

IndexNow (https://www.indexnow.org) is a ping: the site lists URLs that changed, and Bing, Yandex and
the other participating engines recrawl them instead of waiting to rediscover them. Google does not
take part; it reads sitemap.xml, which build_seo.py keeps current.

The key below is public by design. The engines prove the ping came from this site by fetching
https://seqontrol.com/<KEY>.txt and comparing its contents with the key in the ping, so the file must
stay at the site root and must contain exactly the key. Changing the key means renaming that file
in the same commit.

Usage, from the deploy workflow after the smoke test has passed:
    python tools/indexnow.py <before-sha> <after-sha>    pages changed between two commits
    python tools/indexnow.py --all                       every page in sitemap.xml

Only URLs listed in sitemap.xml are ever sent, so a changed tool, stylesheet or draft never is. A
failed ping is reported as a workflow warning and never fails the run: the deploy already happened,
and a missed ping only means the engines find the change on their own schedule.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

HOST = "seqontrol.com"
SITE = f"https://{HOST}/"
KEY = "365386801392052bf24fb6390765394a"
ENDPOINT = "https://api.indexnow.org/indexnow"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sitemap_urls() -> list[str]:
    with open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8") as f:
        return re.findall(r"<loc>([^<]+)</loc>", f.read())


def url_for(path: str) -> str:
    """A repository path to the URL the sitemap uses for it: index.html is served as its folder."""
    if path == "index.html":
        return SITE
    if path.endswith("/index.html"):
        return SITE + path[: -len("index.html")]
    return SITE + path


def changed_urls(before: str, after: str) -> list[str]:
    known = set(sitemap_urls())
    # A first push, or a force-push that dropped `before`, has nothing to diff against.
    if not before or set(before) == {"0"}:
        return sorted(known)
    try:
        out = subprocess.run(["git", "diff", "--name-only", before, after], cwd=ROOT,
                             check=True, capture_output=True, text=True).stdout
    except subprocess.CalledProcessError:
        return sorted(known)
    # A stylesheet, script or the shared chrome changes every page, so send them all.
    paths = out.split()
    if any(p.startswith(("css/", "js/")) for p in paths):
        return sorted(known)
    return sorted({url_for(p) for p in paths if p.endswith(".html")} & known)


def main(argv: list[str]) -> int:
    with open(os.path.join(ROOT, f"{KEY}.txt"), encoding="utf-8") as f:
        if f.read().strip() != KEY:
            print(f"::error::{KEY}.txt does not contain the key; IndexNow would reject every ping")
            return 1

    if argv[1:] == ["--all"]:
        urls = sitemap_urls()
    elif len(argv) == 3:
        urls = changed_urls(argv[1], argv[2])
    else:
        print(__doc__)
        return 2

    if not urls:
        print("No page in sitemap.xml changed; nothing to send.")
        return 0

    body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"{SITE}{KEY}.txt",
                       "urlList": urls}).encode()
    request = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                     headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as e:
        status = e.code
    except OSError as e:
        print(f"::warning::IndexNow ping failed: {e}")
        return 0

    # 200 = received, 202 = received and the key is still being checked.
    if status in (200, 202):
        print(f"IndexNow accepted {len(urls)} URL(s) (HTTP {status}):")
        for url in urls:
            print(f"  {url}")
    else:
        print(f"::warning::IndexNow answered HTTP {status} for {len(urls)} URL(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
