"""Small environment-based settings for the standalone web skeleton."""

from dataclasses import dataclass
import os
from urllib.parse import urlsplit


DEFAULT_CORS_ORIGINS = ("http://localhost:5173",)


def _local_origins_from_environment() -> tuple[str, ...]:
    configured = os.getenv("HAUSFLOW_CORS_ORIGINS")
    if not configured:
        return DEFAULT_CORS_ORIGINS

    origins: list[str] = []
    for value in configured.split(","):
        origin = value.strip().rstrip("/")
        if not origin:
            continue

        parsed = urlsplit(origin)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"localhost", "127.0.0.1"}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "HAUSFLOW_CORS_ORIGINS accepts only explicit local HTTP origins "
                "(localhost or 127.0.0.1)."
            )
        if origin not in origins:
            origins.append(origin)

    return tuple(origins) or DEFAULT_CORS_ORIGINS


@dataclass(frozen=True)
class Settings:
    application_name: str = "HausFlow – Projektwoche"
    version: str = "0.1.0"
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS


def get_settings() -> Settings:
    return Settings(cors_origins=_local_origins_from_environment())
