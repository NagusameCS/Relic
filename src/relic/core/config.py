"""
Relic configuration management.

Loads config from default → user file → environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class LLMConfig(BaseModel):
    provider: str = "ollama"
    base_url: str = "http://localhost:11434"
    model: str = "glm-4.7-flash"
    temperature: float = 0.7
    max_tokens: int = 8192
    num_ctx: int = 8192
    timeout: int = 300
    fallback_model: str = "gemma3:12b"


class VMConfig(BaseModel):
    provider: str = "vagrant"
    base_image: str = "kalilinux/rolling"
    memory: int = 4096
    cpus: int = 2
    network: str = "nat"
    shared_folder: str = "./workspace"
    snapshot_on_start: bool = True
    privileged: bool = True
    unrestricted_network: bool = True


class SessionConfig(BaseModel):
    workspace_dir: str = "~/.relic/sessions"
    auto_save: bool = True
    save_interval: int = 60
    max_history: int = 10000


class ReconConfig(BaseModel):
    enabled: bool = True
    tools: list[str] = Field(default_factory=lambda: ["nmap", "whois", "dig", "subfinder", "httpx-toolkit"])


class ExploitConfig(BaseModel):
    enabled: bool = True
    tools: list[str] = Field(default_factory=lambda: ["metasploit", "sqlmap", "hydra", "john"])


class ReportingConfig(BaseModel):
    enabled: bool = True
    format: str = "markdown"
    output_dir: str = "./reports"


class ModulesConfig(BaseModel):
    recon: ReconConfig = Field(default_factory=ReconConfig)
    exploit: ExploitConfig = Field(default_factory=ExploitConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)


class UIConfig(BaseModel):
    theme: str = "relic-dark"
    show_timestamps: bool = True
    log_level: str = "INFO"
    max_output_lines: int = 5000


class ScopeConfig(BaseModel):
    """Defines the strict authorized target scope.

    Relic will REFUSE to execute any command that references hosts, domains,
    or URLs outside of ``authorized_targets``.  This is enforced at the engine
    level before any command reaches the VM.
    """

    authorized_targets: list[str] = Field(
        default_factory=lambda: ["path.opencs.dev/RelicPermission"],
        description="Exact URL paths / hosts the operator is authorized to test",
    )
    strict: bool = Field(
        default=True,
        description="When True the engine blocks any command whose target "
                    "falls outside authorized_targets",
    )
    authorization_url: str = Field(
        default="https://path.opencs.dev/RelicPermission",
        description="URL of the written authorization page",
    )


class RelicConfig(BaseModel):
    """Root configuration model."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    vm: VMConfig = Field(default_factory=VMConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)
    modules: ModulesConfig = Field(default_factory=ModulesConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    scope: ScopeConfig = Field(default_factory=ScopeConfig)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG_PATHS = [
    Path(__file__).resolve().parents[3] / "config.default.yaml",
    Path.home() / ".relic" / "config.yaml",
]


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *override* into *base*."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """Override config values from RELIC_* env vars (e.g. RELIC_LLM__MODEL)."""
    prefix = "RELIC_"
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        parts = key[len(prefix):].lower().split("__")
        node = data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return data


def load_config(extra_path: str | Path | None = None) -> RelicConfig:
    """Load and return the merged :class:`RelicConfig`."""
    raw: dict[str, Any] = {}

    paths = list(_DEFAULT_CONFIG_PATHS)
    if extra_path:
        paths.append(Path(extra_path))

    for path in paths:
        expanded = path.expanduser()
        if expanded.is_file():
            with open(expanded, "r", encoding="utf-8") as fh:
                layer = yaml.safe_load(fh) or {}
                raw = _deep_merge(raw, layer)

    raw = _apply_env_overrides(raw)
    return RelicConfig(**raw)
