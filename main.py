"""
Main entry point. Run this yourself, on your own machine:

    python main.py --sources arbeitnow
    python main.py --sources arbeitnow linkedin indeed   (needs APIFY_API_TOKEN set)

What it does, in order:
  1. Collect postings from the sources you choose -- ALWAYS filtered to the
     last 24 hours only, across every source.
  2. Normalize + dedupe against data/postings.xlsx (safe to re-run daily)
  3. Score each NEW posting (honest keyword-overlap, not a fake "ATS score")
  4. Drop unwinnable postings (German C1 at A2, PhD-required, 5+ yrs) --
     still logged with the reason, but no package built
  5. Pick the best-fit resume variant (data_engineer / ai_ml / nlp)
  6. Generate a tailored resume + cover letter, convert both to PDF, delete
     the intermediate docx
  7. Save into applications/Company_Role_Date/ as:
       SrikarKodi.pdf        <- resume
       Srikar_Kodi.pdf       <- cover letter
  8. Log everything to data/postings.xlsx with a real clickable hyperlink

Follow-up (after you apply):
    python main.py --mark-applied SHEET ROW          # mark a posting as applied
    python main.py --followup                        # report + follow-up email drafts
    python main.py --mark-outcome SHEET ROW OUTCOME  # replied/interview/offer/...

New postings are packaged in priority order (best overlap_pct first), so when
you only have a few hours you apply to the strongest fits first.

You still click "Apply" yourself -- this tool prepares, it never submits.

REQUIRES LibreOffice installed for PDF conversion.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

from collectors import arbeitnow, indeed_loader
from pipeline import scorer, excel_log, date_filter, followup, blocker_filter
from resume_builder.build import build_resume, build_resume_fitted
from resume_builder.cover_letter import build_cover_letter
from resume_builder.pdf_convert import convert_to_pdf, count_pdf_pages

XLSX_PATH = os.path.join(os.path.dirname(__file__), "data", "postings.xlsx")
APPLICATIONS_DIR = os.path.join(os.path.dirname(__file__), "applications")

RESUME_FILENAME = "SrikarKodi"
COVER_LETTER_FILENAME = "Srikar_Kodi"


def safe_folder_name(company, title, date):
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", f"{company}_{title}").strip("_")
    return f"{slug}_{date}"


def _overlap_sort_key(row):
    try:
        return float(row.get("overlap_pct") or 0)
    except (TypeError, ValueError):
        return 0.0


def run(sources, min_overlap=0.0):
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
        p["_matched"] = result["matched"]
        p["_highlights"] = result["highlights"]

    # Hard blockers: postings you cannot win regardless of CV quality
    # (German C1 at A2, PhD-required, 5+ years on an internship req).
    # They are still logged -- with the reason -- but no package is built.
    all_postings, blocked = blocker_filter.annotate(all_postings)
    if blocked:
        print(f"\n{len(blocked)} posting(s) skipped as unwinnable:")
        for b in blocked:
            print(f"  - {b['company']} | {b['title']}  ->  {b['blockers']}")
        excel_log.append_postings(XLSX_PATH, blocked)

    new_rows = excel_log.append_postings(XLSX_PATH, all_postings)
    print(f"{len(new_rows)} NEW postings added to {XLSX_PATH} (duplicates skipped).\n")

    new_rows.sort(key=_overlap_sort_key, reverse=True)
    print("Priority order (best fit first) -- packages are generated in this order:\n")
    for i, row in enumerate(new_rows, 1):
        print(f"  {i}. [{row['overlap_pct']}% match, variant={row['best_variant']}] "
              f"{row['company']} - {row['title']}")

    from datetime import date
    today = date.today().isoformat()

    for row in new_rows:
        variant = row["best_variant"] or "ai_ml"

        pct = _overlap_sort_key(row)
        if pct < min_overlap:
            print(f"  (skipped package: {row['company']} - {row['title']} "
                  f"at {pct}% < {min_overlap}% minimum -- logged but no folder made)")
            continue

        # makedirs moved BELOW the threshold check -- it used to run first, so
        # skipped postings still got an empty folder while the message said
        # otherwise.
        folder_name = safe_folder_name(row["company"], row["title"], today)
        folder_path = os.path.join(APPLICATIONS_DIR, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # Reuse the scores computed above rather than re-scoring.
        matched = row.get("_matched", [])
        highlights = row.get("_highlights", [])

        resume_docx = os.path.join(folder_path, f"{RESUME_FILENAME}.docx")
        cover_docx = os.path.join(folder_path, f"{COVER_LETTER_FILENAME}.docx")

        build_resume_fitted(variant, resume_docx, matched=matched)
        build_cover_letter(variant, row["company"], row["title"], cover_docx,
                           matched=matched, highlights=highlights)

        try:
            resume_pdf = convert_to_pdf(resume_docx, folder_path)
            cover_pdf = convert_to_pdf(cover_docx, folder_path)
            os.remove(resume_docx)
            os.remove(cover_docx)
            row["resume_file"] = resume_pdf
            pages = count_pdf_pages(resume_pdf)
            if pages > 1:
                print(f"  NOTE: resume for {row['company']} spills to {pages} pages "
                      f"-- consider trimming bullets in config.py")
            print(f"[{row['overlap_pct']}% match, variant={variant}] "
                  f"{row['company']} - {row['title']}  ->  {folder_path}")
        except RuntimeError as e:
            print(f"WARNING: PDF conversion failed for {row['company']} - {row['title']}: {e}")
            print("  Docx files were kept in place so you can convert manually.")
            row["resume_file"] = resume_docx

    print(f"\nDone. {len(new_rows)} application packages ready in {APPLICATIONS_DIR}/")
    print("Review each one, then apply yourself via the apply_url logged in the Excel sheet.")
    print("\nAfter you apply, track it so the follow-up engine can nudge you:")
    print("  python main.py --mark-applied  SHEET ROW")
    print("  python main.py --followup")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources", nargs="+", default=["arbeitnow"],
        choices=["arbeitnow", "linkedin", "indeed"],
        help="Which sources to collect from this run",
    )
    parser.add_argument(
        "--min-overlap", type=float, default=0.0,
        help="Skip generating application packages below this overlap_pct (still logged)",
    )
    parser.add_argument(
        "--followup", action="store_true",
        help="Show the follow-up report for data/postings.xlsx and exit",
    )
    parser.add_argument(
        "--mark-applied", nargs=2, metavar=("SHEET", "ROW"),
        help="Mark a logged posting as applied (sets applied_date + follow_up_date)",
    )
    parser.add_argument(
        "--mark-outcome", nargs=3, metavar=("SHEET", "ROW", "OUTCOME"),
        help="Record replied|interview|offer|rejected|withdrawn for a posting",
    )
    args = parser.parse_args()

    if args.followup:
        followup.render_report(XLSX_PATH)
    elif args.mark_applied:
        followup.mark_applied(XLSX_PATH, args.mark_applied[0], args.mark_applied[1])
    elif args.mark_outcome:
        followup.mark_outcome(XLSX_PATH, *args.mark_outcome)
    else:
        run(args.sources, min_overlap=args.min_overlap)