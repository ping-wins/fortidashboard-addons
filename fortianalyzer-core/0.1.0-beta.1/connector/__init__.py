from __future__ import annotations

from datetime import datetime
from typing import Any

from .fortianalyzer_client import FortiAnalyzerApiClient, FortiAnalyzerApiError

_PREVIEW_META = {
    "source": "fortianalyzer",
    "mode": "preview",
    "applianceValidated": False,
    "beta": True,
}

_WIDGET_PREVIEWS: dict[str, dict[str, Any]] = {
    "fortianalyzer-health-preview": {
        "title": "FortiAnalyzer health preview",
        "summary": "Credential and JSON-RPC reachability scaffold for beta validation.",
        "state": "requires_appliance_validation",
        "checks": [
            {
                "id": "api-admin",
                "label": "REST API Admin key",
                "status": "requires_validation",
            },
            {
                "id": "trusted-host",
                "label": "Trusted host allows FortiDashboard API source IP",
                "status": "requires_validation",
            },
            {
                "id": "jsonrpc-status",
                "label": "JSON-RPC /sys/status health probe",
                "status": "requires_validation",
            },
        ],
    },
    "fortianalyzer-adom-log-posture": {
        "title": "ADOM log posture preview",
        "summary": "Draft view of the ADOM and log-source checks required before ingestion.",
        "state": "preview_only",
        "checks": [
            {
                "id": "adom-scope",
                "label": "Confirm ADOM scope and read permissions",
                "status": "requires_validation",
            },
            {
                "id": "log-storage",
                "label": "Confirm event and traffic log retention",
                "status": "requires_validation",
            },
            {
                "id": "device-mapping",
                "label": "Map FortiGate devices to SOC entities",
                "status": "requires_validation",
            },
        ],
    },
    "fortianalyzer-top-event-types": {
        "title": "Top event types preview",
        "summary": "Preview taxonomy for FortiAnalyzer event categories; no live counts.",
        "state": "preview_only",
        "eventTypes": [
            {"id": "traffic", "label": "Traffic logs", "status": "not_ingesting"},
            {"id": "utm", "label": "UTM/security logs", "status": "not_ingesting"},
            {"id": "event", "label": "System events", "status": "not_ingesting"},
        ],
    },
    "fortianalyzer-ingestion-readiness": {
        "title": "Ingestion readiness preview",
        "summary": "Operator checklist before FortiAnalyzer log ingestion is promoted.",
        "state": "preview_only",
        "readiness": [
            "Validate API key and trusted host from the FortiDashboard API container.",
            "Confirm ADOM names, device inventory, and log categories.",
            "Capture real payload envelopes for normalization tests.",
            "Enable SIEM ingestion only after appliance-backed tests pass.",
        ],
    },
}


def _normalize_device(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "vendor": "Fortinet",
        "product": "FortiAnalyzer",
        "hostname": str(
            payload.get("hostname") or payload.get("hostName") or "FortiAnalyzer"
        ),
        "model": str(
            payload.get("platform_str") or payload.get("model") or "FortiAnalyzer"
        ),
        "version": str(payload.get("version") or payload.get("firmware") or ""),
        "serial": str(payload.get("serial") or payload.get("serialNumber") or ""),
    }


class FortiAnalyzerConnector:
    def __init__(
        self,
        config: dict[str, Any],
        *,
        client: FortiAnalyzerApiClient | None = None,
    ) -> None:
        self.config = config
        self._client = client

    def _ensure_client(self) -> FortiAnalyzerApiClient:
        if self._client is None:
            self._client = FortiAnalyzerApiClient(
                host=str(self.config.get("host") or "").rstrip("/"),
                api_key=str(self.config.get("apiKey") or ""),
                verify_tls=bool(self.config.get("verifyTls", False)),
            )
        return self._client

    def health_check(self) -> dict[str, Any]:
        host = str(self.config.get("host") or "").rstrip("/")
        if not host:
            return {
                "ok": False,
                "status": "missing_host",
                "device": {},
                "message": "FortiAnalyzer host is required",
            }
        try:
            device = _normalize_device(self._ensure_client().get_system_status())
        except (FortiAnalyzerApiError, ValueError) as exc:
            return {
                "ok": False,
                "status": "disconnected",
                "device": {},
                "message": str(exc),
            }
        return {
            "ok": True,
            "status": "connected",
            "device": device,
            "message": "FortiAnalyzer JSON-RPC API reachable",
        }

    def get_widget_data(self, req: dict[str, Any]) -> dict[str, Any]:
        widget_id = str(req.get("widget_id") or req.get("widgetId") or "")
        preview = _WIDGET_PREVIEWS.get(
            widget_id,
            {
                "title": "FortiAnalyzer beta preview",
                "summary": "No appliance-backed widget data is available yet.",
                "state": "preview_only",
            },
        )
        return {
            "status": "preview",
            "data": {
                **preview,
                "applianceValidated": False,
                "validationRequired": True,
            },
            "meta": dict(_PREVIEW_META),
        }

    def ingest_events(self, since: datetime | None) -> list[dict[str, Any]]:
        _ = since
        return []

    def list_playbook_actions(self) -> list[dict[str, Any]]:
        return [
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

    def run_playbook_action(
        self, action_id: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        if action_id != "review_fortianalyzer_signal":
            return {
                "ok": False,
                "status": "unknown_action",
                "dryRun": True,
                "message": f"Unsupported FortiAnalyzer beta action: {action_id}",
            }
        safe_params = {
            key: value
            for key, value in params.items()
            if key in {"eventType", "adom", "sourceIp", "summary"}
        }
        return {
            "ok": True,
            "status": "drafted",
            "dryRun": True,
            "applianceValidated": False,
            "actionId": action_id,
            "params": safe_params,
            "summary": (
                "Draft FortiAnalyzer signal review. Validate the event in a real "
                "FortiAnalyzer ADOM before creating incidents or containment."
            ),
            "steps": [
                "Confirm FortiAnalyzer credentials and trusted-host access.",
                "Search the target ADOM for the referenced event type or source.",
                "Correlate matching logs with FortiGate and endpoint telemetry.",
                "Draft a SIEM ticket with observed entities and analyst notes.",
                "Do not run containment from this beta package.",
            ],
            "meta": dict(_PREVIEW_META),
        }

    def close(self) -> None:
        self._client = None


def get_connector(config: dict[str, Any]) -> FortiAnalyzerConnector:
    return FortiAnalyzerConnector(config)
