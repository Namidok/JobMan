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
from config import (CONTACT, WORK_AUTH, SKILLS, EXPERIENCE, PROJECTS, EDUCATION,
                    VARIANTS, SPOKEN_LANGUAGES, MAX_CREDITLENS_BULLETS, SIDE_PROJECTS,
                    validate)

# Body font size. The page fitter steps this down before it cuts content --
# losing 0.5pt is cheaper than losing a bullet.
BODY_PT = 10.0

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
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(3)
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
    """Manual U+2022 bullet in the body font.

    The old version used style="List Bullet", which LibreOffice renders via
    the Symbol font as U+F0B7 -- a Private Use Area codepoint. It looks fine
    to a human and is invisible/garbled to a text parser. Drawing the bullet
    ourselves with a hanging indent keeps it as a real, extractable character.
    """
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(1.5)
    pf.left_indent = Cm(0.5)
    pf.first_line_indent = Cm(-0.35)
    run = p.add_run("\u2022\u00a0 " + text)
    run.font.size = Pt(BODY_PT)
    return p


def _skill_line(doc, label, value):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(1.5)
    r1 = p.add_run(f"{label}: ")
    r1.bold = True
    r1.font.size = Pt(BODY_PT)
    r2 = p.add_run(value)
    r2.font.size = Pt(BODY_PT)
    return p


def _job_header(doc, title, org):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(0.5)
    r1 = p.add_run(title)
    r1.bold = True
    r1.font.size = Pt(BODY_PT + 0.5)
    r2 = p.add_run(f"  \u2014  {org}")
    r2.font.size = Pt(BODY_PT + 0.5)
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
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(0.5)
    r1 = p.add_run(name)
    r1.bold = True
    r1.font.size = Pt(BODY_PT + 0.5)
    r2 = p.add_run(f"  \u2014  {stack}")
    r2.font.size = Pt(BODY_PT - 0.5)
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


def _strip_trailing_empty(doc):
    """Remove trailing empty paragraphs.

    A single empty paragraph at the end was enough to push LibreOffice into
    generating a second, completely blank page.
    """
    body = doc.element.body
    for child in list(body)[::-1]:
        if child.tag.endswith("}sectPr"):
            continue
        if child.tag.endswith("}p") and not "".join(child.itertext()).strip():
            body.remove(child)
        else:
            break


def build_resume(variant_key: str, output_path: str, matched=None):
    """variant_key: one of 'data_engineer', 'ai_ml', 'nlp'.
    matched: optional list of resume keywords found in the target JD.
    When provided, bullets and skill lines are reordered so the most
    JD-relevant content comes first (stable sort -- ties keep variant order)."""
    validate()   # refuses to build while any FILL: marker survives
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
    style.font.size = Pt(BODY_PT)

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
    r.font.size = Pt(BODY_PT)

    # Skills (most JD-relevant categories first; variant order breaks ties)
    _section_heading(doc, "TECHNICAL SKILLS")
    # The first two categories are PINNED by variant -- they are the reason
    # you are applying for this role, and they outrank JD keyword density.
    # Without this, a JD mentioning Docker/CI/CD/AWS pushes Cloud & Infra above
    # AI/ML on a machine-learning application. Only the tail gets JD-sorted.
    PINNED = 2
    pinned = variant["skill_order"][:PINNED]
    tail = sorted(variant["skill_order"][PINNED:],
                  key=lambda k: _hit_count(SKILLS[k]["items"], matched),
                  reverse=True)
    skill_order = pinned + tail
    for cat_key in skill_order:
        cat = SKILLS[cat_key]
        _skill_line(doc, cat["label"], cat["items"])
    # Pinned last by construction -- it is no longer a sortable SKILLS entry,
    # so a JD asking for German can never push it above AI/ML again.
    _skill_line(doc, "Languages (spoken)", SPOKEN_LANGUAGES)

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
    creditlens_bullets = creditlens_bullets[:MAX_CREDITLENS_BULLETS]   # page control
    for b in creditlens_bullets:
        _bullet(doc, b)

    for proj_key in SIDE_PROJECTS:
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
        r1 = p.add_run(edu["degree"]); r1.bold = True; r1.font.size = Pt(BODY_PT)
        r2 = p.add_run(f'   {edu["dates"]}'); r2.font.size = Pt(9.5); r2.font.color.rgb = GREY
        p2 = doc.add_paragraph()
        p2.paragraph_format.space_after = Pt(5)
        r3 = p2.add_run(edu["detail"]); r3.font.size = Pt(9.5); r3.font.color.rgb = GREY

    _strip_trailing_empty(doc)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc.save(output_path)
    return output_path


# ---------------------------------------------------------------------------
# Page fitter
#
# Two states are bad on a CV: a blank second page, and a second page holding
# three orphaned lines. A genuinely full second page is fine -- German
# Lebenslauf convention accepts two pages, especially with real work
# experience behind you.
#
# This renders, measures the ACTUAL page count, and if a single page is
# reachable by trimming low-value content it takes it. If one page is only
# reachable by deleting a whole project, it does NOT: it reverts to full
# content and tells you, so you decide rather than silently losing a project.
# ---------------------------------------------------------------------------

FIT_LADDER = [
    (MAX_CREDITLENS_BULLETS, list(SIDE_PROJECTS), 10.0, "full content"),
    (MAX_CREDITLENS_BULLETS, list(SIDE_PROJECTS), 9.5, "body text at 9.5pt"),
    (3, list(SIDE_PROJECTS), 9.5, "9.5pt, CreditLens capped at 3 bullets"),
    (3, list(SIDE_PROJECTS), 9.0, "9pt, CreditLens capped at 3 bullets"),
]


def _render_and_count(variant_key, output_path, matched, cl_n, sides, pt):
    import tempfile
    import resume_builder.build as _self
    from resume_builder.pdf_convert import convert_to_pdf, count_pdf_pages

    _self.MAX_CREDITLENS_BULLETS = cl_n
    _self.SIDE_PROJECTS = sides
    _self.BODY_PT = pt
    build_resume(variant_key, output_path, matched=matched)
    with tempfile.TemporaryDirectory() as tmp:
        return count_pdf_pages(convert_to_pdf(output_path, tmp))


def build_resume_fitted(variant_key, output_path, matched=None, verbose=True):
    """Build a resume, preferring one page but never silently dropping a project.

    Returns (docx_path, pages, note).
    """
    import resume_builder.build as _self

    original = (_self.MAX_CREDITLENS_BULLETS, list(_self.SIDE_PROJECTS), _self.BODY_PT)
    try:
        for cl_n, sides, pt, label in FIT_LADDER:
            pages = _render_and_count(variant_key, output_path, matched, cl_n, sides, pt)
            if pages <= 1:
                if verbose and label != "full content":
                    print(f"  (fitted to one page: {label})")
                return output_path, 1, label

        # One page isn't reachable without cutting a project. Go back to full
        # content rather than shipping the tightest, ugliest version.
        pages = _render_and_count(variant_key, output_path, matched, *original)
        if verbose:
            print(f"  ({pages} pages at full content. To force one page, drop a side "
                  f"project via SIDE_PROJECTS in config.py.)")
        return output_path, pages, "full content, 2 pages"
    finally:
        (_self.MAX_CREDITLENS_BULLETS, _self.SIDE_PROJECTS, _self.BODY_PT) = original


# Backwards-compatible alias
build_resume_one_page = build_resume_fitted


if __name__ == "__main__":
    for v in ["data_engineer", "ai_ml", "nlp"]:
        out = build_resume(
            v, os.path.join(os.path.dirname(__file__), "..", "data", f"preview_{v}.docx")
        )
        print("built", out)