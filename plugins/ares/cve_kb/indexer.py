from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from plugins.ares.cve_kb import db, fetcher, parser

logger = logging.getLogger(__name__)


def run(full_reindex: bool = False) -> dict:
    start = time.time()
    result = {"status": "ok", "entries_added": 0, "pocs_added": 0, "refs_added": 0, "duration_sec": 0}

    db.init_db()
    sync_result = fetcher.clone_or_pull()
    result["repo"] = sync_result

    repo_root = fetcher.repo_path()
    if not repo_root.exists():
        result["status"] = "error"
        result["error"] = "Repo directory does not exist after clone"
        return result

    if full_reindex:
        _clear_db()

    total_entries = 0
    total_pocs = 0
    total_refs = 0

    md_entries, md_pocs, md_refs = _parse_markdown_files(repo_root)
    total_entries += len(md_entries)
    total_pocs += len(md_pocs)
    total_refs += len(md_refs)

    e_added = db.bulk_insert_entries(md_entries)
    p_added = db.bulk_insert_pocs(md_pocs)
    r_added = db.bulk_insert_references(md_refs)

    entries, pocs, refs = _parse_cve_list_json(repo_root)
    total_entries += len(entries)
    total_pocs += len(pocs)
    total_refs += len(refs)

    e_added2 = db.bulk_insert_entries(entries)
    p_added2 = db.bulk_insert_pocs(pocs)
    r_added2 = db.bulk_insert_references(refs)

    txt_pocs = _parse_github_txt(repo_root)
    total_pocs += len(txt_pocs)
    p_added3 = db.bulk_insert_pocs(txt_pocs)

    txt_refs = _parse_references_txt(repo_root)
    total_refs += len(txt_refs)
    r_added3 = db.bulk_insert_references(txt_refs)

    try:
        db.rebuild_fts()
    except Exception as e:
        logger.warning("FTS rebuild failed: %s", e)

    stats = db.get_stats()
    now = datetime.now(timezone.utc).isoformat()
    db.set_metadata("last_synced", now)
    db.set_metadata("cve_count", str(stats["total_cves"]))
    db.set_metadata("poc_count", str(stats["total_poc_links"]))
    db.set_metadata("ref_count", str(stats["total_references"]))

    duration = time.time() - start
    result["entries_added"] = e_added + e_added2
    result["pocs_added"] = p_added + p_added2 + p_added3
    result["refs_added"] = r_added + r_added2 + r_added3
    result["total_parsed"] = {"entries": total_entries, "pocs": total_pocs, "refs": total_refs}
    result["stats"] = stats
    result["duration_sec"] = round(duration, 1)

    return result


def _clear_db() -> None:
    import sqlite3
    conn = sqlite3.connect(str(db.db_path()))
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        conn.executescript(
            "DELETE FROM cve_pocs; DELETE FROM cve_references; DELETE FROM cve_entries; DELETE FROM kb_metadata;"
        )
        conn.commit()
    except Exception as e:
        logger.warning("Failed to clear DB: %s", e)
    finally:
        conn.close()


def _parse_cve_list_json(repo_root: Path):
    json_path = repo_root / "docs" / "CVE_list.json"
    entries, pocs, refs = parser.parse_cve_list_json(json_path)
    logger.info("CVE_list.json: %d entries, %d PoCs, %d refs", len(entries), len(pocs), len(refs))
    return entries, pocs, refs


def _parse_markdown_files(repo_root: Path) -> tuple[list, list, list]:
    entries = []
    pocs = []
    refs = []
    count = 0
    for md_file in parser.iter_cve_markdowns(repo_root):
        entry, p, r = parser.parse_markdown_file(md_file)
        if entry:
            entries.append(entry)
            pocs.extend(p)
            refs.extend(r)
        count += 1
        if count % 10000 == 0:
            logger.info("Parsed %d markdown files...", count)
    logger.info("Markdown: %d files, %d entries, %d PoCs, %d refs", count, len(entries), len(pocs), len(refs))
    return entries, pocs, refs


def _parse_github_txt(repo_root: Path) -> list:
    txt_path = repo_root / "github-all.txt"
    pocs = parser.parse_github_txt(txt_path)
    logger.info("github-all.txt: %d PoCs", len(pocs))
    return pocs


def _parse_references_txt(repo_root: Path) -> list:
    txt_path = repo_root / "references-all.txt"
    refs = parser.parse_references_txt(txt_path)
    logger.info("references-all.txt: %d refs", len(refs))
    return refs
