"""
Builds a resume docx in the EXACT approved format/template.
This mirrors the original build_variants.js structure 1:1 -- same layout,
same section order, same styling. Only content ordering/emphasis changes
per variant; the template itself never changes.

JD AWARENESS: when the caller passes the `matched` keyword list (the resume
keywords that appeared in the actual JD), bullets and skill categories are
reordered so the most JD-relevant content appears first. This is pure
reordering of truthful content -- nothing is invented or added.
"""

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

import re
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import CONTACT, WORK_AUTH, SKILLS, EXPERIENCE, PROJECTS, EDUCATION, VARIANTS

ACCENT = RGBColor(0x2B, 0x4C, 0x7E)
GREY = RGBColor(0x55, 0x55, 0x55)
NAME_COLOR = RGBColor(0x1A, 0x1A, 0x1A)


def _hit_count(text, keywords):
    """How many of the JD-matched resume keywords appear in `text`
    (word-boundary match, so 'sql' doesn't match 'sqlite')."""
    if not keywords:
        return 0
    t = text.lower()
    return sum(1 for kw in keywords
               if re.search(r"\b" + re.escape(kw) + r"\b", t))


def _add_hyperlink(paragraph, text, url):
    part = paragraph.part
    r_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")

    color = OxmlElement("w:color")
    color.set(qn("w:val"), "2B4C7E")
    rPr.append(color)

    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(u)

    new_run.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


def _section_heading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(13)
    p.paragraph_format.space_after = Pt(5)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = ACCENT
    # bottom border
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "2")
    bottom.set(qn("w:color"), "2B4C7E")
    pBdr.append(bottom)
    pPr.append(pBdr)
    return p


def _bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(text)
    run.font.size = Pt(10)
    return p


def _skill_line(doc, label, value):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2.5)
    r1 = p.add_run(f"{label}: ")
    r1.bold = True
    r1.font.size = Pt(10)
    r2 = p.add_run(value)
    r2.font.size = Pt(10)
    return p


def _job_header(doc, title, org):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(1)
    r1 = p.add_run(title)
    r1.bold = True
    r1.font.size = Pt(10.5)
    r2 = p.add_run(f"  \u2014  {org}")
    r2.font.size = Pt(10.5)
    return p


def _job_meta(doc, location, dates):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    r1 = p.add_run(location)
    r1.italic = True
    r1.font.size = Pt(9.5)
    r1.font.color.rgb = GREY
    r2 = p.add_run(f"   |   {dates}")
    r2.italic = True
    r2.font.size = Pt(9.5)
    r2.font.color.rgb = GREY
    return p


def _project_header(doc, name, stack):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(0.5)
    r1 = p.add_run(name)
    r1.bold = True
    r1.font.size = Pt(10.5)
    r2 = p.add_run(f"  \u2014  {stack}")
    r2.font.size = Pt(9.5)
    r2.font.color.rgb = GREY
    return p


def _link_line(doc, links):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    for i, (label, url) in enumerate(links):
        if i > 0:
            sep = p.add_run("   |   ")
            sep.font.size = Pt(9)
            sep.font.color.rgb = GREY
        _add_hyperlink(p, label, url)
    return p


def build_resume(variant_key: str, output_path: str, matched=None):
    """variant_key: one of 'data_engineer', 'ai_ml', 'nlp'.
    matched: optional list of resume keywords found in the target JD.
    When provided, bullets and skill lines are reordered so the most
    JD-relevant content comes first (stable sort -- ties keep variant order)."""
    variant = VARIANTS[variant_key]
    matched = matched or []

    doc = Document()
    section = doc.sections[0]
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    section.top_margin = Cm(1.1)
    section.bottom_margin = Cm(1.1)
    section.left_margin = Cm(1.27)
    section.right_margin = Cm(1.27)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10)

    # Name
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(CONTACT["name"])
    r.bold = True
    r.font.size = Pt(20)
    r.font.color.rgb = NAME_COLOR

    # Title line
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(variant["title_line"])
    r.bold = True
    r.font.size = Pt(11.5)
    r.font.color.rgb = ACCENT

    # Contact line
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(1)
    r = p.add_run(f'{CONTACT["location"]}  |  {CONTACT["phone"]}  |  {CONTACT["email"]}')
    r.font.size = Pt(9)
    r.font.color.rgb = GREY

    # Links line
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(1)
    _add_hyperlink(p, CONTACT["site_label"], CONTACT["site"])
    sep = p.add_run("   |   "); sep.font.size = Pt(9); sep.font.color.rgb = GREY
    _add_hyperlink(p, CONTACT["linkedin_label"], CONTACT["linkedin"])
    sep = p.add_run("   |   "); sep.font.size = Pt(9); sep.font.color.rgb = GREY
    _add_hyperlink(p, CONTACT["github_label"], CONTACT["github"])

    # Work auth
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(WORK_AUTH)
    r.font.size = Pt(8.5)
    r.font.color.rgb = GREY

    # Summary
    _section_heading(doc, "SUMMARY")
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(5)
    r = p.add_run(variant["summary"])
    r.font.size = Pt(10)

    # Skills (most JD-relevant categories first; variant order breaks ties)
    _section_heading(doc, "TECHNICAL SKILLS")
    skill_order = sorted(variant["skill_order"],
                         key=lambda k: _hit_count(SKILLS[k]["items"], matched),
                         reverse=True)
    for cat_key in skill_order:
        cat = SKILLS[cat_key]
        _skill_line(doc, cat["label"], cat["items"])

    # Experience (most JD-relevant bullets first within each job)
    _section_heading(doc, "PROFESSIONAL EXPERIENCE")
    for job in EXPERIENCE:
        _job_header(doc, job["title"], job["org"])
        _job_meta(doc, job["location"], job["dates"])
        bullets = sorted(job["bullets"], key=lambda b: _hit_count(b, matched), reverse=True)
        for b in bullets:
            _bullet(doc, b)

    # Projects
    _section_heading(doc, "PROJECTS")
    creditlens = PROJECTS["creditlens"]
    _project_header(doc, creditlens["name"], creditlens["stack"])
    _link_line(doc, creditlens["links"])
    creditlens_bullets = [creditlens["bullets_bank"][key] for key in variant["creditlens_order"]]
    creditlens_bullets.sort(key=lambda b: _hit_count(b, matched), reverse=True)
    for b in creditlens_bullets:
        _bullet(doc, b)

    for proj_key in ["skillsync", "covercraft"]:
        proj = PROJECTS[proj_key]
        _project_header(doc, proj["name"], proj["stack"])
        _link_line(doc, proj["links"])
        for b in proj["bullets"]:
            _bullet(doc, b)

    # Education
    _section_heading(doc, "EDUCATION")
    for edu in EDUCATION:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(1)
        r1 = p.add_run(edu["degree"]); r1.bold = True; r1.font.size = Pt(10)
        r2 = p.add_run(f'   {edu["dates"]}'); r2.font.size = Pt(9.5); r2.font.color.rgb = GREY
        p2 = doc.add_paragraph()
        p2.paragraph_format.space_after = Pt(5)
        r3 = p2.add_run(edu["detail"]); r3.font.size = Pt(9.5); r3.font.color.rgb = GREY

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path


if __name__ == "__main__":
    for v in ["data_engineer", "ai_ml", "nlp"]:
        out = build_resume(v, f"/home/claude/jobagent/data/preview_{v}.docx")
        print("built", out)
