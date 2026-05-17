from datetime import datetime
from typing import Any

from .auth import runtime_auth
from .fortiweb_client import FortiWebApiClient, FortiWebApiError


def _normalize_system_status(payload: dict[str, Any]) -> dict[str, Any]:
    nested = payload.get("system") if isinstance(payload.get("system"), dict) else {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    merged = {**nested, **data, **payload}
    return {
        "hostname": str(
            merged.get("hostname")
            or merged.get("hostName")
            or merged.get("name")
            or "FortiWeb"
        ),
        "model": str(
            merged.get("model")
            or merged.get("model_name")
            or merged.get("platform")
            or "FortiWeb"
        ),
        "version": str(
            merged.get("version")
            or merged.get("firmware")
            or merged.get("firmwareVersion")
            or "unknown"
        ),
        "serial": str(merged.get("serial") or merged.get("serialNumber") or ""),
    }


class FortiWebConnector:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._client: FortiWebApiClient | None = None

    def health_check(self) -> dict[str, Any]:
        host = str(self.config.get("host") or "").rstrip("/")
        if not host:
            return {
                "ok": False,
                "status": "missing_host",
                "device": {},
                "message": "FortiWeb host is required",
            }
        try:
            runtime_config = runtime_auth(self.config)
            self._client = FortiWebApiClient(
                host=host,
                api_key=str(runtime_config.get("apiKey") or ""),
                verify_tls=bool(runtime_config.get("verifyTls", False)),
            )
            device = _normalize_system_status(self._client.get_system_status())
        except (FortiWebApiError, ValueError) as exc:
            return {
                "ok": False,
                "status": "disconnected",
                "device": {},
                "message": str(exc),
            }
        return {
            "ok": True,
            "status": "connected",
            "device": {"vendor": "Fortinet", "product": "FortiWeb", **device},
            "message": "FortiWeb REST API reachable",
        }

    def get_widget_data(self, req: dict[str, Any]) -> dict[str, Any]:
        _ = req
        return {
            "status": "ready",
            "data": {},
            "meta": {"source": "fortiweb", "mode": "push"},
        }

    def ingest_events(self, since: datetime | None) -> list[dict[str, Any]]:
        _ = since
        return []

    def list_playbook_actions(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "block_source_ip",
                "label": "Block source IP on FortiWeb",
                "paramsSchema": {"sourceIp": {"type": "string", "required": True}},
            }
        ]

    def close(self) -> None:
        if self._client is not None:
            close = getattr(self._client, "close", None)
            if callable(close):
                close()
            self._client = None


def get_connector(config: dict[str, Any]) -> FortiWebConnector:
    return FortiWebConnector(config)
