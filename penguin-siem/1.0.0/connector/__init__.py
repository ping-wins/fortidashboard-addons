from datetime import datetime
from typing import Any

from .soc_client import SocServiceClient


_SERVICE = "siem_kowalski"


class PenguinConnector:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._client: SocServiceClient | None = None

    def _ensure_client(self) -> SocServiceClient:
        if self._client is None:
            self._client = SocServiceClient(
                base_url=str(self.config.get("host") or "").rstrip("/"),
                service_name=_SERVICE,
                timeout_seconds=float(self.config.get("timeoutSeconds", 5.0)),
            )
        return self._client

    def health_check(self) -> dict[str, Any]:
        host = str(self.config.get("host") or "").rstrip("/")
        if not host:
            return {
                "ok": False,
                "status": "missing_host",
                "device": {},
                "message": "Service URL is required",
            }
        try:
            payload = self._ensure_client().request("GET", "/health")
        except Exception as exc:
            return {
                "ok": False,
                "status": "disconnected",
                "device": {},
                "message": str(exc),
            }
        ok = str(payload.get("status") or "") == "ok"
        return {
            "ok": ok,
            "status": "connected" if ok else "disconnected",
            "device": {"vendor": "PingWins", "product": _SERVICE, "host": host},
            "message": None if ok else "Service did not report status=ok",
        }

    def get_widget_data(self, req: dict[str, Any]) -> dict[str, Any]:
        _ = req
        return {"status": "ready", "data": {}, "meta": {"source": _SERVICE}}

    def ingest_events(self, since: datetime | None) -> list[dict[str, Any]]:
        _ = since
        return []

    def close(self) -> None:
        self._client = None


def get_connector(config: dict[str, Any]) -> PenguinConnector:
    return PenguinConnector(config)
