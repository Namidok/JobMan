"""Collects postings from StepStone's public job board (Germany internship
volume that Arbeitnow/LinkedIn miss).

The old pipeline only had Arbeitnow. StepStone is the biggest German
job board and carries internship/working-student volume LinkedIn doesn't.
This collector:

  * searches keyword x city pages
  * extracts every job card (title, company, location, apply date) from the
    rendered HTML (data-testid="job-item-title")
  * fetches each job's detail page to recover the full JD text, so the
    parser's city / start-date / channel extraction has real content
  * filters to internships + AI/Data/ML-relevant + last 24h, exactly like
    the Arbeitnow collector

Detail-page fetching is best-effort and capped (max_details) so a large
search result cannot hammer the site.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from collectors import _scrape
from pipeline.date_filter import filter_last_24h
from pipeline.relevance_filter import filter_relevant

SEARCH_URL = "https://www.stepstone.de/jobs/{keyword}/in-{city}"
DETAIL_BASE = "https://www.stepstone.de"

KEYWORDS = ["data-engineer", "machine-learning", "ai-engineer", "nlp", "data-scientist",
            "artificial-intelligence", "genai", "llm", "praktikum", "werkstudent", "intern"]
CITIES = ["berlin", "potsdam"]

# Cap on detail-page fetches per run so a big result set stays polite.
MAX_DETAILS = 40


def _parse_listing(html_text):
    """Yield dicts for every job card in a search page."""
    soup = _scrape.soupify(html_text)
    if soup is None:
        return []
    out = []
    for a in soup.find_all("a", attrs={"data-testid": "job-item-title"}):
        href = a.get("href") or ""
        if not href or "/in-" in href:
            continue
        title = a.get_text(" ", strip=True)
        card = a.find_parent("article")
        card_text = card.get_text(" | ", strip=True) if card else ""
        parts = [p.strip() for p in card_text.split("|")]
        # Card layout: 'Passt hervorragend' | title | company | location | ...
        company = parts[2] if len(parts) > 2 else ""
        location = parts[3] if len(parts) > 3 else ""
        # Apply method marker is a real signal for the channel note.
        channel_hint = ""
        for marker in ("Auf Unternehmenswebsite", "Schnelle Bewerbung"):
            if marker in card_text:
                channel_hint = marker
                break
        date_iso = ""
        if card:
            for time_el in card.find_all("time"):
                iso = _scrape.german_relative_to_iso(time_el.get_text(" ", strip=True))
                if iso:
                    date_iso = iso
                    break
        out.append({
            "title": title,
            "href": href,
            "company": company,
            "location": location,
            "date_posted": date_iso,
            "channel_hint": channel_hint,
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
    keywords = keywords or ["data-engineer", "werkstudent", "intern"]
    postings = []
    detail_budget = max_details
    for kw in keywords:
        url = SEARCH_URL.format(keyword=_scrape.slugify(kw), city=_scrape.slugify(city))
        status, text = _scrape.http_get(url)
        if status != 200 or not text:
            print(f"StepStone: search '{kw}' failed (status={status})")
            continue
        listings = _parse_listing(text)
        print(f"StepStone: '{kw}' in {city} -> {len(listings)} listing(s)")
        for item in listings:
            detail_url = DETAIL_BASE + item["href"] if item["href"].startswith("/") else item["href"]
            jd_text = item.get("channel_hint", "")
            if detail_budget > 0:
                body = _fetch_jd(detail_url)
                detail_budget -= 1
                if body:
                    jd_text = f"{body}\n\n[Channel: {item['channel_hint']}]" if item.get("channel_hint") else body
            postings.append({
                "source": "stepstone",
                "company": item["company"],
                "title": item["title"],
                "location": item["location"],
                "date_posted": item["date_posted"],
                "jd_text": jd_text,
                "apply_url": detail_url,
            })

    # Dedupe by apply_url within this batch (a posting can appear under several
    # keywords).
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
    print(f"StepStone: {before} collected, {stats['after_internship_filter']} internships, "
          f"{stats['after_domain_filter']} AI/Data/ML-relevant")

    kept, dropped = filter_last_24h(postings, date_field="date_posted")
    print(f"StepStone: {len(kept)} within last 24h ({dropped} older/unparseable date)")
    return kept


if __name__ == "__main__":
    ps = fetch_postings()
    print(f"Found {len(ps)} StepStone postings in the last 24h")
    for p in ps[:10]:
        print("-", p["company"], "|", p["title"], "|", p["location"], "|", p["date_posted"])
