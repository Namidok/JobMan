"""
Scores a job description against the master resume's real skills.

IMPORTANT HONESTY NOTE:
There is no universal "ATS score" -- every ATS (Workday, SuccessFactors,
Greenhouse, etc.) scores differently and none expose their real algorithm.
This module computes a transparent, explainable keyword-overlap percentage
instead. Treat it as a directional signal, not a guarantee of any real
system's score.
"""

import re
from config import SKILLS, VARIANTS, KNOWN_GAPS


def _tokenize(text: str):
    return set(re.findall(r"[a-zA-Z0-9\+\#\.\-/]+", text.lower()))


def score_posting(jd_text: str, job_title: str = ""):
    """
    Returns:
      {
        "overlap_pct": float,          # % of resume keywords found in the JD
        "matched": [...],              # resume keywords found in the JD
        "gaps": [...],                 # KNOWN_GAPS keywords found in the JD that
                                        # are genuinely absent from the resume
        "best_variant": "data_engineer" | "ai_ml" | "nlp",
        "variant_scores": {...}        # raw match count per variant, for transparency
      }
    """
    jd_lower = jd_text.lower()
    title_lower = job_title.lower()

    # 1. Which resume-wide skill keywords appear in this JD?
    all_resume_keywords = set()
    for cat in SKILLS.values():
        all_resume_keywords.update(cat["keywords"])

    matched = sorted({kw for kw in all_resume_keywords if kw in jd_lower})
    overlap_pct = round(100 * len(matched) / max(len(all_resume_keywords), 1), 1)

    # 2. Which known gaps (things genuinely NOT on the resume) does this JD ask for?
    gaps = sorted({kw for kw in KNOWN_GAPS if kw in jd_lower})

    # 3. Which variant fits best? Count keyword hits per variant's own keyword list
    #    in the JD body, PLUS a stronger weight for the title itself (titles are a
    #    more reliable signal than body text, which is often generic/templated).
    variant_scores = {}
    for vname, vconf in VARIANTS.items():
        body_hits = sum(1 for kw in vconf["keywords"] if kw in jd_lower)
        title_hits = sum(3 for kw in vconf["keywords"] if kw in title_lower)
        variant_scores[vname] = body_hits + title_hits

    # Direct title-phrase overrides beat keyword scoring entirely -- if the
    # posting is literally titled "Data Engineer", trust that over sparse JD text.
    if "data engineer" in title_lower or "data engineering" in title_lower:
        best_variant = "data_engineer"
    elif "nlp" in title_lower:
        best_variant = "nlp"
    elif any(t in title_lower for t in ["ai engineer", "ml engineer", "machine learning",
                                         "genai", "llm engineer"]):
        best_variant = "ai_ml"
    else:
        best_variant = max(variant_scores, key=variant_scores.get)
        if variant_scores[best_variant] == 0:
            best_variant = "ai_ml"  # broadest, safest default

    return {
        "overlap_pct": overlap_pct,
        "matched": matched,
        "gaps": gaps,
        "best_variant": best_variant,
        "variant_scores": variant_scores,
    }
