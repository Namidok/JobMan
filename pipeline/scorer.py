"""
Fit scoring (remediation brief R4).

Scores each surviving posting on:
  - required-technology overlap with the fact bank (the candidate must claim
    the technology in the bank to get the point; technologies the candidate
    has but is migrating away from -- e.g. Streamlit -- do not count)
  - domain proximity between the employer's business and the candidate's most
    relevant project
  - seniority fit (internship vs the candidate's profile)

The result is a transparent 0-100 fit score plus human-readable reasoning.
main.py refuses to generate documents below config.MIN_FIT_SCORE.

This replaces the old `overlap_pct` keyword-overlap heuristic, which rewarded
generic words ("python", "sql") and never distinguished a real fit from a
bad one -- the reason 10-25 low-value applications were generated per day.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import CANDIDATE_PROFILE, MIN_FIT_SCORE
from fact_bank import (
    has_technology, fact_bank_technologies, PROJECT_ACHIEVEMENTS,
    FAMILY_TO_PROJECT,
)
from pipeline.jd_parser import parse_posting

# Technologies the candidate used but should not be credited for (the CV's
# only mention of Streamlit is migrating away from it).
WEAK_TECHNOLOGIES = {"Streamlit"}

DOMAIN_WEIGHTS = {
    "finance": {"creditlens": 1.0, "skillsync": 0.3, "covercraft": 0.2,
                "stadtanalyse": 0.1, "pipeline_guardian": 0.4},
    "logistics": {"stadtanalyse": 1.0, "pipeline_guardian": 0.5,
                  "creditlens": 0.2, "skillsync": 0.1, "covercraft": 0.1},
    "consumer": {"covercraft": 1.0, "skillsync": 0.9, "creditlens": 0.5,
                 "stadtanalyse": 0.3, "pipeline_guardian": 0.3},
    "productivity": {"skillsync": 1.0, "covercraft": 0.9, "creditlens": 0.4,
                     "stadtanalyse": 0.3, "pipeline_guardian": 0.4},
    "platform": {"pipeline_guardian": 1.0, "stadtanalyse": 0.8,
                 "creditlens": 0.4, "skillsync": 0.3, "covercraft": 0.2},
}

TECH_WEIGHT = 0.55
DOMAIN_WEIGHT = 0.35
SENIORITY_WEIGHT = 0.10

# Every technology in the fact bank the candidate can actually be credited
# for (used to check whether a JD-required technology is a claimed skill).
_CLAIMED = fact_bank_technologies() - WEAK_TECHNOLOGIES


def technology_overlap(parsed):
    """Fraction of JD-required technologies that are claimed in the fact bank.

    A required tech that is not in the bank is a gap; the caller logs it.
    Returns (overlap_frac, matched, missing).
    """
    required = parsed.get("required_technologies") or []
    if not required:
        # Fall back to anything the JD mentions that the bank knows.
        required = parsed.get("technologies_mentioned") or []
    if not required:
        return 1.0, [], []

    matched = []
    missing = []
    for tech in required:
        if tech in WEAK_TECHNOLOGIES:
            continue                       # used but not a selling point
        if has_technology(tech):
            matched.append(tech)
        else:
            missing.append(tech)
    return (len(matched) / max(len(required), 1)), matched, missing


def domain_proximity(parsed):
    """Best project-domain match for the employer's business."""
    domain = parsed.get("domain") or "general"
    weights = DOMAIN_WEIGHTS.get(domain, {})
    if not weights:
        weights = {FAMILY_TO_PROJECT.get(domain, "creditlens"): 0.8,
                   "creditlens": 0.5}
    best = max(weights.items(), key=lambda kv: kv[1])
    return best[0], best[1]


def seniority_fit(parsed):
    """Internship-level roles are a structural fit for a student candidate."""
    text = f"{parsed['title'] or ''} {parsed.get('_jd') or ''}".lower()
    internship = any(t in text for t in
                     ["intern", "internship", "praktikum", "praktikant",
                      "werkstudent", "working student", "pflichtpraktikum"])
    return 1.0 if internship else 0.7


def score_posting(posting, parsed=None):
    """Return a dict with fit_score, reasoning, matched, gaps, and the
    technology gaps to log. `parsed` may be supplied to avoid re-parsing."""
    parsed = parsed or parse_posting(posting)
    parsed["_jd"] = posting.get("jd_text", "")

    overlap, matched, missing_tech = technology_overlap(parsed)
    lead_project, dom_score = domain_proximity(parsed)
    seniority = seniority_fit(parsed)

    fit_score = round(
        100 * (TECH_WEIGHT * overlap + DOMAIN_WEIGHT * dom_score
               + SENIORITY_WEIGHT * seniority), 1)

    reasons = []
    required_list = parsed.get("required_technologies")
    if required_list:
        reasons.append(f"required-tech overlap {len(matched)}/{len(required_list)}")
    else:
        reasons.append("no explicit required tech list in the JD")
    if missing_tech:
        reasons.append(f"lacks: {', '.join(missing_tech)}")
    reasons.append(f"domain proximity to '{lead_project}' ({dom_score:.2f})")
    reasons.append(f"seniority fit {'internship' if seniority == 1.0 else 'general'}")
    if fit_score < MIN_FIT_SCORE:
        reasons.append(f"below configured floor of {MIN_FIT_SCORE}")

    profile = _profile_for(parsed)
    return {
        "fit_score": fit_score,
        "below_floor": fit_score < MIN_FIT_SCORE,
        "min_fit_score": MIN_FIT_SCORE,
        "reasoning": "; ".join(reasons),
        "matched": matched,
        "technology_gaps": parsed.get("technology_gaps") or [],
        "lead_project": lead_project,
        "profile": profile,
    }


def _profile_for(parsed):
    """Pick the CV summary framing: data engineering vs AI/ML, from the JD."""
    text = f"{parsed['title'] or ''} {parsed.get('_jd') or ''}".lower()
    de_hits = sum(1 for t in ["data engineer", "data engineering", "etl",
                              "data pipeline", "warehouse", "daten"] if t in text)
    ai_hits = sum(1 for t in ["machine learning", "ml ", " ai", "llm", "nlp",
                              "genai", "deep learning", "rag"] if t in text)
    return "data_engineer" if de_hits >= ai_hits else "ai_ml"


if __name__ == "__main__":
    posting = {
        "company": "PIMCO Prime Real Estate",
        "title": "Intern in Software and Data Engineering (m/f/d)",
        "location": "Munich, Germany",
        "apply_url": "https://www.linkedin.com/jobs/view/123",
        "jd_text": ("Requirements: Python, RAG/LLM solutions using vector "
                    "databases, Spark. Portfolio and credit analytics. "
                    "Internship for 6 months."),
    }
    result = score_posting(posting)
    for k, v in result.items():
        print(f"{k}: {v}")
