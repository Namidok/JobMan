"""
Indeed postings can't be pulled from your own script -- ask Claude in chat
to pull fresh internship postings and save as JSON to data/raw/indeed.json.

SAFETY NET: runs everything through the same shared internship + domain
filter as the other two sources, so bad data from a chat pull doesn't
silently make it into your applications.
"""

import json
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pipeline.relevance_filter import filter_relevant


def fetch_postings(json_path="data/raw/indeed.json"):
    if not os.path.exists(json_path):
        print(f"No Indeed data file found at {json_path}.")
        print("Ask Claude in chat to pull fresh Indeed postings and save them there.")
        return []

    with open(json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    results = []
    for item in raw:
        results.append({
            "source": "indeed",
            "company": item.get("company", ""),
            "title": item.get("title", ""),
            "location": item.get("location", ""),
            "date_posted": item.get("date_posted", ""),
            "jd_text": item.get("jd_text", ""),
            "apply_url": item.get("apply_url", ""),
        })

    before_relevance = len(results)
    results, stats = filter_relevant(results, require_internship_title=True)
    print(f"Indeed: {before_relevance} loaded, "
          f"{stats['after_internship_filter']} are internships, "
          f"{stats['after_domain_filter']} are also AI/Data/ML-relevant")

    return results


if __name__ == "__main__":
    postings = fetch_postings()
    print(f"Loaded {len(postings)} Indeed postings")