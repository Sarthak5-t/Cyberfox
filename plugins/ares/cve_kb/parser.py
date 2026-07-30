from __future__ import annotations

import json
import logging
import re
import urllib.parse
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

CVE_ID_RE = re.compile(r"CVE-\d{4}-\d+")
CVE_BADGE_RE = re.compile(
    r'label=(Product|Version|Vulnerability)&message=([^&]+)'
)
CWE_BADGE_RE = re.compile(r"CWE-(\d+)")
DESC_SECTION_RE = re.compile(r"### Description\s*\n(.*?)(?=\n###|\Z)", re.DOTALL)
POC_SECTION_RE = re.compile(r"### POC\s*\n(.*?)(?=\n##|\Z)", re.DOTALL)
GITHUB_URL_RE = re.compile(r"https://github\.com/\S+")
REFERENCE_URL_RE = re.compile(r"https?://[^\s)]+")


def parse_cve_list_json(path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    if not path.exists():
        logger.warning("CVE_list.json not found at %s", path)
        return [], [], []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to parse CVE_list.json: %s", e)
        return [], [], []

    entries = []
    pocs = []
    refs = []

    for raw in data:
        cve_id = (raw.get("cve") or "").strip()
        desc = (raw.get("desc") or "").strip()

        if not cve_id or not cve_id.startswith("CVE-"):
            continue

        entries.append({
            "cve_id": cve_id,
            "description": desc[:5000],
            "product": "",
            "version": "",
            "cwe": "",
            "published": "",
            "cvss": None,
            "cvss_vector": "",
            "severity": "",
            "source": "repo",
        })

        for poc_url in (raw.get("poc") or []):
            poc_url = poc_url.strip()
            if not poc_url:
                continue
            if poc_url.startswith("https://github.com/"):
                repo_name = poc_url.replace("https://github.com/", "").rstrip("/")
                pocs.append({"cve_id": cve_id, "url": poc_url, "repo_name": repo_name})
            elif poc_url.startswith("http"):
                refs.append({"cve_id": cve_id, "url": poc_url, "source": "cve_list_json"})

    return entries, pocs, refs


def parse_markdown_file(path: Path) -> tuple[dict | None, list[dict], list[dict]]:
    try:
        text = path.read_text("utf-8", errors="replace")
    except OSError as e:
        logger.warning("Failed to read %s: %s", path, e)
        return None, [], []

    cve_match = CVE_ID_RE.search(path.name)
    if not cve_match:
        cve_match = CVE_ID_RE.search(text)
    if not cve_match:
        return None, [], []
    cve_id = cve_match.group(0)

    description = ""
    m = DESC_SECTION_RE.search(text)
    if m:
        description = m.group(1).strip()
        description = re.sub(r"\s+", " ", description)

    product = ""
    version = ""
    cwe = ""
    for m in CVE_BADGE_RE.finditer(text):
        label = m.group(1)
        value = urllib.parse.unquote_plus(m.group(2)).strip()
        if label == "Product":
            product = value
        elif label == "Version":
            version = value
        elif label == "Vulnerability":
            cwe_match = CWE_BADGE_RE.search(value)
            if cwe_match:
                cwe = cwe_match.group(1)

    if not cwe:
        cwe_match = CWE_BADGE_RE.search(text)
        if cwe_match:
            cwe = cwe_match.group(1)

    cvss = None

    if not description:
        fallback = text[:500].replace("\n", " ").strip()[:200]
        description = fallback

    entry = {
        "cve_id": cve_id,
        "description": description[:5000],
        "product": product[:200],
        "version": version[:200],
        "cwe": cwe[:20],
        "published": "",
        "cvss": cvss,
        "cvss_vector": "",
        "severity": "",
        "source": "markdown",
    }

    pocs, refs = _extract_pocs_and_refs(text, cve_id)

    return entry, pocs, refs


def _extract_pocs_and_refs(text: str, cve_id: str) -> tuple[list[dict], list[dict]]:
    pocs = []
    refs = []

    poc_sec = POC_SECTION_RE.search(text)
    if not poc_sec:
        return pocs, refs

    body = poc_sec.group(1)

    for url in GITHUB_URL_RE.findall(body):
        url = url.rstrip("/).,;")
        repo_name = url.replace("https://github.com/", "").rstrip("/")
        pocs.append({"cve_id": cve_id, "url": url, "repo_name": repo_name})

    for url in REFERENCE_URL_RE.findall(body):
        url = url.rstrip("/).,;")
        if not url.startswith("https://github.com/"):
            refs.append({"cve_id": cve_id, "url": url, "source": "markdown"})

    return pocs, refs


def iter_year_dirs(repo_root: Path) -> Iterator[Path]:
    for year_dir in sorted(repo_root.iterdir()):
        if year_dir.is_dir() and year_dir.name.isdigit():
            yield year_dir


def iter_cve_markdowns(repo_root: Path) -> Iterator[Path]:
    for year_dir in iter_year_dirs(repo_root):
        for f in sorted(year_dir.iterdir()):
            if f.is_file() and f.name.endswith(".md") and f.name.startswith("CVE-"):
                yield f


def parse_github_txt(path: Path) -> list[dict]:
    if not path.exists():
        return []
    pocs = []
    try:
        text = path.read_text("utf-8", errors="replace")
    except OSError as e:
        logger.warning("Failed to read %s: %s", path, e)
        return []
    for line in text.splitlines():
        line = line.strip()
        if " - " not in line:
            continue
        parts = line.split(" - ", 1)
        cve_id = parts[0].strip()
        url = parts[1].strip()
        if cve_id.startswith("CVE-") and url.startswith("https://github.com/"):
            repo_name = url.replace("https://github.com/", "").rstrip("/")
            pocs.append({"cve_id": cve_id, "url": url, "repo_name": repo_name})
    return pocs


def parse_references_txt(path: Path) -> list[dict]:
    if not path.exists():
        return []
    refs = []
    try:
        text = path.read_text("utf-8", errors="replace")
    except OSError as e:
        logger.warning("Failed to read %s: %s", path, e)
        return []
    for line in text.splitlines():
        line = line.strip()
        if " - " not in line:
            continue
        parts = line.split(" - ", 1)
        cve_id = parts[0].strip()
        url = parts[1].strip()
        if cve_id.startswith("CVE-"):
            refs.append({"cve_id": cve_id, "url": url, "source": "references_txt"})
    return refs
