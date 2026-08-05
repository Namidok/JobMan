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

# ---------------------------------------------------------------------------
# ROLE SCOPE
#
# "core"     = AI/ML/Data only. Smallest pool, best on-paper fit.
# "extended" = core + software engineering (backend, full-stack, web, QA).
#              You have 3 years of production full-stack experience -- this is
#              your largest genuinely-qualified pool, not a compromise.
# "broad"    = extended + general IT/product/consulting-tech. Widest net;
#              expect more roles where you are a weaker fit.
#
# Set JOBMAN_SCOPE=core|extended|broad, or pass scope= explicitly.
# ---------------------------------------------------------------------------

CORE_DOMAIN_SIGNALS = [
    "data", "ai", "artificial intelligence", "machine learning", "ml",
    "nlp", "analytics", "cloud", "ki", "data science", "data engineering",
    "genai", "llm", "deep learning",
]

SWE_DOMAIN_SIGNALS = [
    "software", "softwareentwicklung", "developer", "entwickler",
    "engineering", "engineer", "backend", "back-end", "frontend", "front-end",
    "full stack", "fullstack", "full-stack", "web", "python", "javascript",
    "api", "platform", "devops", "qa", "test", "automation", "informatik",
]

BROAD_DOMAIN_SIGNALS = [
    "it", "tech", "technology", "digital", "product", "technical",
    "computer science", "systems", "digitalisierung",
]

SCOPES = {
    "core": CORE_DOMAIN_SIGNALS,
    "extended": CORE_DOMAIN_SIGNALS + SWE_DOMAIN_SIGNALS,
    "broad": CORE_DOMAIN_SIGNALS + SWE_DOMAIN_SIGNALS + BROAD_DOMAIN_SIGNALS,
}

TITLE_DOMAIN_SIGNALS = CORE_DOMAIN_SIGNALS  # back-compat

JD_TECHNICAL_SIGNALS = [
    "python", "sql", "etl", "pandas", "pytorch", "tensorflow", "llm",
    "genai", "generative ai", "rag", "deep learning", "data pipeline",
    "machine learning model", "nlp", "neural network", "spark", "faiss",
    "chromadb", "embeddings",
    # Things you actually build with, which a software-engineering JD will
    # mention even when the title says nothing about AI or data.
    "react", "fastapi", "flask", "django", "node.js", "rest api", "docker",
    "ci/cd", "git", "postgresql", "javascript", "typescript", "aws",
    "microservices", "backend", "frontend",
]

JD_TECHNICAL_HIT_THRESHOLD = 3


def _word_match(signal: str, text: str) -> bool:
    pattern = r"\b" + re.escape(signal) + r"\b"
    return re.search(pattern, text, re.IGNORECASE) is not None


def is_internship_title(title: str) -> bool:
    t = title or ""
    return any(_word_match(sig, t) for sig in INTERNSHIP_TITLE_SIGNALS)


def _active_scope(scope=None):
    import os
    s = (scope or os.environ.get("JOBMAN_SCOPE") or "extended").lower()
    return s if s in SCOPES else "extended"


def is_domain_relevant(title: str, jd_text: str, scope=None) -> bool:
    signals = SCOPES[_active_scope(scope)]
    t = title or ""
    if any(_word_match(sig, t) for sig in signals):
        return True
    jd = jd_text or ""
    hits = sum(1 for sig in JD_TECHNICAL_SIGNALS if _word_match(sig, jd))
    return hits >= JD_TECHNICAL_HIT_THRESHOLD


def filter_relevant(postings, require_internship_title=True, scope=None):
    stats = {"total": len(postings), "scope": _active_scope(scope)}

    if require_internship_title:
        postings = [p for p in postings if is_internship_title(p.get("title", ""))]
    stats["after_internship_filter"] = len(postings)

    postings = [p for p in postings
                if is_domain_relevant(p.get("title", ""), p.get("jd_text", ""), scope)]
    stats["after_domain_filter"] = len(postings)

    return postings, stats