from datetime import datetime
from typing import Any

from .fortigate_client import FortiGateApiClient, FortiGateApiError


class FortiGateConnector:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._client: FortiGateApiClient | None = None

    def _ensure_client(self) -> FortiGateApiClient:
        if self._client is None:
            self._client = FortiGateApiClient(
                host=str(self.config.get("host") or "").rstrip("/"),
                api_key=str(self.config.get("apiKey") or ""),
                verify_tls=bool(self.config.get("verifyTls", False)),
            )
        return self._client

    def health_check(self) -> dict[str, Any]:
        host = str(self.config.get("host") or "").rstrip("/")
        if not host:
            return {"ok": False, "status": "missing_host", "device": {},
                    "message": "FortiGate host is required"}
        try:
            status = self._ensure_client().get_system_status()
        except FortiGateApiError as exc:
            return {"ok": False, "status": "disconnected", "device": {},
                    "message": str(exc)}
        results = status.get("results", status) if isinstance(status, dict) else {}
        return {
            "ok": True,
            "status": "connected",
            "device": {
                "vendor": "Fortinet",
                "product": "FortiGate",
                "hostname": str(results.get("hostname") or "FortiGate"),
                "model": str(results.get("model") or ""),
                "version": str(results.get("version") or ""),
                "serial": str(results.get("serial") or ""),
            },
            "message": "FortiGate REST API reachable",
        }

    def get_widget_data(self, req: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ready", "data": {}, "meta": {"source": "fortigate"}}

    def ingest_events(self, since: datetime | None) -> list[dict[str, Any]]:
        return []

    def close(self) -> None:
        if self._client is not None:
            close = getattr(self._client, "close", None)
            if callable(close):
                close()
            self._client = None


def get_connector(config: dict[str, Any]) -> FortiGateConnector:
    return FortiGateConnector(config)
