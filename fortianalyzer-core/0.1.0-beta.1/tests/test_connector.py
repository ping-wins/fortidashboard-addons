from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import httpx


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_WIDGETS = [
    "fortianalyzer-health-preview",
    "fortianalyzer-adom-log-posture",
    "fortianalyzer-top-event-types",
    "fortianalyzer-ingestion-readiness",
]


def load_connector_module():
    entry = PACKAGE_ROOT / "connector" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "fortianalyzer_connector_test",
        entry,
        submodule_search_locations=[str(entry.parent)],
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def test_missing_host_is_graceful():
    module = load_connector_module()
    connector = module.get_connector({"host": "", "apiKey": "secret"})

    result = connector.health_check()

    assert result["ok"] is False
    assert result["status"] == "missing_host"
    assert result["device"] == {}
    assert "host" in result["message"].lower()


def test_health_check_posts_jsonrpc_status_and_normalizes_device():
    module = load_connector_module()
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == "POST"
        assert request.url.path == "/jsonrpc"
        assert request.headers["Authorization"] == "Bearer secret"
        assert json.loads(request.content.decode("utf-8")) == {
            "id": 1,
            "method": "get",
            "params": [{"url": "/sys/status"}],
        }
        return httpx.Response(
            200,
            json={
                "id": 1,
                "result": [
                    {
                        "status": {"code": 0, "message": "OK"},
                        "data": {
                            "hostname": "faza-lab",
                            "platform_str": "FortiAnalyzer-VM64",
                            "version": "v7.6.5",
                            "serial": "FAZVMTEST123",
                        },
                    }
                ],
            },
        )

    client = module.FortiAnalyzerApiClient(
        host="https://faz.local",
        api_key="secret",
        verify_tls=False,
        transport=httpx.MockTransport(handler),
    )
    connector = module.FortiAnalyzerConnector(
        {"host": "https://faz.local", "apiKey": "secret", "verifyTls": False},
        client=client,
    )

    result = connector.health_check()

    assert len(requests) == 1
    assert result["ok"] is True
    assert result["status"] == "connected"
    assert result["device"] == {
        "vendor": "Fortinet",
        "product": "FortiAnalyzer",
        "hostname": "faza-lab",
        "model": "FortiAnalyzer-VM64",
        "version": "v7.6.5",
        "serial": "FAZVMTEST123",
    }


def test_http_auth_failure_is_sanitized():
    module = load_connector_module()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "trusted host check failed"})

    client = module.FortiAnalyzerApiClient(
        host="https://faz.local",
        api_key="secret",
        verify_tls=False,
        transport=httpx.MockTransport(handler),
    )
    connector = module.FortiAnalyzerConnector(
        {"host": "https://faz.local", "apiKey": "secret", "verifyTls": False},
        client=client,
    )

    result = connector.health_check()

    assert result["ok"] is False
    assert result["status"] == "disconnected"
    assert "trusted host" in result["message"].lower()
    assert "secret" not in result["message"]


def test_jsonrpc_error_status_is_disconnected():
    module = load_connector_module()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": 1,
                "result": [
                    {
                        "status": {
                            "code": -11,
                            "message": "No permission for the resource",
                        }
                    }
                ],
            },
        )

    client = module.FortiAnalyzerApiClient(
        host="https://faz.local",
        api_key="secret",
        verify_tls=False,
        transport=httpx.MockTransport(handler),
    )
    connector = module.FortiAnalyzerConnector(
        {"host": "https://faz.local", "apiKey": "secret", "verifyTls": False},
        client=client,
    )

    result = connector.health_check()

    assert result["ok"] is False
    assert result["status"] == "disconnected"
    assert "permission" in result["message"].lower()


def test_manifest_advertises_beta_widgets_and_playbook_capability():
    manifest = json.loads((PACKAGE_ROOT / "addon.json").read_text(encoding="utf-8"))

    assert manifest["name"] == "FortiAnalyzer Core Beta"
    assert manifest["widgets"] == EXPECTED_WIDGETS
    assert manifest["capabilities"]["playbookTarget"] is True
    assert manifest["compatibility"]["testedVersions"] == []
    assert "Beta" in manifest["compatibility"]["notes"]


def test_widget_previews_are_labeled_beta_and_unvalidated():
    module = load_connector_module()
    connector = module.get_connector(
        {"host": "https://faz.local", "apiKey": "secret", "verifyTls": False}
    )

    for widget_id in EXPECTED_WIDGETS:
        payload = connector.get_widget_data({"widget_id": widget_id})
        assert payload["status"] == "preview"
        assert payload["meta"] == {
            "source": "fortianalyzer",
            "mode": "preview",
            "applianceValidated": False,
            "beta": True,
        }
        assert payload["data"]["title"]
        assert payload["data"]["applianceValidated"] is False
        assert payload["data"]["validationRequired"] is True
    assert connector.ingest_events(None) == []


def test_playbook_action_is_draft_only_and_sanitizes_params():
    module = load_connector_module()
    connector = module.get_connector(
        {"host": "https://faz.local", "apiKey": "secret", "verifyTls": False}
    )

    actions = connector.list_playbook_actions()
    assert actions == [
        {
            "id": "review_fortianalyzer_signal",
            "label": "Draft FortiAnalyzer signal review",
            "paramsSchema": {
                "eventType": {"type": "string", "required": False},
                "adom": {"type": "string", "required": False},
                "sourceIp": {"type": "string", "required": False},
                "summary": {"type": "string", "required": False},
            },
        }
    ]

    result = connector.run_playbook_action(
        "review_fortianalyzer_signal",
        {
            "eventType": "utm.ips",
            "adom": "root",
            "sourceIp": "203.0.113.10",
            "summary": "Potential IPS burst",
            "apiKey": "secret",
        },
    )

    assert result["ok"] is True
    assert result["status"] == "drafted"
    assert result["dryRun"] is True
    assert result["applianceValidated"] is False
    assert result["params"]["eventType"] == "utm.ips"
    assert "apiKey" not in result["params"]
    assert "secret" not in json.dumps(result)
