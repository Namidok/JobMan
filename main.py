"""
Main entry point. Run this yourself, on your own machine:

    python main.py --sources arbeitnow
    python main.py --sources arbeitnow linkedin indeed   (needs APIFY_API_TOKEN set)

What it does, in order:
  1. Collect postings from the sources you choose -- ALWAYS filtered to the
     last 24 hours only, across every source.
  2. Normalize + dedupe against data/postings.xlsx (safe to re-run daily)
  3. Score each NEW posting (honest keyword-overlap, not a fake "ATS score")
  4. Pick the best-fit resume variant (data_engineer / ai_ml / nlp)
  5. Generate a tailored resume + cover letter, convert both to PDF, delete
     the intermediate docx
  6. Save into applications/Company_Role_Date/ as:
       SrikarKodi.pdf        <- resume
       Srikar_Kodi.pdf       <- cover letter
  7. Log everything to data/postings.xlsx with a real clickable hyperlink

You still click "Apply" yourself -- this tool prepares, it never submits.

REQUIRES LibreOffice installed for PDF conversion.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

from collectors import arbeitnow, indeed_loader
from pipeline import scorer, excel_log, date_filter
from resume_builder.build import build_resume
from resume_builder.cover_letter import build_cover_letter
from resume_builder.pdf_convert import convert_to_pdf

XLSX_PATH = os.path.join(os.path.dirname(__file__), "data", "postings.xlsx")
APPLICATIONS_DIR = os.path.join(os.path.dirname(__file__), "applications")

RESUME_FILENAME = "SrikarKodi"
COVER_LETTER_FILENAME = "Srikar_Kodi"


def safe_folder_name(company, title, date):
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", f"{company}_{title}").strip("_")
    return f"{slug}_{date}"


def run(sources):
    all_postings = []

    if "arbeitnow" in sources:
        print("Collecting from Arbeitnow (last 24h only)...")
        try:
            all_postings += arbeitnow.fetch_postings()
        except Exception as e:
            print(f"WARNING: Arbeitnow collection failed, skipping this source: {e}")

    if "linkedin" in sources:
        print("Collecting from LinkedIn via Apify (last 24h only)...")
        try:
            from collectors import linkedin_apify
            all_postings += linkedin_apify.fetch_postings()
        except Exception as e:
            print(f"WARNING: LinkedIn collection failed, skipping this source: {e}")

    if "indeed" in sources:
        print("Loading Indeed postings from data/raw/indeed.json...")
        try:
            raw_indeed = indeed_loader.fetch_postings()
            kept, dropped = date_filter.filter_last_24h(raw_indeed, date_field="date_posted")
            print(f"Indeed: {len(raw_indeed)} loaded, {len(kept)} within last 24h "
                  f"({dropped} dropped as older or unparseable date)")
            all_postings += kept
        except Exception as e:
            print(f"WARNING: Indeed loading failed, skipping this source: {e}")

    print(f"\nCollected {len(all_postings)} raw postings (last 24h) across selected sources.")

    for p in all_postings:
        result = scorer.score_posting(p.get("jd_text", ""), p.get("title", ""))
        p["overlap_pct"] = result["overlap_pct"]
        p["best_variant"] = result["best_variant"]
        p["gaps"] = ", ".join(result["gaps"]) if result["gaps"] else ""

    new_rows = excel_log.append_postings(XLSX_PATH, all_postings)
    print(f"{len(new_rows)} NEW postings added to {XLSX_PATH} (duplicates skipped).\n")

    from datetime import date
    today = date.today().isoformat()

    for row in new_rows:
        folder_name = safe_folder_name(row["company"], row["title"], today)
        folder_path = os.path.join(APPLICATIONS_DIR, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        variant = row["best_variant"] or "ai_ml"

        resume_docx = os.path.join(folder_path, f"{RESUME_FILENAME}.docx")
        cover_docx = os.path.join(folder_path, f"{COVER_LETTER_FILENAME}.docx")

        build_resume(variant, resume_docx)
        build_cover_letter(variant, row["company"], row["title"], cover_docx)

        try:
            resume_pdf = convert_to_pdf(resume_docx, folder_path)
            cover_pdf = convert_to_pdf(cover_docx, folder_path)
            os.remove(resume_docx)
            os.remove(cover_docx)
            row["resume_file"] = resume_pdf
            print(f"[{row['overlap_pct']}% match, variant={variant}] "
                  f"{row['company']} - {row['title']}  ->  {folder_path}")
        except RuntimeError as e:
            print(f"WARNING: PDF conversion failed for {row['company']} - {row['title']}: {e}")
            print("  Docx files were kept in place so you can convert manually.")
            row["resume_file"] = resume_docx

    print(f"\nDone. {len(new_rows)} application packages ready in {APPLICATIONS_DIR}/")
    print("Review each one, then apply yourself via the apply_url logged in the Excel sheet.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources", nargs="+", default=["arbeitnow"],
        choices=["arbeitnow", "linkedin", "indeed"],
        help="Which sources to collect from this run",
    )
    args = parser.parse_args()
    run(args.sources)