"""
Collects LinkedIn postings via the Apify Actor `worldunboxer/rapid-linkedin-scraper`.
Scrapes WITHOUT cookies/login -- not tied to your personal LinkedIn account.
Requires: export APIFY_API_TOKEN="your_token_here"
"""

import os
import requests
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pipeline.date_filter import filter_last_24h
from pipeline.relevance_filter import filter_relevant

ACTOR = "worldunboxer/rapid-linkedin-scraper"
BASE_URL = f"https://api.apify.com/v2/acts/{ACTOR.replace('/', '~')}/run-sync-get-dataset-items"

DEFAULT_TITLES = ["Data Engineer Praktikum", "Machine Learning Praktikum",
                   "Werkstudent Data Engineering", "Werkstudent Machine Learning",
                   "AI Engineer Intern", "Data Science Praktikum", "NLP Praktikum",
                   "AI Praktikum", "KI Praktikum", "Werkstudent AI",
                   "Werkstudent Künstliche Intelligenz", "Artificial Intelligence Intern"]


def fetch_postings(cities=None, job_titles=None, max_results=50):
    token = os.environ.get("APIFY_API_TOKEN")
    if not token:
        raise RuntimeError(
            "APIFY_API_TOKEN not set. Create a free Apify account, get your token from "
            "https://console.apify.com/account/integrations, then run:\n"
            "  export APIFY_API_TOKEN='your_token_here'"
        )

    job_titles = job_titles or DEFAULT_TITLES
    cities = cities or ["Germany"]

    results = []
    for title in job_titles:
        payload = {
            "job_title": title,
            "cities": cities,
            "jobs_entries": max_results,
            "posted_within": "Past 24 hours",
        }
        resp = requests.post(BASE_URL, params={"token": token}, json=payload, timeout=120)
        resp.raise_for_status()
        items = resp.json()

        for item in items:
            results.append({
                "source": "linkedin",
                "company": item.get("company_name", ""),
                "title": item.get("job_title", ""),
                "location": item.get("location", ""),
                "date_posted": item.get("time_posted", ""),
                "jd_text": item.get("job_description", ""),
                "apply_url": item.get("apply_url", ""),
            })

    results, stats = filter_relevant(results, require_internship_title=True)
    print(f"LinkedIn: {stats['total']} returned by Actor, "
          f"{stats['after_internship_filter']} are internships, "
          f"{stats['after_domain_filter']} are also AI/Data/ML-relevant")

    kept, dropped = filter_last_24h(results, date_field="date_posted")
    print(f"LinkedIn: {len(kept)} confirmed within last 24h "
          f"({dropped} dropped as older or unparseable date)")
    return kept


if __name__ == "__main__":
    postings = fetch_postings()
    print(f"Found {len(postings)} matching postings")
    for p in postings[:10]:
        print("-", p["company"], "|", p["title"], "|", p["date_posted"])