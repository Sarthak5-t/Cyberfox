"""Unit tests for Ares orchestration layer: store, tools, reflection, error handling."""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Point the engagement store to a fresh temp DB for each test."""
    db_path = tmp_path / "engagement.db"
    monkeypatch.setattr(
        "plugins.ares.state.engagement_store._db_path", lambda: db_path
    )
    # Also isolate the journal
    journal_path = tmp_path / "journal.md"
    monkeypatch.setattr(
        "plugins.ares.journal_store._journal_path", lambda: journal_path
    )
    from plugins.ares.state import engagement_store as store
    store.init_db()
    return store


@pytest.fixture
def store(_isolated_db):
    return _isolated_db


@pytest.fixture
def eng_id(store):
    """Create a default engagement and return its ID."""
    return store.create_engagement("test-eng", ["10.10.10.10"], "Find RCE")


# ═══════════════════════════════════════════════════════════════════════════
# Phase 1: Error handling — store functions
# ═══════════════════════════════════════════════════════════════════════════

class TestStoreErrorHandling:
    def test_create_engagement_returns_id(self, store):
        eid = store.create_engagement("eng1", ["10.0.0.1"], "goal")
        assert eid > 0

    def test_create_engagement_duplicate_returns_zero(self, store):
        store.create_engagement("dup")
        result = store.create_engagement("dup")
        assert result == 0

    def test_get_engagement_missing_returns_none(self, store):
        assert store.get_engagement(name="nonexistent") is None

    def test_get_engagement_by_id_missing(self, store):
        assert store.get_engagement(engagement_id=99999) is None

    def test_list_engagements_empty(self, store):
        assert store.list_engagements() == []

    def test_list_engagements_returns_data(self, store, eng_id):
        result = store.list_engagements()
        assert len(result) == 1
        assert result[0]["name"] == "test-eng"

    def test_transition_state_invalid_returns_false(self, store, eng_id):
        assert store.transition_state(eng_id, "INVALID_STATE") is False

    def test_transition_state_valid(self, store, eng_id):
        assert store.transition_state(eng_id, "recon") is True
        eng = store.get_engagement(engagement_id=eng_id)
        assert eng.state == "recon"

    def test_save_entity_returns_id(self, store, eng_id):
        eid = store.save_entity(eng_id, "host", "10.0.0.1")
        assert eid > 0

    def test_save_entity_upsert(self, store, eng_id):
        id1 = store.save_entity(eng_id, "host", "10.0.0.1", data={"a": 1})
        id2 = store.save_entity(eng_id, "host", "10.0.0.1", data={"a": 2})
        # Upsert: SQLite returns lastrowid=0 on conflict, but entity is updated
        e = store.get_entity_by_name(eng_id, "host", "10.0.0.1")
        assert e is not None
        assert e.data["a"] == 2

    def test_get_entity_missing(self, store):
        assert store.get_entity(99999) is None

    def test_query_entities_empty(self, store, eng_id):
        assert store.query_entities(eng_id) == []

    def test_query_entities_by_type(self, store, eng_id):
        store.save_entity(eng_id, "host", "10.0.0.1")
        store.save_entity(eng_id, "port", "80/tcp")
        hosts = store.query_entities(eng_id, entity_type="host")
        assert len(hosts) == 1
        assert hosts[0].name == "10.0.0.1"

    def test_query_entities_by_name_pattern(self, store, eng_id):
        store.save_entity(eng_id, "host", "10.0.0.1")
        store.save_entity(eng_id, "host", "192.168.1.1")
        result = store.query_entities(eng_id, name_pattern="10.0")
        assert len(result) == 1

    def test_get_entity_by_name(self, store, eng_id):
        store.save_entity(eng_id, "service", "Apache/2.4.57")
        e = store.get_entity_by_name(eng_id, "service", "Apache/2.4.57")
        assert e is not None
        assert e.name == "Apache/2.4.57"

    def test_get_entity_by_name_missing(self, store, eng_id):
        assert store.get_entity_by_name(eng_id, "service", "missing") is None

    def test_count_entities(self, store, eng_id):
        store.save_entity(eng_id, "host", "10.0.0.1")
        store.save_entity(eng_id, "host", "10.0.0.2")
        store.save_entity(eng_id, "port", "80/tcp")
        counts = store.count_entities(eng_id)
        assert counts == {"host": 2, "port": 1}

    def test_count_entities_empty(self, store, eng_id):
        assert store.count_entities(eng_id) == {}


# ═══════════════════════════════════════════════════════════════════════════
# Phase 1: Error handling — relationships
# ═══════════════════════════════════════════════════════════════════════════

class TestRelationships:
    def test_add_relationship(self, store, eng_id):
        h = store.save_entity(eng_id, "host", "10.0.0.1")
        p = store.save_entity(eng_id, "port", "80/tcp")
        rid = store.add_relationship(eng_id, h, p, "has_port")
        assert rid > 0

    def test_add_relationship_duplicate_upsert(self, store, eng_id):
        h = store.save_entity(eng_id, "host", "10.0.0.1")
        p = store.save_entity(eng_id, "port", "80/tcp")
        r1 = store.add_relationship(eng_id, h, p, "has_port", data={"x": 1})
        r2 = store.add_relationship(eng_id, h, p, "has_port", data={"x": 2})
        # Upsert succeeds — only 1 relationship, not duplicated
        neighbors = store.get_neighbors(h, direction="outgoing")
        assert len(neighbors) == 1
        rel_data = json.loads(neighbors[0]["data"])
        assert rel_data["x"] == 2

    def test_get_neighbors_outgoing(self, store, eng_id):
        h = store.save_entity(eng_id, "host", "10.0.0.1")
        p = store.save_entity(eng_id, "port", "80/tcp")
        store.add_relationship(eng_id, h, p, "has_port")
        neighbors = store.get_neighbors(h, direction="outgoing")
        assert len(neighbors) == 1
        assert neighbors[0]["target_name"] == "80/tcp"

    def test_get_neighbors_incoming(self, store, eng_id):
        h = store.save_entity(eng_id, "host", "10.0.0.1")
        p = store.save_entity(eng_id, "port", "80/tcp")
        store.add_relationship(eng_id, h, p, "has_port")
        neighbors = store.get_neighbors(p, direction="incoming")
        assert len(neighbors) == 1
        assert neighbors[0]["source_name"] == "10.0.0.1"

    def test_get_neighbors_both(self, store, eng_id):
        h = store.save_entity(eng_id, "host", "10.0.0.1")
        p = store.save_entity(eng_id, "port", "80/tcp")
        store.add_relationship(eng_id, h, p, "has_port")
        neighbors = store.get_neighbors(h, direction="both")
        assert len(neighbors) == 1

    def test_get_neighbors_filtered(self, store, eng_id):
        h = store.save_entity(eng_id, "host", "10.0.0.1")
        p = store.save_entity(eng_id, "port", "80/tcp")
        s = store.save_entity(eng_id, "service", "Apache")
        store.add_relationship(eng_id, h, p, "has_port")
        store.add_relationship(eng_id, p, s, "has_service")
        neighbors = store.get_neighbors(h, direction="both", relation="has_port")
        assert len(neighbors) == 1

    def test_get_full_graph(self, store, eng_id):
        store.save_entity(eng_id, "host", "10.0.0.1")
        store.save_entity(eng_id, "port", "80/tcp")
        graph = store.get_full_graph(eng_id)
        assert len(graph.entities) == 2
        assert len(graph.relationships) == 0


# ═══════════════════════════════════════════════════════════════════════════
# Phase 1: Error handling — plan tasks
# ═══════════════════════════════════════════════════════════════════════════

class TestPlanTasks:
    def test_create_task(self, store, eng_id):
        tid = store.create_task(eng_id, "recon", 1, "Port scan", tool="nmap_scan")
        assert tid > 0

    def test_get_next_task(self, store, eng_id):
        tid = store.create_task(eng_id, "recon", 1, "Port scan")
        task = store.get_next_task(eng_id)
        assert task is not None
        assert task.title == "Port scan"
        assert task.status == "pending"

    def test_get_next_task_empty(self, store, eng_id):
        assert store.get_next_task(eng_id) is None

    def test_update_task_status(self, store, eng_id):
        tid = store.create_task(eng_id, "recon", 1, "Port scan")
        ok = store.update_task(tid, status="completed", result="Found 3 ports")
        assert ok is True
        task = store.get_next_task(eng_id)
        assert task is None  # No more pending tasks

    def test_update_task_invalid_status(self, store, eng_id):
        tid = store.create_task(eng_id, "recon", 1, "Port scan")
        ok = store.update_task(tid, status="INVALID")
        assert ok is False

    def test_update_task_not_found(self, store, eng_id):
        ok = store.update_task(99999, status="completed")
        assert ok is False

    def test_get_tasks_all(self, store, eng_id):
        store.create_task(eng_id, "recon", 1, "Task 1")
        store.create_task(eng_id, "recon", 2, "Task 2")
        tasks = store.get_tasks(eng_id)
        assert len(tasks) == 2

    def test_get_tasks_by_status(self, store, eng_id):
        t1 = store.create_task(eng_id, "recon", 1, "Task 1")
        t2 = store.create_task(eng_id, "recon", 2, "Task 2")
        store.update_task(t1, status="completed")
        pending = store.get_tasks(eng_id, status="pending")
        assert len(pending) == 1
        completed = store.get_tasks(eng_id, status="completed")
        assert len(completed) == 1

    def test_get_tasks_by_phase(self, store, eng_id):
        store.create_task(eng_id, "recon", 1, "Task 1")
        store.create_task(eng_id, "scanning", 1, "Task 2")
        recon = store.get_tasks(eng_id, phase="recon")
        assert len(recon) == 1

    def test_get_plan_summary(self, store, eng_id):
        store.create_task(eng_id, "recon", 1, "Task 1")
        store.create_task(eng_id, "recon", 2, "Task 2")
        summary = store.get_plan_summary(eng_id)
        assert summary["total"] == 2
        assert summary["pending"] == 2
        assert summary["completed"] == 0
        assert summary["percent"] == 0

    def test_dependency_chain(self, store, eng_id):
        t1 = store.create_task(eng_id, "recon", 1, "Scan")
        t2 = store.create_task(eng_id, "scanning", 1, "Exploit", depends_on=t1)
        # Next task should be t1 (no deps)
        task = store.get_next_task(eng_id)
        assert task.id == t1
        # Complete t1
        store.update_task(t1, status="completed")
        # Now t2 should be next
        task = store.get_next_task(eng_id)
        assert task.id == t2


# ═══════════════════════════════════════════════════════════════════════════
# Phase 1: Error handling — decisions & events
# ═══════════════════════════════════════════════════════════════════════════

class TestDecisionsAndEvents:
    def test_add_decision(self, store, eng_id):
        did = store.add_decision(eng_id, "Nmap found HTTP", "Run nuclei_scan")
        assert did > 0

    def test_get_decisions(self, store, eng_id):
        store.add_decision(eng_id, "reason1", "action1")
        store.add_decision(eng_id, "reason2", "action2")
        decisions = store.get_decisions(eng_id)
        assert len(decisions) == 2
        # Most recent first
        assert decisions[0].reasoning == "reason2"

    def test_get_decisions_limit(self, store, eng_id):
        for i in range(10):
            store.add_decision(eng_id, f"reason{i}", f"action{i}")
        decisions = store.get_decisions(eng_id, limit=3)
        assert len(decisions) == 3

    def test_log_event(self, store, eng_id):
        eid = store.log_event(eng_id, "nmap_scan", {"target": "10.0.0.1"}, status="ok")
        assert eid > 0

    def test_get_events(self, store, eng_id):
        store.log_event(eng_id, "nmap_scan", status="ok")
        store.log_event(eng_id, "nuclei_scan", status="ok")
        events = store.get_events(eng_id)
        assert len(events) == 2

    def test_get_events_by_tool(self, store, eng_id):
        store.log_event(eng_id, "nmap_scan", status="ok")
        store.log_event(eng_id, "nuclei_scan", status="ok")
        events = store.get_events(eng_id, tool_name="nmap_scan")
        assert len(events) == 1


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2: Reflection hook entity extraction
# ═══════════════════════════════════════════════════════════════════════════

class TestReflectionExtractors:
    def test_nmap_extract_ports(self):
        from plugins.ares.hooks.reflection import _extract_nmap
        output = """Nmap scan report for 10.0.0.1
22/tcp open ssh OpenSSH 8.9
80/tcp open http Apache/2.4.57
443/tcp open ssl nginx/1.18.0"""
        entities = _extract_nmap(output, {"target": "10.0.0.1"})
        ports = [e for e in entities if e["type"] == "port"]
        services = [e for e in entities if e["type"] == "service"]
        hosts = [e for e in entities if e["type"] == "host"]
        assert len(ports) == 3
        assert len(services) == 3
        assert len(hosts) == 1

    def test_nmap_extract_no_ports(self):
        from plugins.ares.hooks.reflection import _extract_nmap
        entities = _extract_nmap("All 1000 scanned ports on 10.0.0.1 are closed", {})
        assert len(entities) == 0

    def test_whatweb_extract_json(self):
        from plugins.ares.hooks.reflection import _extract_whatweb
        output = json.dumps([{
            "target": "http://10.0.0.1",
            "plugins": {
                "Apache": {"version": ["2.4.57"]},
                "WordPress": {},
                "PHP": {"version": ["8.1.0"]},
            }
        }])
        entities = _extract_whatweb(output, {})
        techs = [e for e in entities if e["type"] == "technology"]
        assert len(techs) == 3
        names = {e["name"] for e in techs}
        assert "Apache" in names
        assert "WordPress" in names

    def test_whatweb_extract_single_object(self):
        from plugins.ares.hooks.reflection import _extract_whatweb
        output = json.dumps({
            "target": "http://10.0.0.1",
            "plugins": {"Nginx": {"version": ["1.18.0"]}}
        })
        entities = _extract_whatweb(output, {})
        assert len(entities) == 1

    def test_nuclei_extract_cve(self):
        from plugins.ares.hooks.reflection import _extract_nuclei
        output = "[critical] [CVE-2024-1234] http://10.0.0.1/vuln\n[high] [CVE-2024-5678] http://10.0.0.1/other"
        entities = _extract_nuclei(output, {})
        vulns = [e for e in entities if e["type"] == "vulnerability"]
        assert len(vulns) == 2
        assert vulns[0]["name"] == "CVE-2024-1234"

    def test_nuclei_extract_findings(self):
        from plugins.ares.hooks.reflection import _extract_nuclei
        output = "[medium] [XSS-Reflected] http://10.0.0.1/search"
        entities = _extract_nuclei(output, {})
        findings = [e for e in entities if e["type"] == "finding"]
        assert len(findings) == 1
        assert findings[0]["name"] == "XSS-Reflected"

    def test_hydra_extract_creds(self):
        from plugins.ares.hooks.reflection import _extract_hydra
        output = '[80][http-post-form] host: 10.0.0.1   login: admin   password: admin123'
        entities = _extract_hydra(output, {})
        assert len(entities) == 1
        assert entities[0]["type"] == "credential"
        assert entities[0]["data"]["username"] == "admin"

    def test_subfinder_extract(self):
        from plugins.ares.hooks.reflection import _extract_subfinder
        output = "app.example.com\napi.example.com\ndev.example.com"
        entities = _extract_subfinder(output, {"domain": "example.com"})
        assert len(entities) == 3
        assert all(e["type"] == "subdomain" for e in entities)

    def test_searchsploit_extract(self):
        from plugins.ares.hooks.reflection import _extract_searchsploit
        output = "Apache httpd 2.4.57 | exploits/linux/remote/CVE-2024-1234.py"
        entities = _extract_searchsploit(output, {"query": "apache"})
        vulns = [e for e in entities if e["type"] == "vulnerability"]
        assert len(vulns) == 1
        assert vulns[0]["name"] == "CVE-2024-1234"

    def test_sqlmap_extract(self):
        from plugins.ares.hooks.reflection import _extract_sqlmap
        output = "sqlmap identified the following injection point(s):\nType: boolean-based blind"
        entities = _extract_sqlmap(output, {"url": "http://10.0.0.1/vuln"})
        assert len(entities) == 1
        assert entities[0]["name"] == "SQL Injection"


# ═══════════════════════════════════════════════════════════════════════════
# Phase 5: Event bus subscribers
# ═══════════════════════════════════════════════════════════════════════════

class TestEventBusSubscribers:
    def test_http_detected_creates_tasks(self, store, eng_id):
        from plugins.ares.hooks.reflection import event_bus, HTTP_DETECTED
        store.transition_state(eng_id, "recon")
        event_bus.emit(HTTP_DETECTED, {"host": "10.0.0.1", "port": 80})
        tasks = store.get_tasks(eng_id, phase="scanning")
        titles = [t.title.lower() for t in tasks]
        assert any("vulnerability" in t for t in titles)
        assert any("directory" in t for t in titles)

    def test_http_detected_no_duplicates(self, store, eng_id):
        from plugins.ares.hooks.reflection import event_bus, HTTP_DETECTED
        store.transition_state(eng_id, "recon")
        event_bus.emit(HTTP_DETECTED, {"host": "10.0.0.1", "port": 80})
        event_bus.emit(HTTP_DETECTED, {"host": "10.0.0.1", "port": 80})
        tasks = store.get_tasks(eng_id, phase="scanning")
        assert len(tasks) == 2  # Only 2 unique tasks, not 4

    def test_smb_detected_creates_task(self, store, eng_id):
        from plugins.ares.hooks.reflection import event_bus, SMB_DETECTED
        store.transition_state(eng_id, "recon")
        event_bus.emit(SMB_DETECTED, {"host": "10.0.0.1", "port": 445})
        tasks = store.get_tasks(eng_id, phase="scanning")
        assert any("smb" in t.title.lower() for t in tasks)

    def test_wordpress_detected_creates_task(self, store, eng_id):
        from plugins.ares.hooks.reflection import event_bus, WORDPRESS_DETECTED
        store.transition_state(eng_id, "recon")
        event_bus.emit(WORDPRESS_DETECTED, {"url": "http://10.0.0.1"})
        tasks = store.get_tasks(eng_id, phase="scanning")
        assert any("wpscan" in t.title.lower() for t in tasks)

    def test_vuln_found_creates_task(self, store, eng_id):
        from plugins.ares.hooks.reflection import event_bus, VULNERABILITY_FOUND
        store.transition_state(eng_id, "recon")
        event_bus.emit(VULNERABILITY_FOUND, {"name": "CVE-2024-1234", "severity": "critical"})
        tasks = store.get_tasks(eng_id, phase="exploitation")
        assert len(tasks) == 1
        assert "CVE-2024-1234" in tasks[0].title

    def test_event_bus_subscribe_and_emit(self):
        from plugins.ares.hooks.reflection import EventBus
        bus = EventBus()
        received = []
        bus.subscribe("test_event", lambda data: received.append(data))
        bus.emit("test_event", {"key": "value"})
        assert len(received) == 1
        assert received[0]["key"] == "value"

    def test_event_bus_unsubscribe(self):
        from plugins.ares.hooks.reflection import EventBus
        bus = EventBus()
        received = []
        cb = lambda data: received.append(data)
        bus.subscribe("test_event", cb)
        bus.unsubscribe("test_event", cb)
        bus.emit("test_event", {})
        assert len(received) == 0


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2: Journal integration
# ═══════════════════════════════════════════════════════════════════════════

class TestJournalIntegration:
    def test_journal_init(self):
        from plugins.ares.journal_store import init_journal, read_journal
        init_journal("test-engagement", "10.0.0.1, example.com")
        content = read_journal()
        assert "test-engagement" in content
        assert "10.0.0.1" in content

    def test_journal_append_and_read(self):
        from plugins.ares.journal_store import init_journal, append_entry, read_journal
        init_journal("test-engagement")
        append_entry("recon", "Found 3 open ports")
        append_entry("scanning", "Nuclei found 2 CVEs")
        content = read_journal()
        assert "Found 3 open ports" in content
        assert "Nuclei found 2 CVEs" in content

    def test_journal_read_recent(self):
        from plugins.ares.journal_store import init_journal, append_entry, read_recent
        init_journal("test-engagement")
        for i in range(5):
            append_entry("test", f"Entry {i}")
        recent = read_recent(10)
        # Should return all entries since 5 < 10
        assert "Entry 0" in recent
        assert "Entry 4" in recent

    def test_journal_search(self):
        from plugins.ares.journal_store import init_journal, append_entry, search_journal
        init_journal("test-engagement")
        append_entry("recon", "Found HTTP on port 80")
        append_entry("scanning", "SQL injection found")
        results = search_journal("HTTP")
        assert "Found HTTP" in results

    def test_journal_exists(self):
        from plugins.ares.journal_store import journal_exists
        assert journal_exists() is False
        from plugins.ares.journal_store import init_journal
        init_journal("test")
        assert journal_exists() is True


# ═══════════════════════════════════════════════════════════════════════════
# Engagement lifecycle end-to-end
# ═══════════════════════════════════════════════════════════════════════════

class TestEngagementLifecycle:
    def test_full_lifecycle(self, store):
        # Create
        eid = store.create_engagement("pentest", ["10.0.0.1"], "Get root")
        assert eid > 0

        # Entities
        h = store.save_entity(eid, "host", "10.0.0.1")
        p = store.save_entity(eid, "port", "80/tcp")
        store.add_relationship(eid, h, p, "has_port")

        # Plan
        t1 = store.create_task(eid, "recon", 1, "Port scan", tool="nmap")
        t2 = store.create_task(eid, "scanning", 1, "Nuclei scan", depends_on=t1)

        # Execute plan
        store.transition_state(eid, "recon")
        assert store.get_next_task(eid).id == t1
        store.update_task(t1, status="completed", result="Found 5 ports")

        store.transition_state(eid, "scanning")
        assert store.get_next_task(eid).id == t2
        store.update_task(t2, status="completed", result="Found 2 CVEs")

        # Decision
        store.add_decision(eid, "Found critical CVE", "Attempt exploit")

        # Event
        store.log_event(eid, "nmap_scan", status="ok")

        # Verify final state
        eng = store.get_engagement(engagement_id=eid)
        assert eng.state == "scanning"
        summary = store.get_plan_summary(eid)
        assert summary["completed"] == 2
        assert summary["percent"] == 100
        entities = store.count_entities(eid)
        assert entities["host"] == 1
        assert entities["port"] == 1

    def test_concurrent_access(self, store):
        """Test thread-safe concurrent writes."""
        eid = store.create_engagement("concurrent", ["10.0.0.1"], "test")
        errors = []

        def writer(thread_id):
            try:
                for i in range(10):
                    store.save_entity(eid, "host", f"thread{thread_id}-host{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        entities = store.query_entities(eid, entity_type="host")
        assert len(entities) == 50  # 5 threads * 10 hosts each
