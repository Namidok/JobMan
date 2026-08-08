"""Collects postings from Absolventa (German student/internship job board --
carries internship volume the LinkedIn ecosystem misses).

Search cards give title, company, location and a 'Neu' freshness badge but no
relative date, so only 'Neu' cards are dated as today; everything else is
dropped by the last-24h filter (we only want fresh postings anyway). The job
detail page is fetched for the full JD so parsing has real content.
"""

import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from collectors import _scrape
from pipeline.date_filter import filter_last_24h
from pipeline.relevance_filter import filter_relevant
from datetime import date

SEARCH_URL = "https://www.absolventa.de/jobs?text={query}&location={city}"
DETAIL_BASE = "https://www.absolventa.de"

KEYWORDS = ["data engineer", "machine learning", "ai", "nlp", "werkstudent",
            "praktikum", "intern"]
MAX_DETAILS = 40


def _parse_listing(html_text):
    soup = _scrape.soupify(html_text)
    if soup is None:
        return []
    out = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/stellenangebote/" not in href:
            continue
        key = href.split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        card = a.find_parent("article") or a.find_parent("li")
        card_text = card.get_text(" | ", strip=True) if card else ""
        parts = [p.strip() for p in card_text.split("|") if p.strip()]

        # The title lives in the card's heading (the anchor wraps the whole
        # card, so a.get_text() would duplicate it).
        title = ""
        if card:
            for h in card.find_all(["h1", "h2", "h3", "h4"]):
                t = h.get_text(" ", strip=True)
                if len(t) > 3 and t not in parts[:1]:
                    title = t
                    break
        if not title and len(parts) > 0:
            title = parts[0]

        company = parts[1] if len(parts) > 1 else ""
        # Location appears after a 'Standort' label.
        location = ""
        if "Standort" in parts:
            loc_i = parts.index("Standort")
            loc_parts = parts[loc_i + 1:loc_i + 3]
            location = " ".join(x for x in loc_parts if not x.isdigit() and x.lower() != "homeoffice")
        date_iso = ""
        if re.search(r"\bneu\b", card_text.lower()):
            date_iso = date.today().isoformat()
        out.append({
            "title": title,
            "href": key,
            "company": company,
            "location": location,
            "date_posted": date_iso,
        })
    return out


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


def fetch_postings(keywords=None, city="berlin", max_details=MAX_DETAILS):
    keywords = keywords or KEYWORDS
    postings = []
    detail_budget = max_details
    for kw in keywords:
        url = SEARCH_URL.format(query=_scrape.slugify(kw), city=_scrape.slugify(city))
        status, text = _scrape.http_get(url)
        if status != 200 or not text:
            print(f"Absolventa: search '{kw}' failed (status={status})")
            continue
        listings = _parse_listing(text)
        print(f"Absolventa: '{kw}' -> {len(listings)} listing(s)")
        for item in listings:
            detail_url = (DETAIL_BASE + item["href"]) if item["href"].startswith("/") else item["href"]
            jd_text = ""
            jd_date = ""
            if detail_budget > 0:
                status, text = _scrape.http_get(detail_url)
                detail_budget -= 1
                if status == 200 and text:
                    jt, jd_date, jdesc = _scrape.extract_jobposting_jsonld(text)
                    if jdesc:
                        jd_text = jdesc
                    if not jd_text:
                        body = _scrape.strip_html(text)
                        if len(body) >= 300:
                            jd_text = body
            # Backfill the publish date from JSON-LD when the card had no
            # 'Neu' badge -- lets the last-24h filter see genuinely fresh
            # postings instead of dropping them.
            if not item.get("date_posted") and jd_date:
                item["date_posted"] = jd_date[:10]
            postings.append({
                "source": "absolventa",
                "company": item["company"],
                "title": item["title"],
                "location": item["location"],
                "date_posted": item["date_posted"],
                "jd_text": jd_text,
                "apply_url": detail_url,
            })

    seen, uniq = set(), []
    for p in postings:
        key = (p["apply_url"] or p["title"]).lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    postings = uniq

    before = len(postings)
    postings, stats = filter_relevant(postings, require_internship_title=True)
    print(f"Absolventa: {before} collected, {stats['after_internship_filter']} internships, "
          f"{stats['after_domain_filter']} AI/Data/ML-relevant")

    kept, dropped = filter_last_24h(postings, date_field="date_posted")
    print(f"Absolventa: {len(kept)} within last 24h ({dropped} older/unparseable date)")
    return kept


if __name__ == "__main__":
    ps = fetch_postings()
    print(f"Found {len(ps)} Absolventa postings in the last 24h")
    for p in ps[:10]:
        print("-", p["company"], "|", p["title"], "|", p["location"], "|", p["date_posted"])
