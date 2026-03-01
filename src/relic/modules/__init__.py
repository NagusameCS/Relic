"""Relic pentesting modules — unified registry of all module categories."""

from __future__ import annotations

from typing import TYPE_CHECKING

from relic.modules.base import BaseModule, ModuleResult
from relic.modules.recon import RECON_MODULES
from relic.modules.exploit import EXPLOIT_MODULES
from relic.modules.reporting import REPORTING_MODULES
from relic.modules.web import WEB_MODULES
from relic.modules.network import NETWORK_MODULES
from relic.modules.osint import OSINT_MODULES
from relic.modules.crypto_ssl import CRYPTO_MODULES
from relic.modules.post_exploit import POST_EXPLOIT_MODULES
from relic.modules.api_testing import API_MODULES

# ═══════════════════════════════════════════════════════════════════
# Category → registry mapping
# ═══════════════════════════════════════════════════════════════════

MODULE_CATEGORIES: dict[str, dict[str, type[BaseModule]]] = {
    "recon": RECON_MODULES,
    "exploit": EXPLOIT_MODULES,
    "web": WEB_MODULES,
    "network": NETWORK_MODULES,
    "osint": OSINT_MODULES,
    "crypto": CRYPTO_MODULES,
    "post-exploit": POST_EXPLOIT_MODULES,
    "api": API_MODULES,
    "reporting": REPORTING_MODULES,
}

# Flat registry: module_name → module_class
ALL_MODULES: dict[str, type[BaseModule]] = {}
for _category_modules in MODULE_CATEGORIES.values():
    ALL_MODULES.update(_category_modules)


def get_module(name: str) -> type[BaseModule] | None:
    """Look up a module class by name across all categories."""
    return ALL_MODULES.get(name)


def list_modules(category: str | None = None) -> list[str]:
    """Return sorted module names, optionally filtered by category."""
    if category and category in MODULE_CATEGORIES:
        return sorted(MODULE_CATEGORIES[category].keys())
    return sorted(ALL_MODULES.keys())


def list_categories() -> list[str]:
    """Return sorted list of module category names."""
    return sorted(MODULE_CATEGORIES.keys())


def module_count() -> dict[str, int]:
    """Return {category: count} mapping."""
    return {cat: len(mods) for cat, mods in MODULE_CATEGORIES.items()}


__all__ = [
    "BaseModule",
    "ModuleResult",
    "MODULE_CATEGORIES",
    "ALL_MODULES",
    "get_module",
    "list_modules",
    "list_categories",
    "module_count",
]
