"""Target-company career-page monitor (review feedback, item 1).

Polls the careers pages of 30-50 named target companies that never post to
Arbeitnow (or post late): Zalando, Delivery Hero, N26, HelloFresh, Celonis,
SAP, Siemens, Bosch, Databricks Berlin, AWS Berlin, Trade Republic, Flix,
Wayfair, Project A / Cherry portfolio companies, etc.

Company career pages are heterogeneous, so this uses the two public ATS JSON
APIs most of them run:

  * Greenhouse:  https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true
    Full JD in `content` (HTML), `absolute_url`, `location.name`, `updated_at`.
  * Lever:       https://api.lever.co/v0/postings/{board}?mode=json
    Full JD in `description` (HTML), `hostedUrl`, `categories.location`,
    `createdAt`.

Anything not on those two falls back to an HTML scrape of the configured
search URL (ld+json JobPosting blocks, then link extraction).

The board list lives in config.TARGET_COMPANIES so you can extend it without
touching code. Filtering is the same as the other collectors: internships +
AI/Data/ML-relevant + Germany + last 24h.
"""

import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from collectors import _scrape
from pipeline.date_filter import filter_last_24h
from pipeline.relevance_filter import filter_relevant
from collectors.arbeitnow import is_germany

GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
LEVER_URL = "https://api.lever.co/v0/postings/{board}?mode=json"


def _greenhouse(board, company_name):
    """Fetch all open jobs from a Greenhouse board. Returns raw posting dicts."""
    status, text = _scrape.http_get(GREENHOUSE_URL.format(board=board))
    if status != 200 or not text:
        print(f"  (greenhouse board '{board}' failed: status={status})")
        return []
    import json
    try:
        data = json.loads(text)
    except ValueError:
        return []
    out = []
    for j in data.get("jobs") or []:
        loc = (j.get("location") or {}).get("name") or ""
        out.append({
            "source": "targets",
            "company": company_name,
            "title": j.get("title") or "",
            "location": loc,
            "date_posted": j.get("updated_at") or "",
            "jd_text": _scrape.strip_html(j.get("content") or ""),
            "apply_url": j.get("absolute_url") or "",
        })
    return out


def _lever(board, company_name):
    status, text = _scrape.http_get(LEVER_URL.format(board=board))
    if status != 200 or not text:
        print(f"  (lever board '{board}' failed: status={status})")
        return []
    import json
    try:
        data = json.loads(text)
    except ValueError:
        return []
    out = []
    for j in data or []:
        loc = (j.get("categories") or {}).get("location") or ""
        out.append({
            "source": "targets",
            "company": company_name,
            "title": j.get("text") or "",
            "location": loc,
            "date_posted": j.get("createdAt") or "",
            "jd_text": _scrape.strip_html(j.get("description") or ""),
            "apply_url": j.get("hostedUrl") or "",
        })
    return out


def _html_fallback(search_url, company_name, item_pattern=r"job"):
    """Best-effort HTML scrape for companies without a public ATS JSON API.
    Extracts candidate links matching item_pattern (loose, case-insensitive)
    and the visible card text. Results depend on the configured URL being a
    genuinely server-rendered job listing page -- client-side job apps yield
    nav links only, which the relevance filter drops."""
    status, text = _scrape.http_get(search_url)
    if status != 200 or not text:
        print(f"  (html fallback for {company_name} failed: status={status})")
        return []
    soup = _scrape.soupify(text)
    if soup is None:
        return []
    out = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not re.search(item_pattern, href, re.IGNORECASE):
            continue
        full = href if href.startswith("http") else ("https://" + _scrape.strip_domain(search_url) + href)
        key = full.split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        txt = a.get_text(" ", strip=True)
        title = txt if len(txt) > 5 else _scrape.strip_html(a.get("title") or "")
        if not title:
            continue
        out.append({
            "source": "targets",
            "company": company_name,
            "title": title,
            "location": "",
            "date_posted": "",
            "jd_text": "",
            "apply_url": full,
        })
    return out


def _backfill_jds(postings, budget=40):
    """Fetch detail-page JDs for HTML-fallback postings that have no JD text.
    Best-effort and capped so a big board list cannot hammer a career page."""
    done = 0
    for p in postings:
        if p.get("jd_text") or not p.get("apply_url") or done >= budget:
            continue
        body = _fetch_jd(p["apply_url"])
        done += 1
        if body:
            p["jd_text"] = body
    return postings


def _fetch_jd(detail_url):
    status, text = _scrape.http_get(detail_url)
    if status != 200 or not text:
        return ""
    jt, jd_date, jdesc = _scrape.extract_jobposting_jsonld(text)
    if jdesc:
        return jdesc
    body = _scrape.strip_html(text)
    if len(body) < 300:
        return ""
    return body


def fetch_postings(companies=None, max_per_company=200):
    from config import TARGET_COMPANIES
    companies = companies if companies is not None else TARGET_COMPANIES
    postings = []
    for target in companies:
        name = target["name"]
        board = target.get("board")
        kind = target.get("kind", "html")
        url = target.get("url")
        print(f"Target: {name} ({kind})...")
        try:
            if kind == "greenhouse" and board:
                got = _greenhouse(board, name)
            elif kind == "lever" and board:
                got = _lever(board, name)
            else:
                got = _html_fallback(url or "", name, target.get("item_pattern", r"/jobs"))
        except Exception as e:
            print(f"  (target {name} failed: {type(e).__name__}: {e})")
            continue

        # Keep only Germany + internships/working-student postings.
        germany_ok = [p for p in got if not p["location"] or is_germany(p["location"])]
        got = germany_ok[:max_per_company]
        postings.extend(got)
        print(f"Target: {name} -> {len(got)} Germany posting(s)")

    postings = _backfill_jds(postings)

    before = len(postings)
    postings, stats = filter_relevant(postings, require_internship_title=True)
    print(f"Targets: {before} collected, {stats['after_internship_filter']} internships, "
          f"{stats['after_domain_filter']} AI/Data/ML-relevant")

    # Date-bearing postings (Greenhouse/Lever) are gated to the last 24h like
    # every other source. Date-less HTML-fallback cards are kept in full: the
    # tracker's dedupe makes repeats harmless, and a target-company role that
    # has no publish date is exactly what the manual monitor should surface.
    dated, undated = [], []
    for p in postings:
        (dated if p.get("date_posted") else undated).append(p)
    kept, dropped = filter_last_24h(dated, date_field="date_posted")
    print(f"Targets: {len(kept)} dated posting(s) within last 24h "
          f"({dropped} older/unparseable) + {len(undated)} undated (tracker-deduped)")
    return kept + undated


if __name__ == "__main__":
    ps = fetch_postings()
    print(f"Found {len(ps)} target-company postings in the last 24h")
    for p in ps[:15]:
        print("-", p["company"], "|", p["title"], "|", p["location"], "|", p["date_posted"])
