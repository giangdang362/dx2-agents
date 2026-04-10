import os
from typing import Any

_DEFAULT_BACKEND_HOST = "localhost"
_DEFAULT_BACKEND_PORT = "8080"
_LEGACY_WEBUI_BASE_URL = f"http://{_DEFAULT_BACKEND_HOST}:{_DEFAULT_BACKEND_PORT}"


def normalize_base_url(url: str | None) -> str:
    return str(url).rstrip("/") if url else ""


def join_url(base_url: str, path: str) -> str:
    return f"{normalize_base_url(base_url)}/{path.lstrip('/')}"


def _default_backend_host() -> str:
    return (
        os.environ.get("OPEN_WEBUI_BACKEND_HOST")
        or os.environ.get("OPEN_WEBUI_HOST")
        or _DEFAULT_BACKEND_HOST
    )


def _default_backend_port() -> str:
    return (
        os.environ.get("OPEN_WEBUI_BACKEND_PORT")
        or os.environ.get("VITE_BACKEND_PORT")
        or os.environ.get("BACKEND_PORT")
        or os.environ.get("PORT")
        or _DEFAULT_BACKEND_PORT
    )


def build_local_base_url() -> str:
    return f"http://{_default_backend_host()}:{_default_backend_port()}"


def _request_config_webui_url(request: Any = None) -> str:
    try:
        return normalize_base_url(request.app.state.config.WEBUI_URL)
    except Exception:
        return ""


def _request_base_url(request: Any = None) -> str:
    try:
        return normalize_base_url(str(request.base_url))
    except Exception:
        return ""


def _env_webui_url() -> str:
    return normalize_base_url(
        os.environ.get("OPEN_WEBUI_BASE_URL") or os.environ.get("WEBUI_URL")
    )


def resolve_webui_base_url(
    request: Any = None,
    explicit_base_url: str | None = None,
) -> str:
    explicit = normalize_base_url(explicit_base_url)
    if explicit and explicit != _LEGACY_WEBUI_BASE_URL:
        return explicit

    for candidate in (
        normalize_base_url(os.environ.get("OPEN_WEBUI_BASE_URL")),
        build_local_base_url(),
        _request_base_url(request),
        _request_config_webui_url(request),
        _env_webui_url(),
    ):
        if candidate:
            return candidate

    return explicit or build_local_base_url()


def resolve_webui_api_base_url(
    path: str,
    request: Any = None,
    explicit_base_url: str | None = None,
) -> str:
    explicit = normalize_base_url(explicit_base_url)
    legacy_explicit = join_url(_LEGACY_WEBUI_BASE_URL, path)
    if explicit and explicit != legacy_explicit:
        return explicit

    return join_url(resolve_webui_base_url(request=request), path)
