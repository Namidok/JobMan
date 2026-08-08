"""
Main entry point. Run this yourself, on your own machine:

    python main.py --sources arbeitnow
    python main.py --sources arbeitnow linkedin indeed   (needs APIFY_API_TOKEN set)

What it does, in order (remediation-brief pipeline):
  1. Collect postings from the sources you choose -- ALWAYS filtered to the
     last 24 hours only, across every source.
  2. Parse each posting (pipeline/jd_parser.py): city, start date, duration,
     required languages, submission channel, required technologies, gaps.
  3. Run the disqualification gate (pipeline/gate.py): German above B1,
     start date outside the availability window, location outside the
     relocation list, postings older than MAX_POSTING_AGE_DAYS, duplicates
     (incl. cross-platform reposts of the same requisition), and roles that
     are not genuinely Data Engineering / Applied AI. Blocked postings are
     still logged -- with the reason -- but no package is built.
  4. Score survivors (pipeline/scorer.py): required-tech overlap with the
     fact bank + domain proximity + seniority. Hard floor = MIN_FIT_SCORE.
  5. Generate a tailored resume + cover letter from the fact bank (R5/R6),
     drop dead project links (R7), convert both to PDF with clean metadata
     (R8), and delete the intermediate docx.
  6. Save into applications/Company_Role_Date/ as:
       Kodi_Srikar_CV.pdf          <- resume
       Kodi_Srikar_Anschreiben.pdf <- cover letter
  7. Log everything to data/postings.xlsx with date sent, channel, fit score,
     gate decisions, gaps, and response tracking (R10).

Follow-up (after you apply):
    python main.py --mark-applied SHEET ROW          # mark a posting as applied
    python main.py --followup                        # report + follow-up email drafts
    python main.py --mark-outcome SHEET ROW OUTCOME  # replied/interview/offer/...

New postings are packaged in priority order (best fit_score first), so when
you only have a few hours you apply to the strongest fits first.

You still click "Apply" yourself -- this tool prepares, it never submits.

REQUIRES LibreOffice installed for PDF conversion.
"""

import argparse
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

from config import (MIN_FIT_SCORE, CV_FILENAME, COVER_LETTER_FILENAME,
                    sender_address_configured, SENDER_ADDRESS)
from collectors import arbeitnow, indeed_loader
from pipeline import excel_log, date_filter, followup, gate
from pipeline.jd_parser import parse_posting
from pipeline.scorer import score_posting
from resume_builder.build import build_resume_fitted
from resume_builder.cover_letter import build_cover_letter
from resume_builder.pdf_convert import convert_to_pdf_clean, count_pdf_pages
from resume_builder.linkcheck import remove_dead_links, check_url

XLSX_PATH = os.path.join(os.path.dirname(__file__), "data", "postings.xlsx")
APPLICATIONS_DIR = os.path.join(os.path.dirname(__file__), "applications")


def safe_folder_name(company, title, date):
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", f"{company}_{title}").strip("_")
    return f"{slug}_{date}"


def _fit_sort_key(row):
    try:
        return float(row.get("fit_score") or 0)
    except (TypeError, ValueError):
        return 0.0


def _collect(sources):
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

    return all_postings


def run(sources, min_fit=MIN_FIT_SCORE, check_links=True):
    all_postings = _collect(sources)
    print(f"\nCollected {len(all_postings)} raw postings (last 24h) across selected sources.")

    # 2. Parse every posting.
    for p in all_postings:
        p["parsed"] = parse_posting(p)
        p["_jd"] = p.get("jd_text", "")

    # 3. Gate: disqualify with a logged reason; survivors carry `parsed`.
    allowed, blocked = gate.annotate(all_postings)
    for b in blocked:
        b["gate_status"] = "blocked"
        b["gate_reasons"] = "; ".join(b["gate_reasons"])
    if blocked:
        print(f"\n{len(blocked)} posting(s) blocked by the gate:")
        for b in blocked:
            print(f"  - {b['company']} | {b['title']}  ->  {b['gate_reasons']}")

    # 4. Score survivors (honest fit against the fact bank, hard floor).
    for p in allowed:
        sc = score_posting(p, p["parsed"])
        p["fit_score"] = sc["fit_score"]
        p["profile"] = sc["profile"]
        p["gaps"] = ", ".join(sc["technology_gaps"]) if sc["technology_gaps"] else ""
        p["gate_status"] = "passed"
        p["scored"] = sc

    below = [p for p in allowed if p.get("fit_score", 0) < min_fit]
    qualified = [p for p in allowed if p.get("fit_score", 0) >= min_fit]
    if below:
        print(f"\n{len(below)} posting(s) below the {min_fit} fit floor (logged, not packaged):")
        for p in below:
            print(f"  - {p['company']} | {p['title']}  ->  fit {p['fit_score']}")

    # 5+7. Log blocked + all allowed postings (their fit scores) to the workbook.
    for p in blocked + allowed:
        p["fit_score"] = p.get("fit_score", "")
    new_rows = excel_log.append_postings(XLSX_PATH, blocked + allowed)
    print(f"\n{len(new_rows)} NEW postings added to {XLSX_PATH} (duplicates skipped).\n")

    qualified.sort(key=_fit_sort_key, reverse=True)
    print("Priority order (best fit first) -- packages are generated in this order:\n")
    for i, row in enumerate(qualified, 1):
        print(f"  {i}. [fit {row['fit_score']}, profile={row['profile']}] "
              f"{row['company']} - {row['title']}")

    today = date.today().isoformat()
    letter_ready = sender_address_configured()
    if not letter_ready:
        print("\nWARNING: SENDER_ADDRESS still has FILL: markers -- cover letters will be "
              "skipped. Set street + postal_code in config.py to enable them.")

    for row in qualified:
        parsed = row["parsed"]
        sc = row["scored"]

        folder_name = safe_folder_name(row["company"], row["title"], today)
        folder_path = os.path.join(APPLICATIONS_DIR, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        resume_docx = os.path.join(folder_path, f"{CV_FILENAME}.docx")
        cover_docx = os.path.join(folder_path, f"{COVER_LETTER_FILENAME}.docx")

        build_resume_fitted(sc["profile"], parsed, sc, resume_docx, jd_text=row.get("jd_text", ""))

        # R7: verify links before conversion and drop dead ones from the docx.
        if check_links:
            try:
                for _, url in _project_urls_for(sc["lead_project"]):
                    ok, _status = check_url(url)
                    if not ok:
                        removed = remove_dead_links(resume_docx, [url])
                        if removed:
                            print(f"  (dropped dead link {url} from resume)")
            except Exception as e:
                print(f"  WARNING: link check failed for {row['company']}: {e}")

        if letter_ready:
            try:
                build_cover_letter(sc["profile"], parsed, sc, cover_docx,
                                   sender_address=SENDER_ADDRESS)
            except SystemExit as e:
                print(f"  (cover letter skipped: {e})")
                cover_docx = None
        else:
            cover_docx = None

        try:
            resume_pdf = convert_to_pdf_clean(resume_docx, folder_path)
            os.remove(resume_docx)
            row["resume_file"] = resume_pdf
            pages = count_pdf_pages(resume_pdf)
            if pages > 1:
                print(f"  NOTE: resume for {row['company']} spills to {pages} pages "
                      f"-- consider trimming bullets in config.py")
            if cover_docx:
                cover_pdf = convert_to_pdf_clean(cover_docx, folder_path)
                os.remove(cover_docx)
                row["cover_file"] = cover_pdf
            row["date_sent"] = today
            row["status"] = "prepared"
            print(f"[fit {row['fit_score']}, profile={row['profile']}] "
                  f"{row['company']} - {row['title']}  ->  {folder_path}")
        except RuntimeError as e:
            print(f"WARNING: PDF conversion failed for {row['company']} - {row['title']}: {e}")
            print("  Docx files were kept in place so you can convert manually.")
            row["resume_file"] = resume_docx

    print(f"\nDone. {len(qualified)} application packages ready in {APPLICATIONS_DIR}/")
    print("Review each one, then apply yourself via the apply_url logged in the Excel sheet.")
    print("\nAfter you apply, track it so the follow-up engine can nudge you:")
    print("  python main.py --mark-applied  SHEET ROW")
    print("  python main.py --followup")


def _project_urls_for(lead_project):
    """All banked URLs that would appear in a package (lead project links)."""
    from fact_bank import PROJECT_ACHIEVEMENTS
    proj = PROJECT_ACHIEVEMENTS.get(lead_project) or PROJECT_ACHIEVEMENTS["creditlens"]
    return proj.get("links") or []


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources", nargs="+", default=["arbeitnow"],
        choices=["arbeitnow", "linkedin", "indeed"],
        help="Which sources to collect from this run",
    )
    parser.add_argument(
        "--min-fit", type=float, default=MIN_FIT_SCORE,
        help=f"Skip generating application packages below this fit score (default {MIN_FIT_SCORE})",
    )
    parser.add_argument(
        "--no-link-check", action="store_true",
        help="Skip the R7 live link check (faster, but dead links are not dropped)",
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
        run(args.sources, min_fit=args.min_fit, check_links=not args.no_link_check)
