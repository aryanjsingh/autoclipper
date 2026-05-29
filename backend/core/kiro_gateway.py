"""
Kiro Gateway configuration discovery.

The gateway lives next to this project in the normal local checkout:
../kiro-gateway.  Keep discovery here so provider code and legacy config checks
use the same source of truth.
"""

import os
from pathlib import Path
from typing import Dict, Optional


DEFAULT_MODEL = "claude-opus-4.8"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = "8000"

API_KEY_ENV_KEYS = (
    "KIRO_GATEWAY_API_KEY",
    "API_KIRO_GATEWAY_API_KEY",
    "PROXY_API_KEY",
)
BASE_URL_ENV_KEYS = (
    "KIRO_GATEWAY_BASE_URL",
    "KIRO_GATEWAY_URL",
    "API_KIRO_GATEWAY_URL",
)
MODEL_ENV_KEYS = (
    "KIRO_GATEWAY_MODEL",
    "API_KIRO_MODEL_NAME",
)


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def get_gateway_root() -> Path:
    configured = os.getenv("KIRO_GATEWAY_ROOT") or os.getenv("API_KIRO_GATEWAY_ROOT")
    if configured:
        return Path(configured).expanduser()
    return get_project_root().parent / "kiro-gateway"


def get_gateway_env_file() -> Path:
    configured = os.getenv("KIRO_GATEWAY_ENV_FILE")
    if configured:
        return Path(configured).expanduser()
    return get_gateway_root() / ".env"


def read_env_file(path: Optional[Path] = None) -> Dict[str, str]:
    env_path = path or get_gateway_env_file()
    values: Dict[str, str] = {}

    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value

    return values


def _first_present(keys: tuple[str, ...], file_values: Dict[str, str]) -> str:
    for key in keys:
        value = os.getenv(key) or file_values.get(key)
        if value:
            return value
    return ""


def normalize_base_url(base_url: str) -> str:
    base_url = base_url.strip().rstrip("/")
    if base_url.endswith("/chat/completions"):
        base_url = base_url[: -len("/chat/completions")]
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    return base_url


def get_gateway_api_key(configured_api_key: Optional[str] = None) -> str:
    if configured_api_key:
        return configured_api_key
    return _first_present(API_KEY_ENV_KEYS, read_env_file())


def get_gateway_base_url(configured_base_url: Optional[str] = None) -> str:
    file_values = read_env_file()
    explicit_base_url = configured_base_url or _first_present(BASE_URL_ENV_KEYS, file_values)
    if explicit_base_url:
        return normalize_base_url(explicit_base_url)

    host = os.getenv("KIRO_GATEWAY_HOST") or os.getenv("SERVER_HOST") or file_values.get("SERVER_HOST") or DEFAULT_HOST
    port = os.getenv("KIRO_GATEWAY_PORT") or os.getenv("SERVER_PORT") or file_values.get("SERVER_PORT") or DEFAULT_PORT
    if host in {"0.0.0.0", "::"}:
        host = DEFAULT_HOST

    return normalize_base_url(f"http://{host}:{port}")


def get_gateway_model(configured_model: Optional[str] = None) -> str:
    if configured_model:
        return configured_model
    return _first_present(MODEL_ENV_KEYS, read_env_file()) or DEFAULT_MODEL
