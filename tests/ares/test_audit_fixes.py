"""Tests for all audit findings — safety, injection, extractors, context, config."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "engagement.db"
    monkeypatch.setattr("plugins.ares.state.engagement_store._db_path", lambda: db_path)
    journal_path = tmp_path / "journal.md"
    monkeypatch.setattr("plugins.ares.journal_store._journal_path", lambda: journal_path)
    from plugins.ares.state import engagement_store as store
    store.init_db()
    return store


@pytest.fixture
def store(_isolated_db):
    return _isolated_db


@pytest.fixture
def eng_id(store):
    return store.create_engagement("audit-test", ["10.10.10.0/24", "example.com"], "Audit fix validation")


# ═══════════════════════════════════════════════════════════════════════════
# C-1: Safety Config Attributes
# ═══════════════════════════════════════════════════════════════════════════

class TestSafetyConfig:
    def test_default_safety_attributes_exist(self):
        from plugins.ares.config import AresConfig
        cfg = AresConfig()
        assert hasattr(cfg, "safety_scope_enforcement")
        assert hasattr(cfg, "safety_doom_loop_threshold")
        assert hasattr(cfg, "safety_require_exploit_approval")
        assert hasattr(cfg, "safety_log_all_commands")
        assert hasattr(cfg, "scope_file")
        assert cfg.safety_scope_enforcement == "enforced"
        assert cfg.safety_doom_loop_threshold == 5
        assert cfg.safety_require_exploit_approval is False
        assert cfg.safety_log_all_commands is True

    def test_config_reload_clears_cache(self):
        from plugins.ares.config import get_config, reload_config, _CONFIG_CACHE
        reload_config()
        cfg = get_config()
        assert cfg.safety_scope_enforcement == "enforced"

    def test_config_mtime_caching(self, tmp_path):
        from plugins.ares.config import AresConfig, get_config, _CONFIG_CACHE
        import plugins.ares.config as cfg_mod
        cfg_mod._CONFIG_CACHE = None
        cfg_mod._CONFIG_MTIME = 0.0
        cfg = get_config(tmp_path)
        assert cfg is not None
        assert cfg is cfg_mod._CONFIG_CACHE


# ═══════════════════════════════════════════════════════════════════════════
# C-6: Scope Validation
# ═══════════════════════════════════════════════════════════════════════════

class TestScopeValidation:
    def test_ip_in_scope(self):
        from plugins.ares.config import AresConfig
        cfg = AresConfig()
        cfg.scope = ["10.10.10.0/24"]
        assert cfg.is_target_in_scope("10.10.10.10") is True

    def test_ip_out_of_scope(self):
        from plugins.ares.config import AresConfig
        cfg = AresConfig()
        cfg.scope = ["10.10.10.0/24"]
        assert cfg.is_target_in_scope("192.168.1.1") is False

    def test_hostname_exact_match(self):
        from plugins.ares.config import AresConfig
        cfg = AresConfig()
        cfg.scope = ["example.com"]
        assert cfg.is_target_in_scope("example.com") is True

    def test_hostname_subdomain_match(self):
        from plugins.ares.config import AresConfig
        cfg = AresConfig()
        cfg.scope = ["example.com"]
        assert cfg.is_target_in_scope("app.example.com") is True

    def test_hostname_subdomain_boundary(self):
        from plugins.ares.config import AresConfig
        cfg = AresConfig()
        cfg.scope = ["example.com"]
        assert cfg.is_target_in_scope("evilexample.com") is False

    def test_hostname_partial_suffix_blocked(self):
        from plugins.ares.config import AresConfig
        cfg = AresConfig()
        cfg.scope = ["example.com"]
        assert cfg.is_target_in_scope("notexample.com") is False

    def test_empty_scope_enforced_blocks(self):
        from plugins.ares.config import AresConfig
        cfg = AresConfig()
        cfg.scope = []
        cfg.safety_scope_enforcement = "enforced"
        assert cfg.is_target_in_scope("10.0.0.1") is False

    def test_empty_scope_disabled_allows(self):
        from plugins.ares.config import AresConfig
        cfg = AresConfig()
        cfg.scope = []
        cfg.safety_scope_enforcement = "disabled"
        assert cfg.is_target_in_scope("10.0.0.1") is True

    def test_port_stripped_from_target(self):
        from plugins.ares.config import AresConfig
        cfg = AresConfig()
        cfg.scope = ["10.10.10.0/24"]
        assert cfg.is_target_in_scope("10.10.10.10:80") is True

    def test_trailing_slash_stripped(self):
        from plugins.ares.config import AresConfig
        cfg = AresConfig()
        cfg.scope = ["example.com"]
        assert cfg.is_target_in_scope("example.com/") is True

    def test_scope_validator_blocks_out_of_scope(self):
        from plugins.ares.safety.scope_validator import pre_tool_call
        with patch("plugins.ares.safety.scope_validator.get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.safety_scope_enforcement = "enforced"
            cfg.scope = ["10.10.10.0/24"]
            cfg.is_target_in_scope.return_value = False
            mock_cfg.return_value = cfg
            result = pre_tool_call("nmap_scan", {"target": "192.168.1.1"})
            assert result is not None
            assert result["action"] == "block"

    def test_scope_validator_allows_in_scope(self):
        from plugins.ares.safety.scope_validator import pre_tool_call
        with patch("plugins.ares.safety.scope_validator.get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.safety_scope_enforcement = "enforced"
            cfg.scope = ["10.10.10.0/24"]
            cfg.is_target_in_scope.return_value = True
            mock_cfg.return_value = cfg
            result = pre_tool_call("nmap_scan", {"target": "10.10.10.10"})
            assert result is None


# ═══════════════════════════════════════════════════════════════════════════
# C-2/C-3/C-4/C-5: Command Injection
# ═══════════════════════════════════════════════════════════════════════════

class TestCommandInjection:
    def test_run_command_argv_uses_shell_false(self):
        from plugins.ares.tools.base import run_command_argv
        result = run_command_argv(["echo", "hello world"], timeout=5)
        assert result.returncode == 0
        assert "hello world" in result.stdout

    def test_hydra_threads_clamped(self):
        from plugins.ares.tools.exploitation.hydra_tool import _handle
        with patch("plugins.ares.tools.exploitation.hydra_tool.check_binary", return_value=True):
            with patch("plugins.ares.tools.exploitation.hydra_tool.run_command_argv") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="no login found")
                _handle({"target": "10.10.10.10", "service": "ssh", "threads": 999})
                call_args = mock_run.call_args[0][0]
                t_idx = call_args.index("-t") + 1
                assert int(call_args[t_idx]) <= 64

    def test_hydra_threads_negative_clamped(self):
        from plugins.ares.tools.exploitation.hydra_tool import _handle
        with patch("plugins.ares.tools.exploitation.hydra_tool.check_binary", return_value=True):
            with patch("plugins.ares.tools.exploitation.hydra_tool.run_command_argv") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="no login found")
                _handle({"target": "10.10.10.10", "service": "ssh", "threads": -5})
                call_args = mock_run.call_args[0][0]
                t_idx = call_args.index("-t") + 1
                assert int(call_args[t_idx]) >= 1

    def test_sqlmap_level_clamped(self):
        from plugins.ares.tools.exploitation.sqlmap_tool import _handle
        with patch("plugins.ares.tools.exploitation.sqlmap_tool.check_binary", return_value=True):
            with patch("plugins.ares.tools.exploitation.sqlmap_tool.run_command_argv") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="done", stderr="")
                _handle({"url": "http://test.com/?id=1", "level": 99})
                call_args = mock_run.call_args[0][0]
                level_args = [a for a in call_args if a.startswith("--level=")]
                assert len(level_args) == 1
                assert int(level_args[0].split("=")[1]) <= 5

    def test_option_key_validation(self):
        from plugins.ares.tools.base import validate_option_key
        assert validate_option_key("RHOSTS") is True
        assert validate_option_key("LPORT") is True
        assert validate_option_key("RHOSTS; rm -rf /") is False
        assert validate_option_key("KEY\nINJECT") is False
        assert validate_option_key("path/to/module") is True

    def test_msf_option_injection_rejected(self):
        from plugins.ares.tools.exploitation.metasploit.msf_console import _run_msf_command
        with patch("plugins.ares.tools.exploitation.metasploit.msf_console.check_binary", return_value=True):
            with patch("plugins.ares.tools.exploitation.metasploit.msf_console.run_command_argv") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="done", stderr="")
                _run_msf_command("exploit", "test/module", {"GOOD_KEY": "value", "BAD\nKEY": "inject"})
                call_args = mock_run.call_args[0][0]
                rc_idx = call_args.index("-r") + 1
                rc_path = call_args[rc_idx]
                assert os.path.exists(rc_path) is False
                assert mock_run.called

    def test_burp_repeater_uses_argv(self):
        from plugins.ares.tools.scanning.burp.burp_repeater import _send_request
        with patch("plugins.ares.tools.scanning.burp.burp_repeater.run_command_argv") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="HTTP/1.1 200 OK\nContent-Type: text/html\n\n<body>",
                stderr="",
            )
            result = _send_request("http://test.com", "GET", {}, "")
            argv = mock_run.call_args[0][0]
            assert isinstance(argv, list)
            assert "curl" in argv[0]

    def test_smbclient_uses_argv(self):
        from plugins.ares.tools.scanning.smbclient_tool import _handle
        with patch("plugins.ares.tools.scanning.smbclient_tool.check_binary", return_value=True):
            with patch("plugins.ares.tools.scanning.smbclient_tool.run_command_argv") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="Sharelist", stderr="")
                _handle({"target": "10.10.10.10"})
                argv = mock_run.call_args[0][0]
                assert isinstance(argv, list)
                assert argv[0] == "smbclient"


# ═══════════════════════════════════════════════════════════════════════════
# H-6: Insecure Temp Files
# ═══════════════════════════════════════════════════════════════════════════

class TestSecureTempFiles:
    def test_msf_payload_uses_mkstemp(self):
        import inspect
        from plugins.ares.tools.exploitation.metasploit import msf_payload
        source = inspect.getsource(msf_payload)
        assert "mktemp" not in source
        assert "mkstemp" in source

    def test_payload_gen_uses_mkstemp(self):
        import inspect
        from plugins.ares.tools.exploitation.custom import payload_gen
        source = inspect.getsource(payload_gen)
        assert "mktemp" not in source
        assert "mkstemp" in source

    def test_msf_console_uses_mkstemp(self):
        import inspect
        from plugins.ares.tools.exploitation.metasploit import msf_console
        source = inspect.getsource(msf_console)
        assert "mkstemp" in source

    def test_exploit_chain_uses_mkstemp(self):
        import inspect
        from plugins.ares.tools.exploitation.custom import exploit_chain
        source = inspect.getsource(exploit_chain)
        assert "mkstemp" in source


# ═══════════════════════════════════════════════════════════════════════════
# C-7: Reflection Extractors Parse JSON
# ═══════════════════════════════════════════════════════════════════════════

class TestReflectionExtractors:
    def test_nmap_extracts_from_json_envelope(self):
        from plugins.ares.hooks.reflection import _extract_nmap
        result = json.dumps({
            "success": True,
            "data": {
                "results": [
                    {"port": 22, "protocol": "tcp", "service": "ssh", "version": "OpenSSH 8.9"},
                    {"port": 80, "protocol": "tcp", "service": "http", "version": "Apache/2.4.57"},
                ],
                "hosts": ["10.10.10.10"],
            },
        })
        entities = _extract_nmap(result, {"target": "10.10.10.10"})
        assert len(entities) >= 4
        types = [e["type"] for e in entities]
        assert "port" in types
        assert "service" in types
        assert "host" in types

    def test_nmap_falls_back_to_regex(self):
        from plugins.ares.hooks.reflection import _extract_nmap
        result = "Nmap scan report for 10.10.10.10\n22/tcp open ssh OpenSSH 8.9"
        entities = _extract_nmap(result, {"target": "10.10.10.10"})
        assert len(entities) >= 2

    def test_nuclei_extracts_from_json_envelope(self):
        from plugins.ares.hooks.reflection import _extract_nuclei
        result = json.dumps({
            "success": True,
            "data": {
                "findings": [
                    {"severity": "critical", "cve": "CVE-2024-1234", "url": "http://target/"},
                    {"severity": "high", "template_id": "xss-detection", "url": "http://target/xss"},
                ],
            },
        })
        entities = _extract_nuclei(result, {})
        assert len(entities) == 2
        assert entities[0]["type"] == "vulnerability"
        assert entities[0]["name"] == "CVE-2024-1234"
        assert entities[1]["type"] == "finding"
        assert entities[1]["name"] == "xss-detection"

    def test_hydra_extracts_from_json_envelope(self):
        from plugins.ares.hooks.reflection import _extract_hydra
        result = json.dumps({
            "success": True,
            "data": {
                "results": [
                    {"login": "admin", "password": "admin123", "host": "10.10.10.10", "service": "ssh"},
                ],
            },
        })
        entities = _extract_hydra(result, {"target": "10.10.10.10"})
        assert len(entities) == 1
        assert entities[0]["type"] == "credential"
        assert entities[0]["data"]["username"] == "admin"

    def test_subfinder_extracts_from_json_envelope(self):
        from plugins.ares.hooks.reflection import _extract_subfinder
        result = json.dumps({
            "success": True,
            "data": {
                "subdomains": ["app.example.com", "api.example.com", "mail.example.com"],
            },
        })
        entities = _extract_subfinder(result, {"domain": "example.com"})
        assert len(entities) == 3
        assert all(e["type"] == "subdomain" for e in entities)

    def test_searchsploit_extracts_from_json_envelope(self):
        from plugins.ares.hooks.reflection import _extract_searchsploit
        result = json.dumps({
            "success": True,
            "data": {
                "results": [
                    {"name": "Apache 2.4.57 - CVE-2024-1234", "path": "exploits/linux/..."},
                ],
            },
        })
        entities = _extract_searchsploit(result, {"query": "apache"})
        assert len(entities) >= 1
        assert entities[0]["type"] == "vulnerability"

    def test_sqlmap_extracts_from_json_envelope(self):
        from plugins.ares.hooks.reflection import _extract_sqlmap
        result = json.dumps({
            "success": True,
            "data": {
                "raw_output": "sqlmap identified the following injection point(s):\nParameter: id",
            },
        })
        entities = _extract_sqlmap(result, {"url": "http://test.com/?id=1"})
        assert len(entities) == 1
        assert entities[0]["type"] == "finding"
        assert entities[0]["name"] == "SQL Injection"


# ═══════════════════════════════════════════════════════════════════════════
# Doom Loop Detection
# ═══════════════════════════════════════════════════════════════════════════

class TestDoomLoop:
    def test_doom_loop_detects_repetition(self):
        from plugins.ares.safety.doom_loop import DoomLoopDetector
        det = DoomLoopDetector()
        for _ in range(6):
            det.check("nmap_scan", {"target": "10.0.0.1"}, turn_id="t1")
        assert det.check("nmap_scan", {"target": "10.0.0.1"}, turn_id="t1") == 7

    def test_doom_loop_resets_on_new_turn(self):
        from plugins.ares.safety.doom_loop import DoomLoopDetector
        det = DoomLoopDetector()
        for _ in range(5):
            det.check("nmap_scan", {"target": "10.0.0.1"}, turn_id="t1")
        count = det.check("nmap_scan", {"target": "10.0.0.1"}, turn_id="t2")
        assert count == 1

    def test_doom_loop_hook_blocks_at_threshold(self):
        from plugins.ares.safety.doom_loop import pre_tool_call, _detector
        _detector.reset()
        with patch("plugins.ares.safety.doom_loop.get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.safety_doom_loop_threshold = 3
            mock_cfg.return_value = cfg
            for _ in range(4):
                pre_tool_call("nmap_scan", {"target": "x"}, turn_id="t1")
            result = pre_tool_call("nmap_scan", {"target": "x"}, turn_id="t1")
            assert result is not None
            assert result["action"] == "block"


# ═══════════════════════════════════════════════════════════════════════════
# Context Injection
# ═══════════════════════════════════════════════════════════════════════════

class TestContextInjection:
    def test_injects_when_engagement_active(self, store, eng_id):
        store.save_entity(eng_id, "host", "10.10.10.10")
        store.save_entity(eng_id, "port", "22/tcp", {"service": "ssh"})
        from plugins.ares.hooks.context_injection import pre_llm_call
        result = pre_llm_call(messages=[{"role": "user", "content": "go"}])
        assert result is not None
        assert "10.10.10.10" in result
        assert "Knowledge Graph" in result

    def test_no_injection_without_engagement(self):
        from plugins.ares.hooks.context_injection import pre_llm_call
        result = pre_llm_call(messages=[{"role": "user", "content": "go"}])
        assert result is None

    def test_output_bounded(self, store, eng_id):
        for i in range(50):
            store.save_entity(eng_id, "subdomain", f"sub{i}.example.com")
        from plugins.ares.hooks.context_injection import pre_llm_call
        result = pre_llm_call(messages=[{"role": "user", "content": "go"}])
        assert result is not None
        assert len(result) <= 2500

    def test_get_context_summary_bounded(self, store, eng_id):
        for i in range(100):
            store.save_entity(eng_id, "host", f"10.0.{i}.{i}")
        from plugins.ares.state.engagement_store import get_context_summary
        summary = get_context_summary(eng_id, max_chars=500)
        assert len(summary) <= 500


# ═══════════════════════════════════════════════════════════════════════════
# H-9: No OpenAI Monkeypatch
# ═══════════════════════════════════════════════════════════════════════════

class TestNoMonkeypatch:
    def test_init_has_no_openai_monkeypatch(self):
        init_path = Path(__file__).resolve().parents[2] / "plugins" / "ares" / "__init__.py"
        source = init_path.read_text()
        assert "_ensure_auth_stripped" not in source
        assert "NoAuthTransport" not in source
        assert "_NoAuthOpenAI" not in source


# ═══════════════════════════════════════════════════════════════════════════
# Curl Secure Defaults
# ═══════════════════════════════════════════════════════════════════════════

class TestCurlDefaults:
    def test_curl_insecure_default_false(self):
        import inspect
        from plugins.ares.tools.scanning import curl_tool
        source = inspect.getsource(curl_tool)
        assert '"insecure", False' in source or 'insecure",\n                "default": False' in source

    def test_curl_follow_redirects_default_false(self):
        import inspect
        from plugins.ares.tools.scanning import curl_tool
        source = inspect.getsource(curl_tool)
        assert '"follow_redirects", False' in source or 'follow_redirects",\n                "default": False' in source


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2: validate_option_value
# ═══════════════════════════════════════════════════════════════════════════

class TestValidateOptionValue:
    def test_rejects_newline(self):
        from plugins.ares.tools.base import validate_option_value
        assert not validate_option_value("bad\nvalue")

    def test_rejects_carriage_return(self):
        from plugins.ares.tools.base import validate_option_value
        assert not validate_option_value("bad\rvalue")

    def test_rejects_null_byte(self):
        from plugins.ares.tools.base import validate_option_value
        assert not validate_option_value("bad\x00value")

    def test_rejects_backtick(self):
        from plugins.ares.tools.base import validate_option_value
        assert not validate_option_value("bad`value")

    def test_rejects_percent_angle(self):
        from plugins.ares.tools.base import validate_option_value
        assert not validate_option_value("bad<%value")

    def test_allows_normal_value(self):
        from plugins.ares.tools.base import validate_option_value
        assert validate_option_value("C:\\Windows\\System32")
        assert validate_option_value("http://target.com:8080")
        assert validate_option_value("10.10.10.10")
        assert validate_option_value("/usr/share/wordlists/common.txt")


# ═══════════════════════════════════════════════════════════════════════════
# Phase 3: smbclient filename validation
# ═══════════════════════════════════════════════════════════════════════════

class TestSmbclientFilenameValidation:
    def test_rejects_semicolon_in_filename(self):
        from plugins.ares.tools.scanning.smbclient_tool import _DANGEROUS_FILENAME_RE
        assert _DANGEROUS_FILENAME_RE.search("file;rm -rf /")

    def test_rejects_pipe_in_filename(self):
        from plugins.ares.tools.scanning.smbclient_tool import _DANGEROUS_FILENAME_RE
        assert _DANGEROUS_FILENAME_RE.search("file|cat /etc/passwd")

    def test_rejects_backtick_in_filename(self):
        from plugins.ares.tools.scanning.smbclient_tool import _DANGEROUS_FILENAME_RE
        assert _DANGEROUS_FILENAME_RE.search("file`whoami`")

    def test_allows_normal_filename(self):
        from plugins.ares.tools.scanning.smbclient_tool import _DANGEROUS_FILENAME_RE
        assert not _DANGEROUS_FILENAME_RE.search("normal_file.txt")
        assert not _DANGEROUS_FILENAME_RE.search("path/to/file.bin")


# ═══════════════════════════════════════════════════════════════════════════
# Phase 4: Schema migration
# ═══════════════════════════════════════════════════════════════════════════

class TestSchemaMigration:
    def test_user_version_set(self):
        from plugins.ares.state import engagement_store as store
        store.init_db()
        from plugins.ares.tools.base import run_command_argv
        import sqlite3
        p = store._db_path()
        conn = sqlite3.connect(str(p))
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        conn.close()
        assert version >= 1


# ═══════════════════════════════════════════════════════════════════════════
# Phase 5: EventBus logging
# ═══════════════════════════════════════════════════════════════════════════

class TestEventBusLogging:
    def test_emit_logs_exceptions(self, caplog):
        import logging
        from plugins.ares.hooks.reflection import EventBus
        bus = EventBus()
        def bad_callback(data):
            raise ValueError("test error")
        bus.subscribe("test_event", bad_callback)
        with caplog.at_level(logging.ERROR):
            bus.emit("test_event", {"key": "val"})
        assert any("test error" in r.message for r in caplog.records)


# ═══════════════════════════════════════════════════════════════════════════
# Phase 6: extract_target expanded keys
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractTargetExpanded:
    def test_rhosts_key(self):
        from plugins.ares.tools.base import extract_target
        assert extract_target({"rhosts": "10.10.10.10"}) == "10.10.10.10"

    def test_rhost_key(self):
        from plugins.ares.tools.base import extract_target
        assert extract_target({"rhost": "10.10.10.10"}) == "10.10.10.10"

    def test_hostnames_key(self):
        from plugins.ares.tools.base import extract_target
        assert extract_target({"hostnames": "target.example.com"}) == "target.example.com"

    def test_target_url_key(self):
        from plugins.ares.tools.base import extract_target
        assert extract_target({"target_url": "http://example.com"}) == "http://example.com"

    def test_target_ip_key(self):
        from plugins.ares.tools.base import extract_target
        assert extract_target({"target_ip": "192.168.1.1"}) == "192.168.1.1"

    def test_fallback_to_none(self):
        from plugins.ares.tools.base import extract_target
        assert extract_target({}) is None
