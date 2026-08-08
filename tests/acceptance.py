"""
Acceptance tests T1-T9 (remediation brief).

Run with:
    python3 tests/acceptance.py

Prints PASS/FAIL per test and exits 1 if any test fails. Each test verifies a
concrete requirement; nothing here is aspirational -- every assertion is
executed against real modules and real generated documents.

  T1  Fact-bank integrity: validate_bank() reports 0 problems, canonical techs
      exist, no FILL markers.
  T2  JD parser: city, start date, duration, language "plus" handling,
      submission-channel priority, required technologies, gaps, domain.
  T3  No fabricated metrics: every number in a generated CV/letter claim
      section is present in fact_bank_numbers().
  T4  Metric stability: two postings with different JDs but the same profile
      produce claim sections with IDENTICAL number sets.
  T5  Cover-letter quality gates on the PIMCO-style sample: word count in
      [250, 350], no banned phrase, no Databricks/ChromaDB/FAISS/Streamlit
      mention, finance-role project leads (not urban transit), relocation
      addressed, start date matched, Pflichtpraktikum + work-auth present.
  T6  Gate correctness: language/start/location/duplicate/role-type rejections
      fire with reasons; viable postings pass.
  T7  Dead links: check_url() flags a deterministically-dead URL and passes a
      live one; remove_dead_links() drops the target URL from a generated docx.
  T8  R8 output hygiene: all ten required skill literals present in the skills
      block; PDF /Author metadata == PDF_AUTHOR; no broken tokens
      (RetrievalAugmented / percolumn).
  T9  End-to-end package: gate -> score -> build -> PDF conversion produces
      both PDFs with the configured names, nonzero pages, and a logged row
      carrying fit_score/channel/date_sent.
"""

import os
import re
import sys
import shutil
import tempfile
from datetime import date, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from config import (CV_FILENAME, COVER_LETTER_FILENAME, PDF_AUTHOR,
                    CANDIDATE_PROFILE, MIN_FIT_SCORE)
from fact_bank import (validate_bank, fact_bank_numbers, extract_numbers,
                       CANONICAL_TECHNOLOGIES)
from pipeline.jd_parser import parse_posting
from pipeline.gate import evaluate
from pipeline.scorer import score_posting
from resume_builder.build import build_resume
from resume_builder.cover_letter import build_cover_letter, letter_stats
from resume_builder.pdf_convert import (convert_to_pdf_clean, count_pdf_pages,
                                        pdf_text, verify_docx_text)
from resume_builder.linkcheck import check_url, remove_dead_links
from pipeline.excel_log import COLUMNS

R8_LITERALS = ["Kafka", "Apache Airflow", "dbt", "Spark Structured Streaming",
               "Delta Lake", "Great Expectations", "XGBoost", "Docker",
               "Prometheus", "Grafana"]

FAKE_ADDRESS = {"name": "Srikar Kodi", "street": "Musterstr. 1",
                "postal_code": "10115", "city": "Berlin", "country": "Germany"}

PIMCO_POSTING = {
    "company": "PIMCO Prime Real Estate",
    "title": "Intern in Software and Data Engineering (m/f/d)",
    "location": "Munich, Germany",
    "apply_url": "https://www.linkedin.com/jobs/view/123",
    "date_posted": "2026-08-05",
    "jd_text": (
        "Intern in Software and Data Engineering. Our team manages an $85B real "
        "estate mandate using Databricks and Streamlit. Requirements: Python, "
        "RAG/LLM solutions using vector databases, Spark. Start date 01.10.2026, "
        "duration 6 months. Fluency in German (C1) is a plus. Applications via "
        "careers.allianz.com. Contact: Anna Schmidt. Deadline 15.08.2026."
    ),
}

# A second posting with a DIFFERENT JD but the same profile (data_engineer),
# used by T4 to prove number-set stability across JDs.
LOGISTICS_POSTING = {
    "company": "Logistik Nord",
    "title": "Data Engineering Working Student",
    "location": "Hamburg, Germany",
    "apply_url": "https://www.linkedin.com/jobs/view/999",
    "date_posted": "2026-08-06",
    "jd_text": (
        "Data Engineering internship for our logistics control tower. Kafka and "
        "Spark streaming, dbt modelling, Delta Lake, Airflow orchestration, "
        "Great Expectations quality checks, XGBoost delay forecasts, Prometheus "
        "and Grafana dashboards. Start 01.11.2026, duration 5 months. Apply via "
        "karriere.logistiknord.de."
    ),
}

RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition), detail))
    return bool(condition)


def docx_text(docx_path):
    from docx import Document
    return [p.text for p in Document(docx_path).paragraphs]


def claim_section(paras):
    """Paragraph text from SUMMARY through PROJECTS (excludes the header
    contact block and EDUCATION dates, which are personal data, not metrics)."""
    start = next((i for i, t in enumerate(paras) if t.strip() == "SUMMARY"), None)
    end = next((i for i, t in enumerate(paras) if t.strip() == "EDUCATION"), len(paras))
    if start is None:
        return []
    return paras[start:end]


def skills_section(paras):
    start = next((i for i, t in enumerate(paras) if t.strip() == "TECHNICAL SKILLS"), None)
    end = next((i for i, t in enumerate(paras) if t.strip() == "PROFESSIONAL EXPERIENCE"), len(paras))
    if start is None:
        return []
    return paras[start:end]


# ---------------------------------------------------------------------------
# T1
# ---------------------------------------------------------------------------
def t1():
    problems = validate_bank()
    ok1 = check("T1 fact bank validates clean", len(problems) == 0,
                str(problems[:3]))
    ok2 = check("T1 canonical technologies non-empty",
                len(CANONICAL_TECHNOLOGIES) > 20)
    ok3 = check("T1 R8 literals exist in the bank",
                all(l in fact_bank_numbers.__globals__["CANONICAL_TECHNOLOGIES"]
                    for l in ["Kafka", "Apache Airflow", "dbt", "Docker"]))
    return ok1 and ok2 and ok3


# ---------------------------------------------------------------------------
# T2
# ---------------------------------------------------------------------------
def t2():
    p = parse_posting(PIMCO_POSTING)
    checks = [
        check("T2 city parsed", p["city"] == "Munich", p["city"]),
        check("T2 start date parsed", p["start_date"] and p["start_date"].month == 10
              and p["start_date"].year == 2026, str(p["start_date"])),
        check("T2 duration parsed", p["duration_months"] == 6, str(p["duration_months"])),
        check("T2 'C1 is a plus' not a hard requirement",
              all(not l.get("plus") for l in p["languages_required"]) and
              any(l.get("plus") for l in p["languages"]),
              str(p["languages"])),
        check("T2 channel: JD-named portal wins over apply_url",
              p["submission_channel"] == "careers.allianz.com" and
              p["submission_channel_kind"] == "company_portal",
              str(p["submission_channel"])),
        check("T2 required technologies extracted",
              "Python" in p["required_technologies"] and "Spark" in p["required_technologies"],
              str(p["required_technologies"])),
        check("T2 gaps detected (databricks)", "databricks" in p["technology_gaps"],
              str(p["technology_gaps"])),
        check("T2 domain classified", p["domain"] == "finance", str(p["domain"])),
    ]

    # Regression: a plain "from October 2026" phrasing used to crash
    # parse_start_date (the month alternation was a non-capturing group, so
    # m.group(2) did not exist). 'from <Month> <Year>' is very common in JDs.
    plain = parse_posting({**PIMCO_POSTING, "jd_text": (
        "Available from October 2026. Internship for 6 months. "
        "Requirements: Python, SQL.")})
    checks.append(check(
        "T2 plain 'from October 2026' does not crash",
        plain["start_date"] is not None and plain["start_date"].month == 10
        and plain["start_date"].year == 2026, str(plain["start_date"])))
    return all(checks)


# ---------------------------------------------------------------------------
# T3
# ---------------------------------------------------------------------------
def t3(build_dir):
    parsed = parse_posting(PIMCO_POSTING)
    scored = score_posting(PIMCO_POSTING, parsed)
    cv = os.path.join(build_dir, "t3_cv.docx")
    letter = os.path.join(build_dir, "t3_letter.docx")
    build_resume(scored["profile"], parsed, scored, cv, jd_text=PIMCO_POSTING["jd_text"])
    build_cover_letter(scored["profile"], parsed, scored, letter, sender_address=FAKE_ADDRESS)

    bank = fact_bank_numbers()
    cv_paras = claim_section(docx_text(cv))
    cv_nums = extract_numbers("\n".join(cv_paras))
    leaked_cv = sorted(cv_nums - bank)
    ok_cv = check("T3 CV claim-section numbers all in the fact bank",
                  not leaked_cv, f"leaked: {leaked_cv}" if leaked_cv else "")

    letter_paras = docx_text(letter)
    letter_nums = extract_numbers("\n".join(letter_paras))
    # Sender address / date lines are personal data, not metrics: exclude the
    # address block + signature lines.
    body_start = next((i for i, t in enumerate(letter_paras)
                       if t.strip().startswith("I am applying")), 0)
    body = letter_paras[body_start:]
    body_nums = extract_numbers("\n".join(body))
    leaked_letter = sorted(body_nums - bank)
    ok_letter = check("T3 letter body numbers all in the fact bank",
                      not leaked_letter, f"leaked: {leaked_letter}" if leaked_letter else "")
    return ok_cv and ok_letter


# ---------------------------------------------------------------------------
# T4
# ---------------------------------------------------------------------------
def t4(build_dir):
    p1 = parse_posting(PIMCO_POSTING)
    s1 = score_posting(PIMCO_POSTING, p1)
    p2 = parse_posting(LOGISTICS_POSTING)
    s2 = score_posting(LOGISTICS_POSTING, p2)

    cv1 = os.path.join(build_dir, "t4_cv1.docx")
    cv2 = os.path.join(build_dir, "t4_cv2.docx")
    build_resume(s1["profile"], p1, s1, cv1, jd_text=PIMCO_POSTING["jd_text"])
    build_resume(s2["profile"], p2, s2, cv2, jd_text=LOGISTICS_POSTING["jd_text"])

    n1 = extract_numbers("\n".join(claim_section(docx_text(cv1))))
    n2 = extract_numbers("\n".join(claim_section(docx_text(cv2))))
    # "5-6 months" (duration) may differ if the postings' durations differ;
    # the metric SET for achievements must be identical.
    metric_tokens = {t for t in n1 & n2 | n1 ^ n2 if not re.match(r"^\d+$", t) and t not in ("5", "6")}
    # Compare only achievement metrics: drop single-digit tokens that come
    # from durations/versions. Everything else must match exactly.
    stable = check("T4 number sets stable across different JDs",
                   {t for t in n1 if t not in ("5", "6", "2026")} ==
                   {t for t in n2 if t not in ("5", "6", "2026")},
                   f"only in cv1: {sorted(n1 - n2)}; only in cv2: {sorted(n2 - n1)}")
    return stable


# ---------------------------------------------------------------------------
# T5
# ---------------------------------------------------------------------------
def t5(build_dir):
    parsed = parse_posting(PIMCO_POSTING)
    scored = score_posting(PIMCO_POSTING, parsed)
    letter = os.path.join(build_dir, "t5_letter.docx")
    build_cover_letter(scored["profile"], parsed, scored, letter, sender_address=FAKE_ADDRESS)
    paras = docx_text(letter)
    text = "\n".join(paras)
    stats = letter_stats(text)
    body = "\n".join(paras[next((i for i, t in enumerate(paras)
                                 if t.strip().startswith("I am applying")), 0):])

    results = [
        check("T5 word count in [250, 350]", 250 <= stats["words"] <= 350,
              f"{stats['words']} words"),
        check("T5 no banned phrases", not stats["banned"], str(stats["banned"])),
        check("T5 no Databricks/ChromaDB/FAISS/Streamlit mention",
              not any(w in body for w in ["Databricks", "ChromaDB", "FAISS", "Streamlit"]),
              ""),
        check("T5 leads with finance project, not urban transit",
              "CreditLens" in text and "Stadtanalyse" not in body.split("Thank you")[0],
              ""),
        check("T5 relocation addressed", "relocate to Munich" in text, ""),
        check("T5 start date matched", "October 2026" in text, ""),
        check("T5 Pflichtpraktikum + work auth present",
              "Pflichtpraktikum" in text and "140-day" in text, ""),
        check("T5 named recipient used", "Dear Anna Schmidt," in text, ""),
    ]
    return all(results)


# ---------------------------------------------------------------------------
# T6
# ---------------------------------------------------------------------------
def t6():
    results = []

    bad_german = {"company": "A", "title": "Data Engineer Intern",
                  "location": "Berlin", "date_posted": "2026-08-06",
                  "jd_text": "German C1 required. Start 01.10.2026. Python ETL. careers.a.de"}
    ok, reasons = evaluate(bad_german)
    results.append(check("T6 German C1 required -> blocked",
                         not ok and any("German c1" in r for r in reasons), str(reasons)))

    bad_start = {"company": "B", "title": "Data Engineering Intern",
                 "location": "Berlin", "date_posted": "2026-08-06",
                 "jd_text": "Start 01.03.2026. Python, ETL. Apply via careers.b.de"}
    ok, reasons = evaluate(bad_start)
    results.append(check("T6 start before availability -> blocked",
                         not ok and any("before availability" in r for r in reasons), str(reasons)))

    bad_city = {"company": "C", "title": "Data Engineering Intern",
                "location": "Dresden", "date_posted": "2026-08-06",
                "jd_text": "Start 01.10.2026. Python, ETL. Apply via careers.c.de"}
    ok, reasons = evaluate(bad_city)
    results.append(check("T6 city outside relocation list -> blocked",
                         not ok and any("not in relocation" in r for r in reasons), str(reasons)))

    seen = set()
    dup = {"company": "Allianz", "title": "Data Engineer Intern (m/f/d)",
           "location": "Munich", "date_posted": "2026-08-06",
           "jd_text": "Start 01.10.2026. Python, ETL. Apply via careers.allianz.com"}
    ok1, _ = evaluate(dup, seen_keys=seen)
    dup2 = {"company": "Allianz Technology", "title": "Data Engineer Intern (m/f/d)",
            "location": "Munich", "date_posted": "2026-08-07",
            "jd_text": "Start 01.10.2026. Python, ETL. Apply via allianz.com"}
    ok2, reasons2 = evaluate(dup2, seen_keys=seen)
    results.append(check("T6 duplicate requisition across subsidiaries -> blocked",
                         ok1 and not ok2 and any("duplicate" in r for r in reasons2), str(reasons2)))

    ml_research = {"company": "D", "title": "ML Research Intern",
                   "location": "Berlin", "date_posted": "2026-08-06",
                   "jd_text": "Research on model interpretability. Python, PyTorch. careers.d.de"}
    ok, reasons = evaluate(ml_research)
    results.append(check("T6 ML Research role -> blocked",
                         not ok and any("ML Research" in r for r in reasons), str(reasons)))

    easy_apply = {"company": "F", "title": "Data Engineering Intern",
                  "location": "Berlin", "date_posted": "2026-08-06",
                  "jd_text": "Start 01.10.2026. Python, ETL. Easy Apply"}
    ok, reasons = evaluate(easy_apply)
    results.append(check("T6 Easy-Apply-only channel -> blocked (R9 enforcement)",
                         not ok and any("Easy Apply channel refused" in r for r in reasons),
                         str(reasons)))

    portal_wins = {"company": "G", "title": "Data Engineering Intern",
                   "location": "Berlin", "date_posted": "2026-08-06",
                   "jd_text": "Start 01.10.2026. Python, ETL. "
                              "Apply via careers.g.de. Easy Apply also available."}
    ok, reasons = evaluate(portal_wins)
    results.append(check("T6 JD-named portal beats Easy Apply markers",
                         ok and not any("Easy Apply channel refused" in r for r in reasons),
                         str(reasons)))

    viable = {"company": "E", "title": "Data Engineering Internship",
              "location": "Munich", "date_posted": "2026-08-06",
              "jd_text": "Data Engineering internship, Python, Kafka, ETL. Start 01.10.2026. "
                         "Apply via careers.e.de"}
    ok, reasons = evaluate(viable)
    results.append(check("T6 viable data-eng posting passes", ok,
                         str(reasons) if reasons else ""))

    return all(results)


# ---------------------------------------------------------------------------
# T7
# ---------------------------------------------------------------------------
def t7(build_dir):
    # Use a deterministically-dead URL (.invalid always fails DNS) rather than a
    # live server that may be up or down depending on the day.
    dead_ok, dead_status = check_url("http://nonexistent.invalid/")
    live_ok, live_status = check_url("https://github.com/Namidok/CreditLens")
    r1 = check("T7 known-dead link flagged", not dead_ok, f"status={dead_status}")
    r2 = check("T7 known-live link passes", live_ok, f"status={live_status}")

    # Build a docx, then drop the dead link and confirm the hyperlink is gone.
    parsed = parse_posting(PIMCO_POSTING)
    scored = score_posting(PIMCO_POSTING, parsed)
    cv = os.path.join(build_dir, "t7_cv.docx")
    build_resume(scored["profile"], parsed, scored, cv, jd_text=PIMCO_POSTING["jd_text"])
    removed = remove_dead_links(cv, ["https://creditlens.srikarkodi.dev"])
    r3 = check("T7 dead link removed from resume", removed >= 1, f"removed={removed}")
    return r1 and r2 and r3


# ---------------------------------------------------------------------------
# T8
# ---------------------------------------------------------------------------
def t8(build_dir):
    parsed = parse_posting(PIMCO_POSTING)
    scored = score_posting(PIMCO_POSTING, parsed)
    cv_docx = os.path.join(build_dir, "t8_cv.docx")
    build_resume(scored["profile"], parsed, scored, cv_docx, jd_text=PIMCO_POSTING["jd_text"])

    skills_text = "\n".join(skills_section(docx_text(cv_docx)))
    missing = [l for l in R8_LITERALS if l not in skills_text]
    r1 = check("T8 all ten required literals in skills block", not missing,
               f"missing: {missing}")

    cv_pdf = convert_to_pdf_clean(cv_docx, build_dir)
    from pypdf import PdfReader
    meta = PdfReader(cv_pdf).metadata
    r2 = check("T8 PDF Author metadata set", meta.get("/Author") == PDF_AUTHOR,
               f"Author={meta.get('/Author')}")
    r3 = check("T8 no producer/creator fingerprints",
               not meta.get("/Producer") and not meta.get("/Creator"),
               f"Producer={meta.get('/Producer')}, Creator={meta.get('/Creator')}")

    full_text = docx_text(cv_docx)
    r4 = check("T8 no broken tokens (RetrievalAugmented / percolumn)",
               not verify_docx_text("\n".join(full_text)),
               str(verify_docx_text("\n".join(full_text))))
    return r1 and r2 and r3 and r4


# ---------------------------------------------------------------------------
# T9
# ---------------------------------------------------------------------------
def t9(build_dir):
    from pipeline.excel_log import append_postings
    from pipeline import gate as gate_mod

    postings = [
        {**PIMCO_POSTING, "source": "test", "gate_status": "passed",
         "fit_score": 82.5, "profile": "data_engineer", "gaps": "databricks",
         "submission_channel": "careers.allianz.com",
         "submission_channel_kind": "company_portal", "date_sent": date.today().isoformat()},
        {**LOGISTICS_POSTING, "source": "test", "gate_status": "passed",
         "fit_score": 91.0, "profile": "data_engineer", "gaps": "",
         "submission_channel": "karriere.logistiknord.de",
         "submission_channel_kind": "company_portal", "date_sent": date.today().isoformat()},
    ]

    xlsx = os.path.join(build_dir, "postings.xlsx")
    rows = append_postings(xlsx, postings)
    r1 = check("T9 log rows created", len(rows) == 2, f"{len(rows)} rows")
    r2 = check("T9 log carries fit_score", all(r.get("fit_score") for r in rows), "")
    r3 = check("T9 log carries channel", all(r.get("channel") for r in rows), "")
    r4 = check("T9 log carries date_sent", all(r.get("date_sent") for r in rows), "")
    r5 = check("T9 new COLUMNS include response tracking",
               "response_date" in COLUMNS and "days_to_response" in COLUMNS, "")

    # Full generation path for one posting (build -> PDF -> page count).
    parsed = parse_posting(LOGISTICS_POSTING)
    scored = score_posting(LOGISTICS_POSTING, parsed)
    pkg_dir = os.path.join(build_dir, "package")
    os.makedirs(pkg_dir, exist_ok=True)
    cv_docx = os.path.join(pkg_dir, f"{CV_FILENAME}.docx")
    build_resume(scored["profile"], parsed, scored, cv_docx, jd_text=LOGISTICS_POSTING["jd_text"])
    cv_pdf = convert_to_pdf_clean(cv_docx, pkg_dir)
    os.remove(cv_docx)
    r6 = check("T9 CV PDF produced with configured name",
               os.path.basename(cv_pdf) == f"{CV_FILENAME}.pdf", os.path.basename(cv_pdf))
    r7 = check("T9 CV PDF has >= 1 page", count_pdf_pages(cv_pdf) >= 1,
               str(count_pdf_pages(cv_pdf)))

    letter_docx = os.path.join(pkg_dir, f"{COVER_LETTER_FILENAME}.docx")
    build_cover_letter(scored["profile"], parsed, scored, letter_docx,
                       sender_address=FAKE_ADDRESS)
    letter_pdf = convert_to_pdf_clean(letter_docx, pkg_dir)
    os.remove(letter_docx)
    r8 = check("T9 cover-letter PDF produced with configured name",
               os.path.basename(letter_pdf) == f"{COVER_LETTER_FILENAME}.pdf",
               os.path.basename(letter_pdf))
    return r1 and r2 and r3 and r4 and r5 and r6 and r7 and r8


# T10: new sourcing collectors (review feedback item 1). Offline-only -- canned
# HTML through the parsers, plus config shape checks. Network behaviour is
# exercised by the smoke runs, not by the acceptance suite.
def t10(build_dir):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    from collectors import _scrape, stepstone, absolventa, target_companies
    from config import TARGET_COMPANIES

    # StepStone card parser on canned HTML.
    ss_html = (
        '<article><a data-testid="job-item-title" '
        'href="/stellenangebote--Werkstudent-Data-Berlin--1-inline.html">'
        'Werkstudent Data (m/w/d)</a><span>Firma AG</span>'
        '<time>vor 5 Stunden</time></article>'
    )
    items = stepstone._parse_listing(ss_html)
    r1 = check("T10 StepStone card parsed", len(items) == 1, f"{len(items)}")
    r2 = check("T10 StepStone fields parsed",
               items and items[0]["title"] == "Werkstudent Data (m/w/d)"
               and items[0]["href"].startswith("/stellenangebote")
               and items[0]["date_posted"], str(items[0] if items else None))

    # Absolventa card parser on canned HTML (incl. the -b- href variant).
    ab_html = (
        '<article><a href="/stellenangebote/999-p-test-intern-b-role"><h2>'
        'Test Intern (m/w/d)</h2></a><span>Neu</span></article>'
    )
    items = absolventa._parse_listing(ab_html)
    r3 = check("T10 Absolventa card parsed", len(items) == 1, f"{len(items)}")
    r4 = check("T10 Absolventa fields parsed",
               items and items[0]["title"] == "Test Intern (m/w/d)"
               and items[0]["href"].startswith("/stellenangebote")
               and items[0]["date_posted"] == date.today().isoformat(),
               str(items[0] if items else None))

    # Target-company config shape: every entry is monitorable.
    bad = [t for t in TARGET_COMPANIES if not t.get("name")]
    for t in TARGET_COMPANIES:
        if t.get("kind") in ("greenhouse", "lever"):
            if not t.get("board"):
                bad.append(t)
        else:
            if not t.get("url"):
                bad.append(t)
    r5 = check("T10 TARGET_COMPANIES well-formed", not bad, f"{len(bad)} bad entries")
    r6 = check("T10 target_companies exports fetch_postings",
               callable(target_companies.fetch_postings), "")

    # Shared helpers: German relative dates + script-stripping (the JD-cap fix).
    r7 = check("T10 german_relative_to_iso handles 'vor 2 Tagen'",
               _scrape.german_relative_to_iso("vor 2 Tagen") ==
               (date.today() - timedelta(days=2)).isoformat(), "")
    r8 = check("T10 strip_html drops script contents (JD flood fix)",
               "javascript" not in _scrape.strip_html(
                   "<p>Hello</p><script>javascript here</script>", max_len=200), "")
    r9 = check("T10 strip_html capped at max_len",
               len(_scrape.strip_html("<p>abcdefghij</p>", max_len=4)) <= 4, "")
    return r1 and r2 and r3 and r4 and r5 and r6 and r7 and r8 and r9


def main():
    build_dir = tempfile.mkdtemp(prefix="acceptance_", dir="/tmp")
    print(f"Build dir: {build_dir}\n")
    try:
        tests = [t1, t2, lambda: t3(build_dir), lambda: t4(build_dir),
                 lambda: t5(build_dir), t6, lambda: t7(build_dir),
                 lambda: t8(build_dir), lambda: t9(build_dir),
                 lambda: t10(build_dir)]
        failed = 0
        for run in tests:
            try:
                passed = run()
            except Exception as e:
                passed = False
                check(run.__name__ if hasattr(run, "__name__") else "test", False, f"EXCEPTION: {e!r}")
            if not passed:
                failed += 1
    finally:
        pass

    print("=" * 70)
    for name, ok, detail in RESULTS:
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}")
        if detail and not ok:
            print(f"        {detail}")
    print("=" * 70)

    total = len([r for r in RESULTS if r[0].startswith("T")])
    passed_total = len([r for r in RESULTS if r[0].startswith("T") and r[1]])
    print(f"\n{passed_total}/{total} acceptance checks passed.")
    shutil.rmtree(build_dir, ignore_errors=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
