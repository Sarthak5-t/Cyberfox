"""Unit tests for boot-time relay self-provisioning.

Covers relay_endpoint() / relay_route_keys() / relay_instance_id() /
relay_wake_url() config readers and the _post_provision() body-shape
behaviour. The trigger path (self_provision_relay) is a dead stub — the
managed-platform access token it relied on was removed, and relay creds
must now be provided explicitly via GATEWAY_RELAY_ID / GATEWAY_RELAY_SECRET.
"""

from __future__ import annotations

import pytest

import gateway.relay as relay


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in (
        "GATEWAY_RELAY_URL",
        "GATEWAY_RELAY_ID",
        "GATEWAY_RELAY_SECRET",
        "GATEWAY_RELAY_DELIVERY_KEY",
        "GATEWAY_RELAY_ENDPOINT",
        "GATEWAY_RELAY_ROUTE_KEYS",
        "GATEWAY_RELAY_PLATFORM",
        "GATEWAY_RELAY_BOT_ID",
        "GATEWAY_RELAY_INSTANCE_ID",
        "GATEWAY_RELAY_WAKE_URL",
    ):
        monkeypatch.delenv(k, raising=False)
    # Never read config.yaml off disk in these tests.
    monkeypatch.setattr("gateway.run._load_gateway_config", lambda: {}, raising=False)


# ─────────────────────────── config readers ───────────────────────────

def test_relay_endpoint_from_env(monkeypatch):
    monkeypatch.setenv("GATEWAY_RELAY_ENDPOINT", "https://gw.example.com/inbound/")
    assert relay.relay_endpoint() == "https://gw.example.com/inbound"


def test_relay_endpoint_absent_is_none():
    assert relay.relay_endpoint() is None


def test_relay_route_keys_csv(monkeypatch):
    monkeypatch.setenv("GATEWAY_RELAY_ROUTE_KEYS", "guild-1, guild-2 ,, guild-3")
    assert relay.relay_route_keys() == ["guild-1", "guild-2", "guild-3"]


def test_relay_route_keys_empty():
    assert relay.relay_route_keys() == []


def test_relay_instance_id_from_env(monkeypatch):
    monkeypatch.setenv("GATEWAY_RELAY_INSTANCE_ID", "  inst-abc  ")
    assert relay.relay_instance_id() == "inst-abc"


def test_relay_instance_id_absent_is_none():
    assert relay.relay_instance_id() is None


def test_relay_instance_id_from_config(monkeypatch):
    monkeypatch.setattr(
        "gateway.run._load_gateway_config",
        lambda: {"gateway": {"relay_instance_id": "inst-from-config"}},
        raising=False,
    )
    assert relay.relay_instance_id() == "inst-from-config"


def test_provision_url_maps_ws_to_http():
    assert relay._provision_url("wss://c.example/relay") == "https://c.example/relay/provision"
    assert relay._provision_url("ws://c.example/relay") == "http://c.example/relay/provision"
    assert relay._provision_url("https://c.example") == "https://c.example/relay/provision"


# ─────────────────── instance-id forwarding (Phase 6 Unit α) ───────────────────

def test_post_provision_body_includes_instanceId_only_when_set(monkeypatch):
    """The real _post_provision adds `instanceId` to the JSON body ONLY when a
    value is supplied — omitting it lets the connector store null (back-compat),
    rather than binding an empty string."""
    import json

    sent: dict = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"secret": "a" * 64, "deliveryKey": "b" * 64, "tenant": "t", "gatewayId": "gw-1"}).encode()

    def _fake_urlopen(req, timeout=None):  # noqa: ANN001
        sent["body"] = json.loads(req.data.decode())
        return _Resp()

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    # With an instance id -> present in the body.
    relay._post_provision(
        provision_url="https://c.example/relay/provision",
        access_token="tok",
        gateway_id="gw-1",
        platform="discord",
        bot_id="app",
        gateway_endpoint=None,
        route_keys=[],
        instance_id="inst-abc",
    )
    assert sent["body"]["instanceId"] == "inst-abc"

    # Without one -> the key is absent entirely (not "" ).
    relay._post_provision(
        provision_url="https://c.example/relay/provision",
        access_token="tok",
        gateway_id="gw-1",
        platform="discord",
        bot_id="app",
        gateway_endpoint=None,
        route_keys=[],
    )
    assert "instanceId" not in sent["body"]


# ─────────────────── wake-url forwarding (Phase 5 Unit C) ───────────────────

def test_relay_wake_url_from_env(monkeypatch):
    """The real _post_provision adds `wakeUrl` to the JSON body ONLY when a value
    is supplied — omitting it lets the connector store null (back-compat)."""
    import json

    sent: dict = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"secret": "a" * 64, "deliveryKey": "b" * 64, "tenant": "t", "gatewayId": "gw-1"}).encode()

    def _fake_urlopen(req, timeout=None):  # noqa: ANN001
        sent["body"] = json.loads(req.data.decode())
        return _Resp()

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    # With a wake url -> present in the body.
    relay._post_provision(
        provision_url="https://c.example/relay/provision",
        access_token="tok",
        gateway_id="gw-1",
        platform="discord",
        bot_id="app",
        gateway_endpoint=None,
        route_keys=[],
        wake_url="https://wake.example/poke",
    )
    assert sent["body"]["wakeUrl"] == "https://wake.example/poke"

    # Without one -> the key is absent entirely (not "").
    relay._post_provision(
        provision_url="https://c.example/relay/provision",
        access_token="tok",
        gateway_id="gw-1",
        platform="discord",
        bot_id="app",
        gateway_endpoint=None,
        route_keys=[],
    )
    assert "wakeUrl" not in sent["body"]
