"""
Hard-blocker filter.

A posting can be a perfect keyword match and still be unwinnable: German C1
when you're A2, PhD-required, "minimum 5 years experience" on an internship
req. Every one of those applications costs you time you don't have.

This module does NOT silently delete them -- it labels them, so you can
decide. Default behaviour in main.py is to log them with the blocker named
in the Excel sheet and skip document generation.
"""

import re

from config import BLOCKER_PATTERNS

# Human-readable reason per pattern, keyed by the pattern's index.
_REASONS = {
    0: "requires C1 German/language level",
    1: "requires C2 German/language level",
    2: "requires 'verhandlungssicher' German",
    3: "requires fluent ('flie\u00dfend') German",
    4: "requires near-native German",
    5: "requires native German",
    6: "requires fluent German",
    7: "requires German C1",
    8: "requires German C2",
    9: "requires a PhD",
    10: "requires 5+ years of experience",
}

_COMPILED = [re.compile(p, re.IGNORECASE) for p in BLOCKER_PATTERNS]


def find_blockers(jd_text: str, job_title: str = ""):
    """Return a list of human-readable blocker reasons found in this posting."""
    haystack = f"{job_title}\n{jd_text or ''}"
    reasons = []
    for i, rx in enumerate(_COMPILED):
        if rx.search(haystack):
            reason = _REASONS.get(i, f"matched blocker pattern {i}")
            if reason not in reasons:
                reasons.append(reason)
    return reasons


def annotate(postings):
    """Attach a `blockers` string to each posting. Returns (clear, blocked)."""
    clear, blocked = [], []
    for p in postings:
        reasons = find_blockers(p.get("jd_text", ""), p.get("title", ""))
        p["blockers"] = "; ".join(reasons)
        (blocked if reasons else clear).append(p)
    return clear, blocked