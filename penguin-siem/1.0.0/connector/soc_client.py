import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SocServiceError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class SocServiceClient:
    def __init__(
        self,
        *,
        base_url: str,
        service_name: str,
        timeout_seconds: float,
        max_attempts: int = 2,
        backoff_seconds: float = 0.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_name = service_name
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max(1, max_attempts)
        self.backoff_seconds = max(0.0, backoff_seconds)

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        pass_through_statuses: set[int] | None = None,
    ) -> dict[str, Any]:
        cleaned_params = _clean_params(params)
        cleaned_headers = _clean_headers(headers)

        for attempt in range(self.max_attempts):
            is_last_attempt = attempt == self.max_attempts - 1
            try:
                response = httpx.request(
                    method,
                    f"{self.base_url}{path}",
                    json=json,
                    params=cleaned_params,
                    headers=cleaned_headers,
                    timeout=self.timeout_seconds,
                )
            except httpx.TimeoutException as exc:
                logger.warning(
                    "soc_service_timeout service=%s method=%s path=%s attempt=%s/%s",
                    self.service_name,
                    method.upper(),
                    path,
                    attempt + 1,
                    self.max_attempts,
                )
                if not is_last_attempt:
                    self._backoff()
                    continue
                raise SocServiceError(f"{self.service_name} timed out", status_code=504) from exc
            except httpx.RequestError as exc:
                logger.warning(
                    "soc_service_unavailable service=%s method=%s path=%s attempt=%s/%s",
                    self.service_name,
                    method.upper(),
                    path,
                    attempt + 1,
                    self.max_attempts,
                )
                if not is_last_attempt:
                    self._backoff()
                    continue
                raise SocServiceError(f"{self.service_name} is unavailable", status_code=502) from exc

            if _is_retryable_status(response.status_code) and not is_last_attempt:
                self._backoff()
                continue

            payload = _response_payload(response)
            if response.status_code >= 400:
                if pass_through_statuses and response.status_code in pass_through_statuses:
                    detail = payload.get("detail", payload)
                    raise SocServiceError(str(detail), status_code=response.status_code)
                _raise_internal_service_error(
                    service_name=self.service_name,
                    status_code=response.status_code,
                    payload=payload,
                )
            return payload

        raise RuntimeError("SOC service request retry loop exited unexpectedly")

    def _backoff(self) -> None:
        if self.backoff_seconds > 0:
            time.sleep(self.backoff_seconds)


def _clean_params(params: dict[str, Any] | None) -> dict[str, Any] | None:
    if params is None:
        return None
    return {key: value for key, value in params.items() if value is not None}


def _clean_headers(headers: dict[str, str] | None) -> dict[str, str] | None:
    if headers is None:
        return None
    return {key: value for key, value in headers.items() if value}


def _is_retryable_status(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


def _response_payload(response: httpx.Response) -> dict[str, Any]:
    if not response.content:
        return {}
    try:
        payload = response.json()
    except ValueError as exc:
        raise SocServiceError("Internal SOC service returned invalid JSON", status_code=502) from exc
    if isinstance(payload, list):
        return {"items": payload}
    if not isinstance(payload, dict):
        raise SocServiceError("Internal SOC service returned an invalid payload", status_code=502)
    return payload


def _raise_internal_service_error(
    *,
    service_name: str,
    status_code: int,
    payload: dict[str, Any],
) -> None:
    if status_code in {401, 403}:
        raise SocServiceError(
            f"{service_name} rejected gateway credentials",
            status_code=502,
        )
    if status_code == 422:
        raise SocServiceError(f"Invalid request for {service_name}", status_code=400)
    if status_code == 429:
        raise SocServiceError(f"{service_name} is temporarily rate limited", status_code=503)
    if status_code >= 500:
        raise SocServiceError(f"{service_name} returned an upstream error", status_code=502)
    raise SocServiceError(
        str(payload.get("detail", f"{service_name} request failed")),
        status_code=status_code,
    )
