"""
Structured JD parsing (remediation brief R2).

For every scraped posting this extracts into structured fields:
  - exact job title, company, parent group
  - city (and remote/hybrid)
  - start date and duration
  - language requirements with level
  - submission channel (the portal/URL the JD instructs you to use)
  - named technologies, split required vs "a plus"
  - domain (the employer's actual business)
  - named contact, application deadline

If any of city, start date or submission channel cannot be extracted, the
posting is FLAGGED for manual review rather than guessed at (R2). The gate
then refuses to generate for a flagged posting.
"""

import re
import sys
import os
from datetime import date, datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline.relevance_filter import _word_match
from fact_bank import CANONICAL_TECHNOLOGIES, KNOWN_GAPS

# ---------------------------------------------------------------------------
# City normalisation (umlaut-stripped keys, mirroring collectors/arbeitnow.py)
# ---------------------------------------------------------------------------

_CITY_CANONICAL = {
    "berlin": "Berlin", "potsdam": "Potsdam",
    "munich": "Munich", "muenchen": "Munich", "munchen": "Munich",
    "frankfurt": "Frankfurt", "hamburg": "Hamburg",
    "cologne": "Cologne", "koeln": "Cologne", "koln": "Cologne",
    "stuttgart": "Stuttgart", "dusseldorf": "Duesseldorf",
    "duesseldorf": "Duesseldorf", "dortmund": "Dortmund", "essen": "Essen",
    "leipzig": "Leipzig", "bremen": "Bremen", "dresden": "Dresden",
    "hannover": "Hannover", "nuremberg": "Nuremberg",
    "nurnberg": "Nuremberg", "nuernberg": "Nuremberg", "bonn": "Bonn",
    "karlsruhe": "Karlsruhe", "mannheim": "Mannheim", "augsburg": "Augsburg",
    "wiesbaden": "Wiesbaden", "freiburg": "Freiburg", "mainz": "Mainz",
    "heidelberg": "Heidelberg", "darmstadt": "Darmstadt",
    "regensburg": "Regensburg", "ingolstadt": "Ingolstadt",
    "wolfsburg": "Wolfsburg", "walldorf": "Walldorf", "aachen": "Aachen",
    "ulm": "Ulm", "kiel": "Kiel", "erfurt": "Erfurt",
}

_REMOTE_MARKERS = ["remote", "home office", "homeoffice", "hybrid", "fully remote"]

_GERMAN_CITY_KEYS = set(_CITY_CANONICAL.keys())

# ---------------------------------------------------------------------------
# Language requirements
# ---------------------------------------------------------------------------

_LANG_LEVELS = {
    "muttersprache": 6, "native": 6, "mother tongue": 6, "native speaker": 6,
    "c2": 6, "verhandlungssicher": 5, "c1": 5, "fluent": 5, "flie\u00dfend": 5,
    "fluent german": 5, "b2": 4, "good": 4, "b1": 3, "basic": 2, "a2": 2,
    "grundkenntnisse": 2, "a1": 1, "elementary": 1,
}

# German-language tokens for each language.
_LANG_NAME_PATTERNS = {
    "german": [r"deutsch\w*", r"german\w*"],
    "english": [r"englisch\w*", r"english\w*"],
}

_GERMAN_BARRIER_PATTERNS = [
    r"verhandlungssicher(?:e[sn]?)?\s+deutsch",
    r"flie\u00dfend(?:e[sn]?)?\s+deutsch",
    r"deutsch\s+auf\s+(?:mutter|verhandlungs)",
    r"deutschkenntnisse\s+auf\s+(?:c1|c2)",
    r"native\s+german",
    r"fluent\s+german",
    r"german\s*\(?c[12]\)?",
    r"deutsch\s*\(?c[12]\)?",
    r"\bc1\b.*\bdeutsch\b", r"\bc2\b.*\bdeutsch\b",
    r"\bdeutsch\b.*\bc1\b", r"\bdeutsch\b.*\bc2\b",
]

# ---------------------------------------------------------------------------
# Start date / duration
# ---------------------------------------------------------------------------

_MONTHS_EN = {m.lower(): i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}
_MONTHS_DE = {m.lower(): i for i, m in enumerate(
    ["januar", "februar", "maerz", "märz", "april", "mai", "juni", "juli",
     "august", "september", "oktober", "november", "dezember"], 1)}
_MONTHS = {**_MONTHS_EN, **_MONTHS_DE}

_START_HINTS = [
    r"start\s*date", r"startdatum", r"start\s*:", r"begin\b", r"beginn\b",
    r"appointment\s*date", r"eintritt\b", r"entry\s*date", r"ab\s+sofort",
    r"zum\s*(?:fr\w*hesten)?", r"voraussichtlich(?:er)?\s*beginn",
]

_DURATION_HINTS = [
    r"(\d+)\s*(?:-\s*\d+)?\s*(?:month|months|monate|monaten|monat)",
    r"(?:month|months|monate|monaten|monat)\s*(?:\(|\s)*(?:for\s*)?(\d+)",
    r"for\s+(\d+)\s*(?:-\s*\d+)?\s*months",
    r"(\d+)\s*(?:bis\s*)?\d*\s*monate",
]

# ---------------------------------------------------------------------------
# Submission channel
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r"https?://[^\s\"'<>\)\]]+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

_PORTAL_MARKERS = [
    "careers.", "jobs.", "jobsearch", "recruiting", "recruit", "apply",
    "bewerbung", "karriere", "taleo", "successfactors", "workday",
    "jobs/", "/careers", "smartrecruiters", "greenhouse", "lever.co",
    "personio", "join.com", "applygate", "ats",
]

_EASY_APPLY_MARKERS = ["easy apply", "easyapply", "linkedin.com/jobs",
                       "einmalige bewerbung", "1-click apply"]

_CONTACT_HINTS = [r"contact\s*person", r"ansprechpartner", r"contact\s*:",
                  r"kontakt\s*:", r"recruiter", r"hr\s*contact"]

# ---------------------------------------------------------------------------
# Technology extraction
# ---------------------------------------------------------------------------

_BANK_TECH_RE = sorted(CANONICAL_TECHNOLOGIES, key=len, reverse=True)

def _extract_technologies(text):
    """Technologies in `text` that the fact bank knows (case-insensitive,
    word-boundary where sensible). Returns raw names (bank casing)."""
    found = []
    lower = text.lower()
    for tech in _BANK_TECH_RE:
        pattern = re.escape(tech)
        if not re.search(r"\s", tech):
            pattern = r"(?<![a-z0-9])" + pattern + r"(?![a-z0-9])"
        if re.search(pattern, lower, re.IGNORECASE):
            found.append(tech)
    return found


# ---------------------------------------------------------------------------
# Domain classification
# ---------------------------------------------------------------------------

_DOMAIN_SIGNALS = {
    "finance": ["portfolio", "fund", "credit", "valuation", "real estate",
                "investment", "asset", "banking", "insurance", "trading",
                "private equity", "lending", "debt", "capital", "treasury",
                "risk management", "liquidity"],
    "logistics": ["transit", "transport", "mobility", "logistics", "fleet",
                  "supply chain", "traffic", "routing", "congestion", "rail",
                  "warehouse", "freight", "delivery", "route", "vehicle",
                  "shipping", "carrier"],
    "consumer": ["consumer", "e-commerce", "ecommerce", "retail", "marketplace",
                 "b2c", "shopping", "customers", "user-facing", "booking",
                 "hotel", "travel", "food delivery", "media", "social",
                 "entertainment", "education"],
    "productivity": ["productivity", "office", "document", "writing",
                     "collaboration", "workflow", "scheduling", "content"],
    "platform": ["data platform", "data engineering", "pipeline", "warehouse",
                 "infrastructure", "mlops", "internal", "back office",
                 "backend platform", "etl", "data quality", "automation"],
}

_PLUS_SEGMENT_MARKERS = ["a plus", "nice to have", "bonus", "von vorteil",
                         "beneficial", "desired", "w\u00fcnschenswert",
                         "preferred", "would be a plus", "plus:"]

_REQUIRED_SEGMENT_MARKERS = ["requirements", "anforderungen", "qualifikation",
                             "profile", "profil", "must", "required",
                             "erforderlich", "voraussetzung", "skills",
                             "what you", "we expect"]

# ---------------------------------------------------------------------------
# Main parse
# ---------------------------------------------------------------------------

def _norm(text):
    t = (text or "").lower()
    for a, b in [("\u00e4", "a"), ("\u00f6", "o"), ("\u00fc", "u"), ("\u00df", "ss")]:
        t = t.replace(a, b)
    return t


def parse_city(location, jd_text=""):
    """Return (city_key, display_city, remote) or (None, None, remote)."""
    hay = _norm(f"{location} {jd_text[:2000]}")
    remote = any(m in hay for m in _REMOTE_MARKERS)
    # Location field is authoritative when it names a city.
    for key in _GERMAN_CITY_KEYS:
        if _word_match(key, _norm(location)):
            return key, _CITY_CANONICAL[key], remote
    # Fall back to JD text for the city name.
    for key in _GERMAN_CITY_KEYS:
        if _word_match(key, hay):
            return key, _CITY_CANONICAL[key], remote
    if remote:
        return "remote", "Remote", remote
    return None, None, remote


def _parse_date_candidate(s):
    s = s.strip().rstrip(".").strip()
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    m = re.match(r"(\d{1,2})[./](\d{1,2})[./](\d{2,4})$", s)
    if m:
        d, mo, y = m.groups()
        y = int(y) if len(y) == 4 else 2000 + int(y)
        try:
            return date(y, int(mo), int(d))
        except ValueError:
            return None
    return None


def parse_start_date(jd_text, title=""):
    """Return (start_date or None, start_text or None)."""
    text = jd_text or ""
    today = date.today()

    # Whole-line / explicit date patterns.
    for m in re.finditer(
            r"(?:start(?:ing|s| date)?|beginn|eintritt|appointment date|zum|ab)\s*"
            r"[:\-]?\s*(\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{4}-\d{2}-\d{2})",
            text, re.IGNORECASE):
        d = _parse_date_candidate(m.group(1))
        if d:
            return d, d.isoformat()

    # Month-year patterns.
    for m in re.finditer(
            r"\b(january|february|march|april|may|june|july|august|september|"
            r"october|november|december|januar|februar|maerz|m\u00e4rz|april|mai|"
            r"juni|juli|august|september|oktober|november|dezember)"
            r"\s+(20\d{2}|'\d{2})", text, re.IGNORECASE):
        mon = _MONTHS.get(m.group(1).lower())
        yr = int(m.group(2).replace("'", ""))
        yr = yr + 2000 if yr < 100 else yr
        if mon:
            return date(yr, mon, 1), m.group(0)

    # "ab sofort" / "immediately".
    if re.search(r"\bab\s+sofort\b|start\s+immediately|available immediately",
                 text, re.IGNORECASE):
        return today, "as soon as possible"

    # First sentence containing a start hint and a year.
    for hint in _START_HINTS:
        m = re.search(hint + r"[^.]{0,120}\b(20\d{2}|'\d{2})\b", text, re.IGNORECASE)
        if m:
            year = int(m.group(1).replace("'", ""))
            year = year + 2000 if year < 100 else year
            mon = None
            sentence = m.group(0)
            for name, idx in _MONTHS.items():
                if _word_match(name, sentence):
                    mon = idx
                    break
            if mon:
                return date(year, mon, 1), sentence.strip()[:80]
    return None, None


def parse_duration(jd_text):
    text = jd_text or ""
    for pat in _DURATION_HINTS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            n = int(m.group(1))
            return f"{n} months", n
    return "", None


def parse_languages(jd_text, title=""):
    """Return a list of {lang, level, level_code} for each language found.
    A language mention whose enclosing sentence contains a plus marker
    ("C1 is a plus", "nice to have") is reported with level_code=None and
    plus=True -- it is not a hard requirement."""
    text = f"{title or ''} {jd_text or ''}"
    sentences = re.split(r"(?<=[.!?])\s+", text)
    result = []
    for lang, pats in _LANG_NAME_PATTERNS.items():
        found_level = None
        found_code = None
        is_plus = False
        for m in re.finditer(r"\b(?:%s)\b" % "|".join(pats), text, re.IGNORECASE):
            # Sentence that contains this mention.
            sentence = next((s for s in sentences if m.group(0).lower() in s.lower()), text)
            plus_ctx = any(mk in sentence.lower() for mk in _PLUS_SEGMENT_MARKERS)
            window = sentence.lower()
            best_code = None
            for word, code in sorted(_LANG_LEVELS.items(), key=lambda kv: -kv[1]):
                if re.search(r"\b" + re.escape(word) + r"\b", window):
                    best_code = code
                    found_level = word
                    break
            if best_code is not None and (found_code is None or best_code > found_code):
                found_code = best_code
            if plus_ctx:
                is_plus = True
        if found_level or lang in _norm(text):
            result.append({
                "lang": lang.capitalize(),
                "level": found_level or "",
                "level_code": None if is_plus else found_code,
                "plus": is_plus,
            })
    return result


def parse_submission_channel(posting):
    """Return (channel, kind, note) where kind is
    'company_portal' | 'email' | 'easy_apply' | 'apply_url' | None.

    R9: the channel the JD instructs you to use wins. LinkedIn Easy Apply is
    NOT a substitute for a company portal and is flagged as non-compliant.
    """
    jd = posting.get("jd_text", "") or ""
    apply_url = posting.get("apply_url", "") or ""
    jd_lower = jd.lower()

    emails = _EMAIL_RE.findall(jd)
    urls = [u.rstrip(".,;") for u in _URL_RE.findall(jd)]
    # Bare "careers.example.com" domains in the JD count as portal URLs too.
    urls += [u.group(0).rstrip(".,;") for u in re.finditer(
        r"(?:careers\.|jobs\.|jobsearch\.|recruiting\.|recruit\.|apply\."
        r"|karriere\.|bewerbung\.)[\w.-]+\.(?:com|de|org|net|io|ch|at|eu)[^\s\"'<>\)\]]*",
        jd, re.IGNORECASE)]

    # 1. A portal the JD explicitly names always wins.
    portal = None
    for u in urls:
        low = u.lower()
        if any(mk in low for mk in _PORTAL_MARKERS):
            portal = u
            break
    if portal:
        return portal, "company_portal", "JD names the employer's portal; use it, not Easy Apply"

    # 2. An application email address in the JD.
    if emails:
        return emails[0], "email", "JD names a contact address"

    # 3. LinkedIn Easy Apply markers.
    for marker in _EASY_APPLY_MARKERS:
        if marker in jd_lower or marker in apply_url.lower():
            return "LinkedIn Easy Apply", "easy_apply", "non-compliant: does not reach the employer's ATS"

    # 4. A non-LinkedIn apply_url from the source listing.
    if apply_url and not apply_url.lower().startswith(("https://www.linkedin.com", "http://www.linkedin.com")):
        return apply_url, "apply_url", "apply_url from the source listing"
    if apply_url:
        return apply_url, "easy_apply", "source apply_url is a LinkedIn listing; verify the employer's portal"
    return None, None, "submission channel not stated - flag for manual review"


def parse_contact(jd_text):
    """Best-effort named contact person (or a contact-like string) from the JD.

    'Contact: Anna Schmidt. Apply via careers.x.com' must yield 'Anna Schmidt',
    not the whole rest of the paragraph. We stop the snippet at the first
    sentence boundary after the hint, then keep only a person-name prefix.
    """
    text = jd_text or ""
    emails = _EMAIL_RE.findall(text)
    for hint in _CONTACT_HINTS:
        m = re.search(hint + r"[^\n]{0,160}", text, re.IGNORECASE)
        if not m:
            continue
        snippet = m.group(0)
        if emails:
            cut = snippet.find(emails[0])
            if cut != -1:
                snippet = snippet[:cut].rstrip(", ")
        # Stop at the first sentence boundary ("Name. Next sentence").
        snippet = re.split(r"\.\s+[A-Z\u00c4\u00d6\u00dc]", snippet)[0]
        snippet = re.sub(r"[\.;:]*$", "", snippet).strip()
        # Keep only a person-name prefix ("Anna Schmidt"), tolerating 2-4
        # capitalized words. Falls back to the truncated snippet.
        name = re.match(
            r"^(?:contact\s*person\s*[:\-]?\s*|ansprechpartner(?:in)?\s*[:\-]?\s*"
            r"|contact\s*[:\-]\s*)?"
            r"([A-Z\u00c4\u00d6\u00dc][a-z\u00e4\u00f6\u00fc\u00df]+"
            r"(?:\s+[A-Z\u00c4\u00d6\u00dc][a-z\u00e4\u00f6\u00fc\u00df]+){1,3})",
            snippet, re.IGNORECASE)
        if name:
            return name.group(1)
        if len(snippet) > 4:
            return snippet[:120]
    return emails[0] if emails else ""


def parse_deadline(jd_text):
    text = jd_text or ""
    for m in re.finditer(
            r"(?:deadline|frist|apply\s*by|bis\s+zum|bewerbungsfrist)"
            r"[^.\n]{0,40}?(\d{1,2}[./]\d{1,2}[./]\d{2,4})", text, re.IGNORECASE):
        d = _parse_date_candidate(m.group(1))
        if d:
            return d, m.group(0).strip()[:80]
    for m in re.finditer(
            r"(?:deadline|frist|apply\s*by|bewerbungsfrist)[^.\n]{0,60}"
            r"\b(20\d{2})", text, re.IGNORECASE):
        return None, m.group(0).strip()[:80]
    return None, ""


def parse_domain(jd_text, title=""):
    """Classify the employer's business into a domain family."""
    text = _norm(f"{title} {jd_text}")
    scores = {}
    for domain, signals in _DOMAIN_SIGNALS.items():
        scores[domain] = sum(1 for s in signals if _word_match(s, text))
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def _split_required_plus(jd_text):
    """Split the JD into (required_segment, plus_segment)."""
    text = jd_text or ""
    lower = text.lower()
    # Find the split point between "requirements" and "nice to have" segments.
    plus_idx = None
    for mk in _PLUS_SEGMENT_MARKERS:
        idx = lower.find(mk)
        if idx != -1 and (plus_idx is None or idx < plus_idx):
            plus_idx = idx
    req_idx = None
    for mk in _REQUIRED_SEGMENT_MARKERS:
        idx = lower.find(mk)
        if idx != -1 and (req_idx is None or idx < req_idx):
            req_idx = idx

    if plus_idx is not None:
        return text[:plus_idx], text[plus_idx:]
    if req_idx is not None:
        return text[req_idx:], ""
    return text, ""


def parse_posting(posting):
    """Parse one posting dict into structured fields (R2)."""
    title = (posting.get("title") or "").strip()
    company = (posting.get("company") or "").strip()
    jd_text = posting.get("jd_text", "") or ""
    location = posting.get("location", "") or ""

    city_key, city_display, remote = parse_city(location, jd_text)
    start_date, start_text = parse_start_date(jd_text, title)
    duration, duration_months = parse_duration(jd_text)
    languages = parse_languages(jd_text, title)
    channel, channel_kind, channel_note = parse_submission_channel(posting)
    domain = parse_domain(jd_text, title)
    contact = parse_contact(jd_text)
    deadline, deadline_note = parse_deadline(jd_text)

    required_seg, plus_seg = _split_required_plus(jd_text)
    required_techs = _extract_technologies(required_seg)
    plus_techs = _extract_technologies(plus_seg)
    # A technology anywhere in the JD is at minimum "mentioned".
    mentioned = set(required_techs) | set(plus_techs) | set(_extract_technologies(jd_text))

    # Gaps: JD-named technologies the candidate lacks.
    jd_all = set(_extract_technologies(jd_text)) | {
        t for t in KNOWN_GAPS if _word_match(t, jd_text)}
    gaps = sorted(jd_all - mentioned)

    # Language requirements: only mentions NOT flagged as "plus" count as hard
    # requirements (a "C1 is a plus" line must not block the application).
    languages_mentioned = parse_languages(jd_text, title)
    languages_required = [lang for lang in languages_mentioned if not lang.get("plus")]

    missing = []
    if city_key is None:
        missing.append("city")
    if start_date is None:
        missing.append("start_date")
    if channel is None:
        missing.append("submission_channel")

    return {
        "title": title,
        "company": company,
        "parent_group": "",              # populated by gate (known-group map)
        "city": city_display,
        "city_key": city_key,
        "remote": bool(remote),
        "start_date": start_date,
        "start_text": start_text,
        "duration": duration,
        "duration_months": duration_months,
        "languages": languages_mentioned,
        "languages_required": languages_required,
        "submission_channel": channel,
        "submission_channel_kind": channel_kind,
        "submission_channel_note": channel_note,
        "required_technologies": sorted(set(required_techs)),
        "plus_technologies": sorted(set(plus_techs)),
        "technologies_mentioned": sorted(mentioned),
        "technology_gaps": gaps,
        "domain": domain,
        "contact": contact,
        "deadline": deadline,
        "deadline_note": deadline_note,
        "flagged": missing,
        "age_days": _posting_age_days(posting),
    }


def _posting_age_days(posting):
    """Approximate posting age in days from date_posted, or 0 if unparseable."""
    from pipeline.date_filter import _parse_any_date
    dt = _parse_any_date(posting.get("date_posted"))
    if dt is None:
        return 0
    return (date.today() - dt.date()).days


if __name__ == "__main__":
    sample = {
        "company": "PIMCO Prime Real Estate",
        "title": "Intern in Software and Data Engineering (m/f/d)",
        "location": "Munich, Germany",
        "apply_url": "https://www.linkedin.com/jobs/view/123",
        "jd_text": ("Intern in Software and Data Engineering. Our team manages an $85B real estate "
                    "mandate using Databricks and Streamlit. Requirements: Python, RAG/LLM solutions "
                    "using vector databases, Spark. Start date 01.10.2026, duration 6 months. "
                    "Fluency in German (C1) is a plus. Applications via careers.allianz.com. "
                    "Contact: Anna Schmidt, anna.schmidt@allianz.com. Deadline 15.08.2026."),
    }
    parsed = parse_posting(sample)
    for k, v in parsed.items():
        print(f"{k}: {v}")
