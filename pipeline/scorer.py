"""
Scores a job description against the master resume's real skills.

IMPORTANT HONESTY NOTE:
There is no universal "ATS score" -- every ATS (Workday, SuccessFactors,
Greenhouse, etc.) scores differently and none expose their real algorithm.
This module computes a transparent, explainable keyword-overlap percentage
instead. Treat it as a directional signal, not a guarantee of any real
system's score.

BUG FIX (the big one): this module used naive substring matching
(`if kw in jd_lower`), which produced silent false positives:
    "git"  matched inside "digital"
    "rag"  matched inside "Leveraging" / "storage" / "average"
    "iam"  matched inside "Miami"
    "sql"  matched inside "postgresql"
Those phantom matches then (a) inflated overlap_pct, (b) reordered resume
skill categories so Cloud & Infra outranked AI/ML on AI roles, and (c) got
printed verbatim into cover letters. relevance_filter.py already had the
word-boundary fix; it now lives in one place and both modules use it.
"""

import re
from collections import OrderedDict

from config import SKILLS, VARIANTS, KNOWN_GAPS, KEYWORD_DISPLAY, NEVER_HIGHLIGHT
from pipeline.relevance_filter import _word_match


def _count_occurrences(keyword: str, text: str) -> int:
    return len(re.findall(r"\b" + re.escape(keyword) + r"\b", text, re.IGNORECASE))


def _display(keyword: str) -> str:
    return KEYWORD_DISPLAY.get(keyword, keyword.title())


def _rank_highlights(matched, jd_text, job_title):
    """Order matched keywords by how central they are to THIS posting, then
    map to display names and drop duplicates + non-signalling terms.

    Replaces the old `sorted(matched)[:6]`, which was alphabetical -- that is
    why letters opened with "aws, english, german, git".
    """
    scored = []
    for kw in matched:
        if kw in NEVER_HIGHLIGHT:
            continue
        score = _count_occurrences(kw, jd_text) + (5 * _count_occurrences(kw, job_title))
        scored.append((score, kw))

    scored.sort(key=lambda pair: (-pair[0], pair[1]))

    # Dedupe on the DISPLAY name so postgres/postgresql don't both appear.
    seen = OrderedDict()
    for _, kw in scored:
        seen.setdefault(_display(kw), None)
    return list(seen.keys())


def score_posting(jd_text: str, job_title: str = ""):
    """
    Returns:
      {
        "overlap_pct": float,      # % of resume keywords genuinely in the JD
        "matched": [...],          # raw keywords, for resume reordering
        "highlights": [...],       # display-ready, relevance-ranked, for the letter
        "gaps": [...],             # KNOWN_GAPS the JD asks for that you lack
        "best_variant": "data_engineer" | "ai_ml" | "nlp",
        "variant_scores": {...}
      }
    """
    jd_text = jd_text or ""
    job_title = job_title or ""
    title_lower = job_title.lower()

    all_resume_keywords = set()
    for cat in SKILLS.values():
        all_resume_keywords.update(cat["keywords"])

    # Word-boundary matching -- the fix.
    matched = sorted({kw for kw in all_resume_keywords if _word_match(kw, jd_text)})
    overlap_pct = round(100 * len(matched) / max(len(all_resume_keywords), 1), 1)

    gaps = sorted({kw for kw in KNOWN_GAPS if _word_match(kw, jd_text)})

    variant_scores = {}
    for vname, vconf in VARIANTS.items():
        body_hits = sum(1 for kw in vconf["keywords"] if _word_match(kw, jd_text))
        title_hits = sum(3 for kw in vconf["keywords"] if _word_match(kw, job_title))
        variant_scores[vname] = body_hits + title_hits

    # Direct title-phrase overrides beat keyword scoring entirely.
    if "data engineer" in title_lower or "data engineering" in title_lower:
        best_variant = "data_engineer"
    elif _word_match("nlp", job_title):
        best_variant = "nlp"
    elif any(t in title_lower for t in ["ai engineer", "ml engineer", "machine learning",
                                        "genai", "llm engineer", "ai scientist",
                                        "data scientist"]):
        best_variant = "ai_ml"
    else:
        best_variant = max(variant_scores, key=variant_scores.get)
        if variant_scores[best_variant] == 0:
            best_variant = "ai_ml"

    return {
        "overlap_pct": overlap_pct,
        "matched": matched,
        "highlights": _rank_highlights(matched, jd_text, job_title),
        "gaps": gaps,
        "best_variant": best_variant,
        "variant_scores": variant_scores,
    }