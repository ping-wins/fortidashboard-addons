from __future__ import annotations

import json as jsonlib
from typing import Any

import httpx


class FortiAnalyzerApiError(RuntimeError):
    pass


class FortiAnalyzerApiClient:
    def __init__(
        self,
        *,
        host: str,
        api_key: str,
        verify_tls: bool,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("api_key is required")
        self.host = host.rstrip("/")
        self.api_key = api_key.strip()
        self.verify_tls = verify_tls
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def get_system_status(self) -> dict[str, Any]:
        payload = self._jsonrpc("get", [{"url": "/sys/status"}])
        result = _first_result(payload)
        status = result.get("status")
        if isinstance(status, dict) and int(status.get("code", 0) or 0) != 0:
            raise FortiAnalyzerApiError(
                str(status.get("message") or "FortiAnalyzer JSON-RPC error")
            )
        data = result.get("data")
        if isinstance(data, dict):
            return data
        return result

    def _jsonrpc(self, method: str, params: list[dict[str, Any]]) -> dict[str, Any]:
        request_payload = {"id": 1, "method": method, "params": params}
        try:
            with httpx.Client(
                base_url=self.host,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                verify=self.verify_tls,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = client.post("/jsonrpc", json=request_payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise FortiAnalyzerApiError(
                _http_status_error_message(exc.response)
            ) from exc
        except httpx.RequestError as exc:
            raise FortiAnalyzerApiError(
                f"FortiAnalyzer API request failed: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise FortiAnalyzerApiError(
                "FortiAnalyzer API returned non-JSON response"
            ) from exc
        if not isinstance(payload, dict):
            raise FortiAnalyzerApiError(
                "FortiAnalyzer JSON-RPC response was not an object"
            )
        if payload.get("error"):
            raise FortiAnalyzerApiError(_json_excerpt(payload["error"]))
        return payload


def _first_result(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result")
    if isinstance(result, list) and result and isinstance(result[0], dict):
        return result[0]
    if isinstance(result, dict):
        return result
    raise FortiAnalyzerApiError(
        "FortiAnalyzer JSON-RPC response did not include a result object"
    )


def _http_status_error_message(response: httpx.Response) -> str:
    if response.status_code in (401, 403):
        prefix = (
            "FortiAnalyzer credentials rejected or trusted host/profile denied "
            "the request"
        )
    elif response.status_code == 404:
        prefix = (
            "FortiAnalyzer JSON-RPC endpoint not found; check host URL and "
            "firmware version"
        )
    else:
        prefix = f"FortiAnalyzer API request failed with HTTP {response.status_code}"
    detail = _response_error_excerpt(response)
    return f"{prefix}: {detail}" if detail else prefix


def _response_error_excerpt(
    response: httpx.Response, *, max_length: int = 240
) -> str:
    text = response.text.strip()
    if not text:
        return ""
    try:
        payload = response.json()
    except ValueError:
        excerpt = text
    else:
        excerpt = _json_excerpt(payload)
    return excerpt[:max_length]


def _json_excerpt(payload: Any, *, max_length: int = 240) -> str:
    try:
        return jsonlib.dumps(payload, sort_keys=True, separators=(",", ":"))[
            :max_length
        ]
    except TypeError:
        return str(payload)[:max_length]
