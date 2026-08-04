"""
Collects postings from Arbeitnow's free public job-board API.
Always filtered to the last 24 hours.

FIX: this previously only filtered by domain keyword, with NO check for
internship status -- meaning it could silently include full-time roles.
"""

import re
import requests
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pipeline.date_filter import filter_last_24h
from pipeline.relevance_filter import filter_relevant

API_URL = "https://www.arbeitnow.com/api/job-board-api"

KEYWORDS = ["data engineer", "machine learning", "ai engineer", "nlp", "data scientist",
            "artificial intelligence", "genai", "llm", "praktikum", "werkstudent", "intern"]


# ---------------------------------------------------------------------------
# GERMANY FILTER
#
# BUG FIX: this used to be `if "germany" not in (title + description)`.
# The `location` field was fetched and never checked, so a Berlin posting
# whose description never literally says "Germany" -- which is most of them
# -- was silently dropped before it was ever scored. That was starving the
# whole pipeline of volume.
#
# Arbeitnow is a DACH/EU board, so it is not enough to look for German
# cities: Vienna and Zurich appear too and must be excluded explicitly.
# ---------------------------------------------------------------------------

GERMAN_CITIES = {
    "berlin", "munich", "muenchen", "munchen", "hamburg", "frankfurt", "cologne",
    "koeln", "koln", "stuttgart", "dusseldorf", "duesseldorf", "dortmund", "essen",
    "leipzig", "bremen", "dresden", "hannover", "hanover", "nuremberg", "nurnberg",
    "nuernberg", "duisburg", "bochum", "wuppertal", "bielefeld", "bonn", "munster",
    "muenster", "karlsruhe", "mannheim", "augsburg", "wiesbaden", "braunschweig",
    "kiel", "chemnitz", "aachen", "halle", "magdeburg", "freiburg", "krefeld",
    "mainz", "lubeck", "luebeck", "erfurt", "rostock", "kassel", "potsdam",
    "saarbrucken", "saarbruecken", "heidelberg", "darmstadt", "regensburg",
    "ingolstadt", "wurzburg", "wuerzburg", "ulm", "jena", "osnabruck", "osnabrueck",
    "heilbronn", "wolfsburg", "gottingen", "goettingen", "koblenz", "trier",
    "paderborn", "siegen", "hildesheim", "tubingen", "tuebingen", "konstanz",
    "bamberg", "walldorf", "eschborn", "leverkusen", "ludwigshafen",
}

# Same board carries Austria/Switzerland/EU-remote. Reject these outright.
NON_GERMAN_MARKERS = {
    "austria", "osterreich", "oesterreich", "vienna", "wien", "graz", "linz", "salzburg",
    "switzerland", "schweiz", "zurich", "zuerich", "basel", "bern", "geneva", "lausanne",
    "netherlands", "amsterdam", "rotterdam", "utrecht", "eindhoven", "hague",
    "poland", "warsaw", "krakow", "wroclaw", "spain", "madrid", "barcelona", "valencia",
    "france", "paris", "lyon", "toulouse", "united kingdom", "london", "manchester",
    "ireland", "dublin", "portugal", "lisbon", "porto", "italy", "milan", "rome",
    "belgium", "brussels", "denmark", "copenhagen", "sweden", "stockholm",
    "norway", "oslo", "finland", "helsinki", "czech", "prague", "hungary", "budapest",
    "romania", "bucharest", "bulgaria", "sofia", "greece", "athens", "estonia", "tallinn",
    "united states", "usa", "canada", "india", "singapore",
}


def _norm(text):
    """Lowercase and strip umlauts so 'München' matches 'muenchen'/'munchen'."""
    t = (text or "").lower()
    for a, b in [("\u00e4", "a"), ("\u00f6", "o"), ("\u00fc", "u"), ("\u00df", "ss")]:
        t = t.replace(a, b)
    return t


def _has_word(word, text):
    return re.search(r"\b" + re.escape(word) + r"\b", text) is not None


def is_germany(location, title="", description=""):
    """True when the posting is plausibly in Germany.

    Order matters: an explicit non-German marker in `location` wins, so a
    'Vienna, Austria' role is rejected even if the description name-drops
    Germany somewhere.
    """
    loc = _norm(location)
    text = _norm(f"{title} {description}")

    if any(_has_word(m, loc) for m in NON_GERMAN_MARKERS):
        return False
    if _has_word("germany", loc) or _has_word("deutschland", loc):
        return True
    if any(_has_word(c, loc) for c in GERMAN_CITIES):
        return True

    # Remote roles often carry no city -- fall back to the body text, but only
    # if nothing there points at another country.
    if any(_has_word(m, text) for m in NON_GERMAN_MARKERS):
        return False
    if _has_word("germany", text) or _has_word("deutschland", text):
        return True
    if any(_has_word(c, text) for c in GERMAN_CITIES):
        return True
    return False


def fetch_postings(keywords=None, germany_only=True):
    keywords = keywords or KEYWORDS
    results = []
    keyword_hits = 0
    non_german = 0
    page = 1
    while True:
        resp = requests.get(API_URL, params={"page": page}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("data", [])
        if not jobs:
            break

        for job in jobs:
            title = (job.get("title") or "")
            desc = (job.get("description") or "")
            location = (job.get("location") or "")
            combined = f"{title} {desc}".lower()

            if not any(kw in combined for kw in keywords):
                continue
            keyword_hits += 1
            if germany_only and not is_germany(location, title, desc):
                non_german += 1
                continue

            results.append({
                "source": "arbeitnow",
                "company": job.get("company_name", ""),
                "title": title,
                "location": location,
                "date_posted": job.get("created_at", ""),
                "jd_text": desc,
                "apply_url": job.get("url", ""),
            })

        page += 1
        if page > 5:
            break

    if germany_only:
        print(f"Arbeitnow: {keyword_hits} keyword matches, "
              f"{non_german} dropped as outside Germany, {len(results)} remain")

    before_relevance = len(results)
    results, stats = filter_relevant(results, require_internship_title=True)
    print(f"Arbeitnow: {before_relevance} in Germany, "
          f"{stats['after_internship_filter']} are internships, "
          f"{stats['after_domain_filter']} are also AI/Data/ML-relevant")

    kept, dropped = filter_last_24h(results, date_field="date_posted")
    print(f"Arbeitnow: {len(kept)} confirmed within last 24h "
          f"({dropped} dropped as older or unparseable date)")
    return kept


if __name__ == "__main__":
    postings = fetch_postings()
    print(f"Found {len(postings)} matching postings")
    for p in postings[:5]:
        print("-", p["company"], "|", p["title"])