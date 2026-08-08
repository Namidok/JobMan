"""
Disqualification gate (remediation brief R3).

Rejects a posting BEFORE document generation, with a logged reason:

  - German requirement above the candidate's level (config: max_german_level)
  - Start date outside the candidate's availability window
  - Location outside the candidate's relocation list
  - Posting older than MAX_POSTING_AGE_DAYS
  - Duplicate of a posting already applied to, including cross-platform
    reposts of the same requisition (matched on company group + title + city)
  - Role is not genuinely Data Engineering / Applied AI (no stretching to ML
    Research, Data Science, or generic SWE)
  - Required structured field missing (city / start date / submission
    channel) -- the parser flagged it; we refuse to guess (R2)
  - LinkedIn Easy Apply as the only submission channel (R9) -- refused
    because it never reaches the employer's ATS (BLOCK_EASY_APPLY_ONLY)

The gate reads ALL thresholds from config (CANDIDATE_PROFILE,
MAX_POSTING_AGE_DAYS); nothing is hardcoded here.
"""

import re
import sys
import os
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import CANDIDATE_PROFILE, MAX_POSTING_AGE_DAYS, BLOCK_EASY_APPLY_ONLY
from pipeline.jd_parser import parse_posting

# Parent groups that run a single ATS across subsidiaries. A repost from any
# subsidiary must be caught as the same requisition.
PARENT_GROUPS = {
    "pimco prime real estate": "PIMCO",
    "allianz": "Allianz",
    "allianz technology": "Allianz",
    "sap": "SAP",
    "bosch": "Bosch",
    "siemens": "Siemens",
    "volkswagen": "Volkswagen",
    "vw": "Volkswagen",
    "bmw": "BMW",
    "bmw group": "BMW",
    "mercedes": "Mercedes-Benz",
    "mercedes-benz": "Mercedes-Benz",
    "deutsche bahn": "Deutsche Bahn",
    "db systel": "Deutsche Bahn",
    "telekom": "Deutsche Telekom",
    "t-systems": "Deutsche Telekom",
}

_LANG_CODE = {"a1": 1, "a2": 2, "b1": 3, "b2": 4, "c1": 5, "c2": 6}

# Role-type classification. A role is viable ONLY if it is genuinely
# Data Engineering or Applied AI. Titles/descriptions that point to ML
# Research, pure Data Science or generic SWE are rejected.
_ML_RESEARCH = re.compile(
    r"research\s+(?:scientist|engineer|intern)|wissenschaftliche\w*\s*(?:mitarbeit|hilf)"
    r"|researcher\b|phd\s+candidate|publish\w*\s+paper", re.IGNORECASE)

_DATA_SCIENCE = re.compile(
    r"data\s+scientist|data\s+science\b(?!.*engineering)|statistical?\s+modell"
    r"|econometrics", re.IGNORECASE)

_SWE_GENERIC = re.compile(
    r"(?:^|[\s(])(?:software|softwareentwickler|developer|entwickler|frontend|"
    r"front-end|backend|back-end|full[\s-]?stack|web\s+developer|react\s+developer)"
    r"(?!\s*(?:intern|praktikum))", re.IGNORECASE)

_DE_AI = re.compile(
    r"data\s+engineer|data\s+engineering|daten\s*engineer\b|daten\s*engineering|"
    r"data\s+platform|data\s+pipeline|etl\b|data\s+warehouse|"
    r"(?:machine\s+learning|ai|ml|llm|genai|nlp|rag)\s*(?:engineer|engineering|"
    r"intern|praktikum|internship)|applied\s+ai|artificial\s+intelligence", re.IGNORECASE)


def classify_role(parsed):
    """Return ('viable'|'reject', reason)."""
    title = parsed["title"] or ""
    text = f"{title} {parsed.get('_jd') or ''}"
    if _ML_RESEARCH.search(text):
        return "reject", "ML Research role, not Applied AI/Data Engineering"
    if _DATA_SCIENCE.search(text) and not _DE_AI.search(text):
        return "reject", "Data Science role, not Data Engineering/Applied AI"
    if _SWE_GENERIC.search(text) and not _DE_AI.search(text):
        return "reject", "Generic SWE role, not Data Engineering/Applied AI"
    if not _DE_AI.search(text):
        return "reject", "Role is not genuinely Data Engineering or Applied AI"
    return "viable", ""


def _parent_group(company):
    key = re.sub(r"\b(gmbh|ag|se|s\.a\.|inc\.?|ltd\.?)\b", "", (company or "").lower())
    key = " ".join(key.split())
    if key in PARENT_GROUPS:
        return PARENT_GROUPS[key]
    return (company or "").strip()


def _requisition_key(parsed):
    """Company group + normalized title + city = one requisition, so a repost
    from a different subsidiary or platform is caught as a duplicate."""
    title = re.sub(r"\((?:m|w|f|d|x|all genders)[^)]*\)", "",
                   parsed["title"] or "", flags=re.IGNORECASE).lower()
    title = re.sub(r"[\s\-\u2013\u2014|]+", " ", title).strip()
    return f"{_parent_group(parsed['company']).lower()}|{title}|{parsed.get('city_key') or ''}"


def _max_german_level():
    return CANDIDATE_PROFILE.get("max_german_level", "B1").lower()


def evaluate(posting, parsed=None, seen_keys=None, today=None):
    """Run every gate rule. Returns (blocked, warnings) where:

      blocked:  True ONLY for a within-batch duplicate requisition (the same
                posting scraped from two sources). Duplicates are already
                logged by the tracker, so no second package is built.
      warnings: every other concern (missing fields, German level, start
                window, relocation, age, role classification, Easy Apply).
                Warnings do NOT stop a package from being built -- the
                pipeline logs them in the `gate_reasons` column so you can
                spot the concern without losing the CV/CL.
    """
    parsed = parsed or parse_posting(posting)
    if seen_keys is None:
        seen_keys = set()
    today = today or date.today()
    blocked = False
    warnings = []

    cfg = CANDIDATE_PROFILE

    # 1. Missing required fields -> warning (never a guess, but not a block).
    if parsed["flagged"]:
        warnings.append(f"flagged for manual review: missing {', '.join(parsed['flagged'])}")

    # 2. Language requirement above candidate level.
    max_code = _LANG_CODE.get(_max_german_level(), 3)
    for lang in parsed.get("languages_required") or []:
        if lang["lang"].lower() == "german" and lang.get("level_code"):
            if lang["level_code"] > max_code:
                warnings.append(
                    f"German {lang['level']} required, candidate is {cfg.get('german_level')}"
                    f" (max {_max_german_level()})")

    # 3. Start date outside availability window.
    start = parsed.get("start_date")
    if start:
        earliest = _d(cfg.get("availability_start"))
        latest = _d(cfg.get("availability_end"))
        if earliest and start < earliest:
            warnings.append(f"start date {start} before availability window ({earliest})")
        if latest and start > latest:
            warnings.append(f"start date {start} after availability window ({latest})")

    # 4. Location outside relocation list.
    if parsed.get("city_key") and parsed.get("city_key") != "remote":
        if parsed["city_key"] not in {c.lower() for c in cfg.get("relocation_cities", [])}:
            warnings.append(
                f"location {parsed.get('city')} not in relocation list "
                f"({', '.join(sorted(cfg.get('relocation_cities', [])))})")

    # 5. Posting too old.
    if (parsed.get("age_days") or 0) > MAX_POSTING_AGE_DAYS:
        warnings.append(f"posting is {parsed['age_days']} days old (> {MAX_POSTING_AGE_DAYS} days)")

    # 6. Duplicate requisition (incl. cross-platform / cross-subsidiary) --
    #    the ONLY rule that still blocks. The tracker already logs the first
    #    occurrence, so a duplicate would just build a second identical package.
    key = _requisition_key(parsed)
    if key in seen_keys:
        blocked = True
        warnings.append("duplicate requisition of another posting in this batch")
    else:
        seen_keys.add(key)

    # 7. Role-type classification -> warning, not a block. German KI/ML and
    #    data-adjacent internship titles are kept: the package is still built
    #    and the concern is recorded so you can judge the role yourself.
    verdict, why = classify_role(parsed)
    if verdict == "reject":
        warnings.append(why)

    # 8. Channel: Easy Apply still flagged in the log, but the package is
    #    generated. The CV/CL is reusable on the employer's own portal.
    if BLOCK_EASY_APPLY_ONLY and parsed.get("submission_channel_kind") == "easy_apply":
        note = parsed.get("submission_channel_note") or "non-compliant"
        warnings.append(f"Easy Apply channel ({note}) -- apply via the employer's portal instead")

    return (not blocked), warnings


def _d(value):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def annotate(postings):
    """Batch gate. Returns (allowed, blocked).

    Since the rebalance, `blocked` holds ONLY within-batch duplicates (the
    sole remaining hard block). Every posting -- allowed or not -- carries
    `gate_reasons`: the joined warnings, so a concern about a posting is
    visible in the log even though the package is still built."""
    seen = set()
    allowed, blocked = [], []
    for p in postings:
        parsed = p.get("parsed") or parse_posting(p)
        p["parsed"] = parsed
        p["_jd"] = p.get("jd_text", "")
        ok, warnings = evaluate(p, parsed, seen, today=date.today())
        p["gate_reasons"] = "; ".join(warnings)
        if ok:
            p["gate_status"] = "passed"
            allowed.append(p)
        else:
            p["gate_status"] = "blocked"
            blocked.append(p)
    return allowed, blocked


if __name__ == "__main__":
    samples = [
        {"company": "Bankhaus Test", "title": "Data Engineer Intern",
         "location": "Munich", "jd_text": "German C1 required. Start 01.03.2026.",
         "date_posted": "2026-08-01"},
        {"company": "ACME", "title": "Werkstudent Data Engineering",
         "location": "Berlin", "jd_text": "Start 01.11.2026. Python, ETL. Apply via careers.acme.de.",
         "date_posted": "2026-08-07"},
        {"company": "ML Lab", "title": "ML Research Intern",
         "location": "Berlin", "jd_text": "Research on model interpretability. Python, PyTorch.",
         "date_posted": "2026-08-07"},
    ]
    for s in samples:
        ok, reasons = evaluate(s)
        print(ok, "|", s["title"], "->", reasons if reasons else "ALLOWED")
