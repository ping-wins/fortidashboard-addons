import json
from base64 import b64encode


def build_fortiweb_authorization(*, username: str, password: str, vdom: str) -> str:
    normalized_username = username.strip()
    normalized_password = password.strip()
    normalized_vdom = (vdom or "root").strip() or "root"
    if not normalized_username:
        raise ValueError("username is required")
    if not normalized_password:
        raise ValueError("password is required")

    compact = json.dumps(
        {
            "username": normalized_username,
            "password": normalized_password,
            "vdom": normalized_vdom,
        },
        separators=(",", ":"),
    )
    return b64encode(compact.encode("utf-8")).decode("ascii")


def runtime_auth(config: dict) -> dict:
    if config.get("apiKey"):
        return dict(config)
    authorization = build_fortiweb_authorization(
        username=str(config.get("username") or ""),
        password=str(config.get("password") or ""),
        vdom=str(config.get("vdom") or "root"),
    )
    cleaned = {key: value for key, value in config.items() if key != "password"}
    cleaned["apiKey"] = authorization
    cleaned["authorization"] = authorization
    cleaned["vdom"] = str(cleaned.get("vdom") or "root")
    return cleaned
