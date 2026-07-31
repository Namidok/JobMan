"""
Shared relevance filtering, used by ALL THREE collectors (Arbeitnow, LinkedIn,
Indeed) so the internship + domain rules stay identical everywhere.

BUG FIX: previously used naive substring matching, which caused false
positives -- "ai" matched inside "trainee", "ml" matched inside "html",
"intern" matched inside "international"/"internal", "rag" matched inside
"storage". Fixed by switching to word-boundary regex matching.
"""

import re

INTERNSHIP_TITLE_SIGNALS = [
    "intern", "internship", "praktikum", "praktikant", "werkstudent",
    "working student", "trainee", "pflichtpraktikum",
]

TITLE_DOMAIN_SIGNALS = [
    "data", "ai", "artificial intelligence", "machine learning", "ml",
    "nlp", "analytics", "cloud", "ki",
]

JD_TECHNICAL_SIGNALS = [
    "python", "sql", "etl", "pandas", "pytorch", "tensorflow", "llm",
    "genai", "generative ai", "rag", "deep learning", "data pipeline",
    "machine learning model", "nlp", "neural network", "spark", "faiss",
    "chromadb", "embeddings",
]

JD_TECHNICAL_HIT_THRESHOLD = 3


def _word_match(signal: str, text: str) -> bool:
    pattern = r"\b" + re.escape(signal) + r"\b"
    return re.search(pattern, text, re.IGNORECASE) is not None


def is_internship_title(title: str) -> bool:
    t = title or ""
    return any(_word_match(sig, t) for sig in INTERNSHIP_TITLE_SIGNALS)


def is_domain_relevant(title: str, jd_text: str) -> bool:
    t = title or ""
    if any(_word_match(sig, t) for sig in TITLE_DOMAIN_SIGNALS):
        return True
    jd = jd_text or ""
    hits = sum(1 for sig in JD_TECHNICAL_SIGNALS if _word_match(sig, jd))
    return hits >= JD_TECHNICAL_HIT_THRESHOLD


def filter_relevant(postings, require_internship_title=True):
    stats = {"total": len(postings)}

    if require_internship_title:
        postings = [p for p in postings if is_internship_title(p.get("title", ""))]
    stats["after_internship_filter"] = len(postings)

    postings = [p for p in postings if is_domain_relevant(p.get("title", ""), p.get("jd_text", ""))]
    stats["after_domain_filter"] = len(postings)

    return postings, stats