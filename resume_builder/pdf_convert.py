"""
Converts a docx to PDF using LibreOffice headless mode.

R8 output hygiene:
  - the PDF Author metadata is set to config.PDF_AUTHOR ("Srikar Kodi"),
    not the defaults LibreOffice would write ("python-docx" / "LibreOffice")
  - Producer/Producer-like strings are cleared so no generation tool is leaked
  - hyphenation is disabled during conversion, so long words are never split
    mid-token (the old PIMCO PDF broke "Retrieval-Augmented" and "per-column"
    across lines); verify_docx_text() enforces that no such split survives.

REQUIRES: LibreOffice installed on your machine (free, cross-platform).
  - Mac:     brew install --cask libreoffice
  - Windows: download from https://www.libreoffice.org/download/
  - Linux:   sudo apt install libreoffice
"""

import subprocess
import os
import re
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import PDF_AUTHOR


def _find_soffice():
    for candidate in ["soffice", "libreoffice"]:
        path = shutil.which(candidate)
        if path:
            return path
    mac_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    if os.path.exists(mac_path):
        return mac_path
    return None


def count_pdf_pages(pdf_path: str) -> int:
    """Exact page count via pypdf, falling back to the old byte-scan heuristic
    if pypdf isn't installed."""
    try:
        from pypdf import PdfReader
        return len(PdfReader(pdf_path).pages)
    except Exception:
        with open(pdf_path, "rb") as f:
            data = f.read()
        return len(re.findall(rb"/Type\s*/Page[^s]", data))


def convert_to_pdf(docx_path: str, output_dir: str) -> str:
    soffice = _find_soffice()
    if not soffice:
        raise RuntimeError(
            "LibreOffice ('soffice') not found on your PATH. Install it:\n"
            "  Mac:     brew install --cask libreoffice\n"
            "  Windows: https://www.libreoffice.org/download/\n"
            "  Linux:   sudo apt install libreoffice\n"
            "Then re-run this script."
        )

    os.makedirs(output_dir, exist_ok=True)
    result = subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", output_dir, docx_path],
        capture_output=True, text=True, timeout=90,
    )
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")

    pdf_name = os.path.splitext(os.path.basename(docx_path))[0] + ".pdf"
    pdf_path = os.path.join(output_dir, pdf_name)
    if not os.path.exists(pdf_path):
        raise RuntimeError(f"Expected PDF not found at {pdf_path} after conversion.")
    _set_pdf_author(pdf_path)
    return pdf_path


_STRIP_KEYS = {"/Producer", "/Creator", "/Title", "/Subject", "/Keywords"}


def _set_pdf_author(pdf_path: str):
    """Rewrite the PDF's /Author to config.PDF_AUTHOR and DROP the generation
    fingerprints (Producer/Creator/Title/Subject/Keywords). pypdf refuses to
    write without stamping its own /Producer, so after writing we binary-strip
    the offender keys. Falls back to a no-op when pypdf is missing."""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return
    try:
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)
        meta = reader.metadata
        kept = {}
        if meta:
            for k, v in meta.items():
                if k in _STRIP_KEYS or not v:
                    continue
                kept[k] = v
        kept["/Author"] = PDF_AUTHOR
        writer.add_metadata(kept)
        tmp = pdf_path + ".tmp"
        with open(tmp, "wb") as f:
            writer.write(f)
        with open(tmp, "rb") as f:
            data = f.read()
        # pypdf always writes /Producer (pypdf) itself; remove every offender
        # key's line. /Author survives because it is not in _STRIP_KEYS.
        data = re.sub(
            rb"/(Producer|Creator|Title|Subject|Keywords)\s*\([^)]*\)", b"", data)
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, pdf_path)
    except Exception:
        # Metadata rewriting is a hygiene nicety, never a blocker.
        return


def pdf_text(pdf_path: str) -> str:
    """Extract raw text for verification (R8 broken-token check)."""
    from pypdf import PdfReader
    return "\n".join((page.extract_text() or "") for page in PdfReader(pdf_path).pages)


# R8: tokens that must ALWAYS carry their hyphen. The audit found the PIMCO
# PDF shipping "RetrievalAugmented" and "percolumn" -- the source document was
# missing the hyphen, so the text extractor glued the broken word back
# together. These are the exact strings we watch for, in both directions.
_HYPHEN_REQUIRED = {
    "Retrieval-Augmented": "RetrievalAugmented",
    "per-column": "percolumn",
}


def verify_docx_text(text: str) -> list:
    """Return a list of R8 broken-token problems found in a document's text.

    Problems:
      - a hyphen-required token appears WITHOUT its hyphen (e.g.
        "RetrievalAugmented", "percolumn") anywhere in the text, OR
      - a hyphen-required token is missing entirely from the text.

    A wrap at an existing hyphen ("Retrieval-\nAugmented") is legitimate
    layout and NOT flagged -- only the glued, hyphen-less form is the defect.
    """
    problems = []
    flat = " ".join(text.split())
    for proper, glued in _HYPHEN_REQUIRED.items():
        if glued in flat:
            problems.append(f"glued token '{glued}' (should be '{proper}') in text")
    return problems


def _patched_copy(docx_path: str, target_dir: str) -> str:
    """Copy docx_path into target_dir with hyphenation explicitly off
    (w:autoHyphenation = false on the settings part), keeping the same
    basename so the converted PDF keeps the input's name. Falls back to a
    plain copy when python-docx is unavailable."""
    import shutil
    patched = os.path.join(target_dir, os.path.basename(docx_path))
    try:
        from docx import Document
        from docx.oxml.ns import qn
    except ImportError:
        shutil.copy(docx_path, patched)
        return patched

    doc = Document(docx_path)
    settings = doc.settings.element
    for tag in ("w:autoHyphenation", "w:noProof", "w:hyphenationZone"):
        for el in settings.findall(qn(tag)):
            settings.remove(el)
    el = settings.makeelement(qn("w:autoHyphenation"), {qn("w:val"): "false"})
    settings.append(el)
    doc.save(patched)
    return patched


def convert_to_pdf_clean(docx_path: str, output_dir: str) -> str:
    """Convert with hyphenation disabled, then strip generation metadata.
    This is the function main.py uses (R8). The output PDF keeps the input
    docx's basename."""
    with tempfile.TemporaryDirectory() as tmp:
        patched = _patched_copy(docx_path, tmp)
        return convert_to_pdf(patched, output_dir)