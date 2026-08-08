"""
Main entry point. Run this yourself, on your own machine:

    python main.py --sources arbeitnow
    python main.py --sources arbeitnow linkedin indeed   (needs APIFY_API_TOKEN set)
    python main.py --sources stepstone absolventa targets  (direct scraping/ATS boards)

    Diagnostic flags (all offline except the collectors themselves):
      python main.py --link-check       verify fact-bank project links (exit 1 on dead)
      python main.py --gap-report       aggregate technology gaps across all log sheets
      python main.py --dedupe-audit     summary of tracked postings + duplicate hash check
      python main.py --import-history CSV   load an old tracker CSV into a sheet
      python main.py --metric-audit     provenance for every metric token on the resume

What it does, in order (remediation-brief pipeline):
  1. Collect postings from the sources you choose -- ALWAYS filtered to the
     last 24 hours only, across every source. Sources: arbeitnow (JSON API),
     linkedin (Apify, needs token), indeed (pre-downloaded JSON),
     stepstone + absolventa (German boards, direct scraping), targets
     (target-company career pages via Greenhouse/Lever ATS APIs with an HTML
     fallback).
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
from resume_builder.linkcheck import remove_dead_links, \
    check_project_links, report_project_links

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

    if "stepstone" in sources:
        print("Collecting from StepStone (last 24h only)...")
        try:
            from collectors import stepstone
            all_postings += stepstone.fetch_postings()
        except Exception as e:
            print(f"WARNING: StepStone collection failed, skipping this source: {e}")

    if "absolventa" in sources:
        print("Collecting from Absolventa (last 24h only)...")
        try:
            from collectors import absolventa
            all_postings += absolventa.fetch_postings()
        except Exception as e:
            print(f"WARNING: Absolventa collection failed, skipping this source: {e}")

    if "targets" in sources:
        print("Collecting from target-company career pages (last 24h only)...")
        try:
            from collectors import target_companies
            all_postings += target_companies.fetch_postings()
        except Exception as e:
            print(f"WARNING: target-company collection failed, skipping this source: {e}")

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
        # A dead link is a signal, not noise -- check_urls_alive prints a loud
        # banner whenever the failing link belongs to the project leading this
        # posting (its server should be fixed, not its link suppressed).
        if check_links:
            try:
                from resume_builder.linkcheck import check_urls_alive
                lead_urls = [u for _, u in _project_urls_for(sc["lead_project"])]
                dead_links = check_urls_alive(lead_urls)
                removed = remove_dead_links(resume_docx, dead_links)
                if removed:
                    print(f"  (dropped {removed} dead link(s) from resume)")
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
        choices=["arbeitnow", "linkedin", "indeed", "stepstone", "absolventa", "targets"],
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
        "--link-check", action="store_true",
        help="Check every project link in the fact bank, print a banner for dead "
             "ones, and exit 1 if any are down (run this before a batch)",
    )
    parser.add_argument(
        "--gap-report", action="store_true",
        help="Aggregate the gaps column across all postings and show the techs "
             "that block you most (R5)",
    )
    parser.add_argument(
        "--dedupe-audit", action="store_true",
        help="Report how many postings are tracked and confirm the dedupe net "
             "covers your full apply history",
    )
    parser.add_argument(
        "--import-history", metavar="CSV",
        help="Import a CSV (company,title,location,apply_url) of postings you "
             "already applied to, so the pipeline never re-packages them",
    )
    parser.add_argument(
        "--metric-audit", action="store_true",
        help="List every metric in the fact bank with its declared source and "
             "flag any you cannot defend yet (review feedback, item 5)",
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

    if args.metric_audit:
        from fact_bank import metric_audit
        metrics = metric_audit()
        print("\nMetric provenance audit (review feedback, item 5) -- "
              "fix every needs_action row before your next run\n")
        for m in metrics:
            flag = "!!" if m["needs_action"] else "ok"
            print(f"  [{flag}] {m['token']:<9} {m['achievement']:<45} "
                  f"verified={m['verified']} kind={m['kind']} "
                  f"source={m['source'] or 'UNSET'}")
        action = sum(1 for m in metrics if m["needs_action"])
        print(f"\n{action} metric(s) still need a declared source. Set them in "
              "METRIC_SOURCES in fact_bank.py, or rewrite the claim as scope.")
        sys.exit(0)
    elif args.import_history:
        from pipeline.excel_log import import_history
        added = import_history(XLSX_PATH, args.import_history)
        print(f"Imported {added} new posting(s) from {args.import_history} "
              f"into the dedupe history ({XLSX_PATH}).")
        sys.exit(0)
    elif args.dedupe_audit:
        from pipeline.excel_log import audit_history
        stats = audit_history(XLSX_PATH)
        print(f"\nDedupe audit -- {XLSX_PATH}")
        print(f"  sheets:          {stats['sheets']}")
        print(f"  total rows:      {stats['rows']}")
        print(f"  unique postings: {stats['unique']}")
        print(f"  marked applied:  {stats['applied']}")
        print(f"  by status:       {stats['by_status']}")
        if stats["duplicate_rows"]:
            print(f"  WARNING: {len(stats['duplicate_rows'])} duplicate hash row(s): "
                  f"{stats['duplicate_rows'][:5]}")
        else:
            print("  no duplicate hashes -- dedupe net is clean")
        if not stats["rows"]:
            print("  NOTE: the tracker is empty. If you have applied to postings "
                  "before, import them with --import-history so they are never re-sent.")
        sys.exit(0)
    elif args.gap_report:
        from pipeline.excel_log import aggregate_gaps
        gaps = aggregate_gaps(XLSX_PATH)
        print(f"\nTechnology gap report (R5) -- {sum(g['count'] for g in gaps.values())} "
              f"gap occurrence(s) across all tracked postings\n")
        if not gaps:
            print("  No gaps logged yet -- run the pipeline first.")
        else:
            for tech, info in sorted(gaps.items(), key=lambda kv: -kv[1]["count"]):
                ex = "; ".join(f"{c} | {t}" for c, t in info["examples"])
                print(f"  {tech:<24} x{info['count']:<4} e.g. {ex}")
        sys.exit(0)
    elif args.link_check:
        results = check_project_links()
        report_project_links(results)
        dead = any(not ok for links in results.values() for ok, _ in links.values())
        print("\n" + ("1 or more project links are DOWN -- fix before generating packages."
                      if dead else "All project links are up."))
        sys.exit(1 if dead else 0)
    elif args.followup:
        followup.render_report(XLSX_PATH)
    elif args.mark_applied:
        followup.mark_applied(XLSX_PATH, args.mark_applied[0], args.mark_applied[1])
    elif args.mark_outcome:
        followup.mark_outcome(XLSX_PATH, *args.mark_outcome)
    else:
        run(args.sources, min_fit=args.min_fit, check_links=not args.no_link_check)
