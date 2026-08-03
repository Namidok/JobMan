"""
Maintains data/postings.xlsx as a running history.

Each run of main.py creates a NEW SHEET (tab) inside this same workbook,
named with that run's date + timestamp (e.g. "2026-07-29_14-32-05").
Nothing from previous runs is ever overwritten or deleted -- full history
is preserved across every tab.

Deduplication still works across the ENTIRE file: before writing new rows,
we scan every existing sheet's posting_hash column and skip anything
already seen in any prior run, even though it now lives in a different tab.
"""

import os
import re
import hashlib
from datetime import datetime
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

COLUMNS = [
    "posting_hash", "source", "company", "title", "location",
    "date_posted", "date_collected", "jd_text", "apply_url",
    "overlap_pct", "best_variant", "gaps", "blockers", "status",
    "applied_date", "follow_up_date", "outcome", "resume_file",
]

APPLY_URL_COL_INDEX = COLUMNS.index("apply_url") + 1


def _hash_posting(company, title):
    norm_company = " ".join(company.strip().lower().split())
    norm_title = " ".join(title.strip().lower().split())
    key = f"{norm_company}|{norm_title}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _clean_url(url):
    if not url:
        return ""
    url = url.strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.IGNORECASE):
        if url.startswith("//"):
            url = "https:" + url
        elif re.match(r"^[\w.-]+\.[a-z]{2,}(/.*)?$", url, re.IGNORECASE):
            url = "https://" + url
        else:
            return ""
    if not re.match(r"^https?://[\w.-]+\.[a-z]{2,}", url, re.IGNORECASE):
        return ""
    return url


def _make_sheet_name():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def load_all_existing_hashes(xlsx_path):
    if not os.path.exists(xlsx_path):
        return set()
    wb = load_workbook(xlsx_path)
    hashes = set()
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row and row[0]:
                hashes.add(row[0])
    return hashes


def append_postings(xlsx_path, postings):
    os.makedirs(os.path.dirname(xlsx_path), exist_ok=True)
    existing = load_all_existing_hashes(xlsx_path)

    if os.path.exists(xlsx_path):
        wb = load_workbook(xlsx_path)
    else:
        wb = Workbook()
        default_sheet = wb.active
        wb.remove(default_sheet)

    sheet_name = _make_sheet_name()
    base_name = sheet_name
    counter = 1
    while sheet_name in wb.sheetnames:
        sheet_name = f"{base_name}_{counter}"
        counter += 1

    ws = wb.create_sheet(title=sheet_name)
    ws.append(COLUMNS)

    new_rows = []
    from datetime import date
    today = date.today().isoformat()

    for p in postings:
        h = _hash_posting(p["company"], p["title"])
        if h in existing:
            continue
        existing.add(h)

        clean_url = _clean_url(p.get("apply_url", ""))

        row = {
            "posting_hash": h,
            "source": p.get("source", ""),
            "company": p.get("company", ""),
            "title": p.get("title", ""),
            "location": p.get("location", ""),
            "date_posted": p.get("date_posted", ""),
            "date_collected": today,
            "jd_text": p.get("jd_text", ""),
            "apply_url": clean_url if clean_url else "N/A - broken or missing link, check source manually",
            "overlap_pct": p.get("overlap_pct", ""),
            "best_variant": p.get("best_variant", ""),
            "gaps": p.get("gaps", ""),
            "status": p.get("status", "not_applied"),
            "applied_date": p.get("applied_date", ""),
            "follow_up_date": p.get("follow_up_date", ""),
            "outcome": p.get("outcome", ""),
            "resume_file": p.get("resume_file", ""),
        }
        ws.append([row[c] for c in COLUMNS])

        if clean_url:
            cell = ws.cell(row=ws.max_row, column=APPLY_URL_COL_INDEX)
            cell.hyperlink = clean_url
            cell.font = Font(color="0563C1", underline="single")

        new_rows.append(row)

    wb.save(xlsx_path)
    print(f"New sheet '{sheet_name}' created with {len(new_rows)} new posting(s).")
    return new_rows