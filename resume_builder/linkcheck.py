"""
Link checker (remediation brief R7).

Verifies every URL that goes into a resume or cover letter (the candidate's
own project links + any apply/channel URLs the pipeline logs). Dead links are
reported -- and dropped from generated documents -- so the delivered PDFs
never point at a broken page.

The audit found the applied-to postings had project links that returned HTTP
errors when the PDFs were generated. This runs BEFORE conversion, right after
the documents are built, and removes any failing link from the final docx.

A dead link is a signal, not just noise: when the failing link belongs to the
project the scorer picked as the lead for this posting, the drop is announced
with a loud banner (and `python main.py --link-check` exits non-zero) instead
of a quiet one-line removal.
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


def _banner(url: str, status: str, lead: bool = False):
    kind = "DEAD LEAD-PROJECT LINK" if lead else "DEAD LINK"
    bar = "!" * 68
    print(
        "\n" + bar +
        f"\n!! {kind}: {url} -> {status}"
        f"\n!! {'This project leads the resume/letter for this posting -- fix the server' if lead else 'Link will be dropped from generated docs'}"
        "\n" + bar + "\n"
    )


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


def report_project_links(results: dict, lead_project=None) -> dict:
    """Print a status line per link and a loud banner for dead ones. When
    lead_project is given, a dead link in that project gets the strongest
    warning (its server should be fixed, not its link suppressed). Returns
    {url: (ok, status)} for every checked link."""
    flat = {}
    for key, links in results.items():
        is_lead = (lead_project is not None and key == lead_project)
        for label, (ok, status) in links.items():
            flat[label] = (ok, status)
            if ok:
                print(f"[OK   ] {key}:{label} -> {status}")
            else:
                _banner(label, status, lead=is_lead)
    return flat


def check_urls_alive(urls) -> list:
    """Convenience: run check_url() over a list, print a banner per dead one,
    and return the dead urls. Used by main.py before PDF conversion."""
    dead = []
    for u in urls:
        ok, status = check_url(u)
        if not ok:
            dead.append(u)
            _banner(u, status, lead=True)
    return dead


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
    _lead = sys.argv[1] if len(sys.argv) > 1 else None
    report_project_links(check_project_links(), lead_project=_lead)
    sys.exit(1 if any(not ok for ok, _ in sum(check_project_links().values(), [])) else 0)
