"""
Converts a docx to PDF using LibreOffice headless mode.

REQUIRES: LibreOffice installed on your machine (free, cross-platform).
  - Mac:     brew install --cask libreoffice
  - Windows: download from https://www.libreoffice.org/download/
  - Linux:   sudo apt install libreoffice
"""

import subprocess
import os
import re
import shutil


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
    """Lightweight page count by scanning the PDF for page objects.
    Heuristic -- good enough to warn about a resume spilling to 2 pages."""
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
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")

    pdf_name = os.path.splitext(os.path.basename(docx_path))[0] + ".pdf"
    pdf_path = os.path.join(output_dir, pdf_name)
    if not os.path.exists(pdf_path):
        raise RuntimeError(f"Expected PDF not found at {pdf_path} after conversion.")
    return pdf_path