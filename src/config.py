"""Loads .env and config/*.yaml into typed, importable settings.

Nothing else in the codebase should call os.getenv() or open a yaml file
directly — this module is the single place configuration is assembled, so
tests can override it and there is one place to look when a setting changes.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"

load_dotenv(PROJECT_ROOT / ".env")


def _load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass(frozen=True)
class Settings:
    # Secrets (from environment only — never from yaml)
    anthropic_api_key: str | None = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY") or None)
    apollo_api_key: str | None = field(default_factory=lambda: os.getenv("APOLLO_API_KEY") or None)

    # Non-secret runtime config (from yaml, overridable by env)
    orchestrator_model: str = field(
        default_factory=lambda: os.getenv("ORCHESTRATOR_MODEL", "claude-sonnet-5")
    )
    db_path: str = field(default_factory=lambda: os.getenv("JWALT_DB_PATH", "data/leads.db"))
    log_level: str = field(default_factory=lambda: os.getenv("JWALT_LOG_LEVEL", "INFO"))
    log_path: str = field(default_factory=lambda: os.getenv("JWALT_LOG_PATH", "data/agent.log"))

    raw_settings: dict[str, Any] = field(default_factory=lambda: _load_yaml("settings.yaml"))
    raw_scoring: dict[str, Any] = field(default_factory=lambda: _load_yaml("scoring.yaml"))

    @property
    def apollo_base_url(self) -> str:
        return self.raw_settings.get("apollo", {}).get("base_url", "https://api.apollo.io/v1")

    @property
    def apollo_max_requests_per_run(self) -> int:
        return int(self.raw_settings.get("apollo", {}).get("max_requests_per_run", 25))

    @property
    def apollo_timeout_seconds(self) -> int:
        return int(self.raw_settings.get("apollo", {}).get("request_timeout_seconds", 30))

    @property
    def orchestrator_max_iterations(self) -> int:
        return int(self.raw_settings.get("orchestrator", {}).get("max_iterations", 20))

    @property
    def orchestrator_max_retries_per_step(self) -> int:
        return int(self.raw_settings.get("orchestrator", {}).get("max_retries_per_step", 2))

    def resolved_db_path(self) -> Path:
        p = Path(self.db_path)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


def get_settings() -> Settings:
    return Settings()
