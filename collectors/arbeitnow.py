"""
Collects postings from Arbeitnow's free public job-board API.
Always filtered to the last 24 hours.

FIX: this previously only filtered by domain keyword, with NO check for
internship status -- meaning it could silently include full-time roles.
"""

import requests
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pipeline.date_filter import filter_last_24h
from pipeline.relevance_filter import filter_relevant

API_URL = "https://www.arbeitnow.com/api/job-board-api"

KEYWORDS = ["data engineer", "machine learning", "ai engineer", "nlp", "data scientist",
            "artificial intelligence", "genai", "llm", "praktikum", "werkstudent", "intern"]


def fetch_postings(keywords=None, germany_only=True):
    keywords = keywords or KEYWORDS
    results = []
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
            if germany_only and "germany" not in combined:
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

    before_relevance = len(results)
    results, stats = filter_relevant(results, require_internship_title=True)
    print(f"Arbeitnow: {before_relevance} keyword matches, "
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