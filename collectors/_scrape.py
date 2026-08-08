"""Shared helpers for the HTML/JSON scraping collectors (StepStone,
Absolventa, target-company ATS boards). Kept dependency-light: requests only,
plus optional BeautifulSoup when installed."""

import re
import sys
import os
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests

USER_AGENT = "Mozilla/5.0 (job-application-collector)"
TIMEOUT = 25


def http_get(url, timeout=TIMEOUT, headers=None):
    """GET with a browser-ish UA. Returns (status, text) or (None, None) on
    transport errors / non-200. Never raises."""
    try:
        h = {"User-Agent": USER_AGENT}
        if headers:
            h.update(headers)
        r = requests.get(url, headers=h, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return r.status_code, r.text
        return r.status_code, r.text
    except Exception as e:
        print(f"  (http error for {url[:80]}: {type(e).__name__})")
        return None, None


def soupify(html_text):
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(html_text or "", "html.parser")
    except ImportError:
        return None


def extract_jobposting_jsonld(html_text):
    """Pull (title, date_posted, description_text) from a schema.org JobPosting
    JSON-LD block. Job detail pages that render the JD in the JSON-LD give the
    cleanest content here -- far better than trimming the whole page's chrome.
    Returns (None, None, None) when no JobPosting block is present."""
    if not html_text:
        return None, None, None
    import html as _h
    import json as _json
    for m in re.finditer(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html_text, re.DOTALL | re.IGNORECASE):
        raw = m.group(1).strip()
        if not raw:
            continue
        # Some boards embed literal control characters inside JSON string
        # values (a raw newline in the description), which strict json.loads
        # rejects. Replacing them with spaces keeps valid whitespace outside
        # strings and turns the offending control chars inside strings into
        # harmless text.
        raw = re.sub(r"[\x00-\x1f]", " ", raw)
        try:
            data = _json.loads(raw)
        except ValueError:
            continue
        blocks = data if isinstance(data, list) else [data]
        for b in blocks:
            if isinstance(b, dict) and b.get("@type") == "JobPosting":
                desc = _h.unescape(b.get("description") or "")
                desc = re.sub(r"<[^>]+>", " ", desc)
                desc = re.sub(r"\s+", " ", desc).strip()
                return b.get("title"), b.get("datePosted"), desc[:6000]
    return None, None, None


def strip_html(html_text, max_len=6000):
    """HTML -> rough text: drop script/style contents and tags, unescape
    entities, collapse whitespace. Capped at max_len so a detail page's
    inline JavaScript cannot flood the JD field."""
    if not html_text:
        return ""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html_text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    try:
        import html as _h
        text = _h.unescape(text)
    except Exception:
        pass
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def slugify(text):
    """'Data Engineer (m/f/d)' -> 'data-engineer-m-f-d' (StepStone URL style)."""
    s = (text or "").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def strip_domain(url):
    """'https://www.example.com/careers?x=1' -> 'www.example.com'."""
    m = re.match(r"https?://([^/]+)", (url or ""))
    return m.group(1) if m else ""


def german_relative_to_iso(text, today=None):
    """Parse German relative dates used on job boards into ISO dates.

    Handles 'Heute', 'Gestern', 'Erschienen: vor 1 Tag', 'vor 3 Tagen',
    'vor 2 Wochen', 'vor 1 Monat', 'vor 5 Stunden', 'vor 30 Minuten'.
    Returns '' when nothing is recognizable."""
    today = today or date.today()
    t = re.sub(r"\s+", " ", (text or "").lower())
    if not t:
        return ""

    if re.search(r"\bheute\b", t):
        return today.isoformat()
    if re.search(r"\bgestern\b", t):
        return (today - timedelta(days=1)).isoformat()

    m = re.search(r"vor\s+(\d+)\s+(minuten?|stunden?|tagen?|wochen?|monaten?)", t)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        days = 0
        if unit.startswith("minute") or unit.startswith("stunde"):
            days = 0
        elif unit.startswith("tag"):
            days = n
        elif unit.startswith("woche"):
            days = 7 * n
        elif unit.startswith("monat"):
            days = 30 * n
        return (today - timedelta(days=days)).isoformat()

    # Plain ISO / DD.MM.YYYY dates.
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b", t)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date().isoformat()
        except ValueError:
            return ""
    return ""


def is_internship_title(title):
    """Cheap internship check (praktikum/werkstudent/internship/student/student/intern)."""
    t = (title or "").lower()
    return any(k in t for k in ("praktikum", "werkstudent", "intern", "student", "working student"))
