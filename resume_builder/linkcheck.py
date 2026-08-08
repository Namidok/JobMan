"""
Link checker (remediation brief R7).

Verifies every URL that goes into a resume or cover letter (the candidate's
own project links + any apply/channel URLs the pipeline logs). Dead links are
reported -- and dropped from generated documents -- so the delivered PDFs
never point at a broken page.

The audit found the applied-to postings had project links that returned HTTP
errors when the PDFs were generated. This runs BEFORE conversion, right after
the documents are built, and removes any failing link from the final docx.
"""

import os
import sys
import socket
import ssl
import urllib.request
import urllib.error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fact_bank import PROJECT_ACHIEVEMENTS

CHECK_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (job-application-link-check)"


def check_url(url: str) -> tuple:
    """Return (ok: bool, status_or_error: str).

    HEAD first, then GET as a fallback (some servers reject HEAD). Any HTTP
    status below 400 counts as OK; redirects are followed."""
    if not url or not url.lower().startswith(("http://", "https://")):
        return False, "not-an-http-url"
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=CHECK_TIMEOUT) as resp:
                return True, str(resp.status)
        except urllib.error.HTTPError as e:
            if e.code < 400:
                return True, str(e.code)
            if method == "HEAD":
                continue
            return False, f"HTTP {e.code}"
        except (urllib.error.URLError, socket.timeout,
                ssl.SSLError, OSError, ValueError) as e:
            if method == "HEAD":
                continue
            return False, type(e).__name__
    return False, "HEAD and GET both failed"


def check_project_links() -> dict:
    """Check every link in the fact bank's projects. Returns
    {project_key: {label: (ok, status)}}."""
    results = {}
    for key, proj in PROJECT_ACHIEVEMENTS.items():
        results[key] = {}
        for label, url in proj.get("links") or []:
            results[key][label] = check_url(url)
    return results


def remove_dead_links(docx_path: str, dead_urls) -> int:
    """Remove hyperlinks whose URL is in dead_urls from a built docx.
    Returns how many links were removed."""
    if not dead_urls:
        return 0
    try:
        from docx import Document
        from docx.oxml.ns import qn
    except ImportError:
        return 0

    dead = set(dead_urls)
    doc = Document(docx_path)
    removed = 0
    for rel in list(doc.part.rels.values()):
        if rel.reltype.endswith("/hyperlink"):
            target = rel.target_ref or ""
            if target.rstrip("/") in dead:
                # Remove every w:hyperlink element referencing this relationship.
                for hyperlink in doc.part.element.iter(qn("w:hyperlink")):
                    if hyperlink.get(qn("r:id")) == rel.rId:
                        hyperlink.getparent().remove(hyperlink)
                        removed += 1
                doc.part.drop_rel(rel.rId)
    if removed:
        doc.save(docx_path)
    return removed


if __name__ == "__main__":
    for proj_key, links in check_project_links().items():
        for label, (ok, status) in links.items():
            print(f"[{'OK ' if ok else 'DEAD'}] {proj_key}:{label} -> {status}")
