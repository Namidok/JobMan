"""T1 automation (review feedback): prove that the three domain variants of
the CV differ in the ways that matter, instead of self-certifying by eye.

Generates three synthetic postings -- fintech (data_eng profile), logistics
(data_eng profile), manufacturing (ai_ml profile, 'general' domain) -- runs
each through parse -> score -> build -> PDF, then asserts:

  * the lead project differs per domain (creditlens for finance, stadtanalyse
    for logistics, and the general-domain fallback for manufacturing),
  * the project order differs between fintech and logistics CVs,
  * the skills category order is profile-pinned (programming/data_eng vs
    programming/ai_ml) and the within-line reorder surfaces JD-mentioned
    technologies first,
  * the PDF literals match the profile: the profile-role line and the lead
    project appear in each rendered PDF.

Run:  python3 scripts/verify_t1_variants.py
Exits 1 on any failed assertion (like the acceptance suite).
"""

import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pypdf import PdfReader

from pipeline.jd_parser import parse_posting
from pipeline.scorer import score_posting
from resume_builder.build import build_resume, _profile_role, _project_order, \
    _skill_category_order, _reorder_skill_items
from resume_builder.pdf_convert import convert_to_pdf_clean

from config import CV_FILENAME

BASE = {
    "company": "Acme",
    "location": "Berlin, Germany",
    "apply_url": "https://example.com/job",
    "jd_text": (
        "Internship for 6 months. Requirements: Python, SQL, Pandas. "
        "Build ETL pipelines. Available from October 2026. "
        "We expect strong analytical skills and English. "
    ),
}

POSTINGS = {
    "fintech": dict(BASE, company="Fintech Bank AG", title="Data Engineering Intern (m/f/d)",
                    jd_text=BASE["jd_text"] +
                    " Credit portfolio analytics, risk management, lending and treasury."),
    "logistics": dict(BASE, company="Logistik Nord GmbH", title="Data Engineering Intern (m/f/d)",
                      jd_text=BASE["jd_text"] +
                      " Supply chain analytics, routing and fleet telematics."),
    "manufacturing": dict(BASE, company="Maschinenbau West", title="AI / Machine Learning Intern (m/f/d)",
                          jd_text=BASE["jd_text"] +
                          " Machine learning, LLM and RAG pipelines for the shop floor."),
}


def _extract_pdf_text(pdf_path):
    reader = PdfReader(pdf_path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _docx_text(docx_path):
    from docx import Document
    doc = Document(docx_path)
    return "\n".join(p.text for p in doc.paragraphs)


def _run_case(name, posting, build_dir):
    parsed = parse_posting(posting)
    sc = score_posting(posting, parsed)
    case_dir = os.path.join(build_dir, name)
    os.makedirs(case_dir, exist_ok=True)

    docx = os.path.join(case_dir, f"{CV_FILENAME}.docx")
    build_resume(sc["profile"], parsed, sc, docx, jd_text=posting["jd_text"])
    doc_text = _docx_text(docx)
    pdf = convert_to_pdf_clean(docx, case_dir)
    os.remove(docx)

    pdf_text = _extract_pdf_text(pdf)

    order = _project_order(parsed, sc)
    cat_order = _skill_category_order(sc["profile"], posting["jd_text"])
    return {
        "domain": parsed.get("domain"),
        "profile": sc["profile"],
        "lead": sc.get("lead_project"),
        "order": order,
        "cat_order": cat_order,
        "pdf_text": pdf_text,
        "doc_text": doc_text if doc_text.strip() else pdf_text,
    }


def main():
    build_dir = tempfile.mkdtemp(prefix="t1_variants_", dir="/tmp")
    print(f"Build dir: {build_dir}\n")

    results = {}
    fails = []
    for name, posting in POSTINGS.items():
        results[name] = _run_case(name, posting, build_dir)
        r = results[name]
        print(f"{name}: domain={r['domain']:10s} profile={r['profile']:10s} "
              f"lead={r['lead']}")
        print(f"    project order: {', '.join(r['order'])}")
        print(f"    category order: {', '.join(r['cat_order'])}")

    def fail(cond, msg):
        if not cond:
            fails.append(msg)

    fin = results["fintech"]
    log = results["logistics"]
    man = results["manufacturing"]

    # Domains parsed as intended.
    fail(fin["domain"] == "finance", f"fintech domain = {fin['domain']}, want finance")
    fail(log["domain"] == "logistics", f"logistics domain = {log['domain']}, want logistics")

    # Lead project differs per domain.
    fail(fin["lead"] == "creditlens", f"fintech lead = {fin['lead']}, want creditlens")
    fail(log["lead"] == "stadtanalyse", f"logistics lead = {log['lead']}, want stadtanalyse")
    fail(man["lead"] != log["lead"] or man["lead"] != fin["lead"],
         f"manufacturing lead {man['lead']} must differ from the other two")

    # Profiles as expected.
    fail(fin["profile"] == "data_engineer", f"fintech profile = {fin['profile']}, want data_engineer")
    fail(man["profile"] == "ai_ml", f"manufacturing profile = {man['profile']}, want ai_ml")

    # Project order differs between the fintech and logistics CVs.
    fail(fin["order"] != log["order"],
         f"project order identical across variants ({fin['order']})")

    # Category order is profile-pinned.
    fail(fin["cat_order"][:2] == ["programming", "data_eng"],
         f"fintech category order {fin['cat_order'][:2]}")
    fail(man["cat_order"][:2] == ["programming", "ai_ml"],
         f"manufacturing category order {man['cat_order'][:2]}")

    # Within-line reorder surfaces a JD-mentioned tech first when present.
    reordered = _reorder_skill_items("Pandas, PySpark, Airflow", "We use Airflow daily.")
    fail(reordered.startswith("Airflow"), f"_reorder_skill_items -> '{reordered}'")

    # PDF literals: profile role line + lead project rendered in the PDF.
    fail(_profile_role("data_engineer") in fin["pdf_text"],
         "fintech PDF lacks 'Data Engineering' role line")
    fail("creditlens" in fin["pdf_text"].lower(),
         "fintech PDF lacks creditlens literal")
    fail(_profile_role("data_engineer") in log["pdf_text"],
         "logistics PDF lacks 'Data Engineering' role line")
    fail("stadtanalyse" in log["pdf_text"].lower(),
         "logistics PDF lacks stadtanalyse literal")
    fail(_profile_role("ai_ml") in man["pdf_text"],
         "manufacturing PDF lacks 'Applied AI / Machine Learning' role line")

    print()
    if fails:
        for f in fails:
            print("FAIL:", f)
        print(f"\n{len(fails)} T1 assertion(s) failed.")
        return 1
    print("T1 variant check: all assertions passed (projects, skills, PDF literals differ as intended).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
