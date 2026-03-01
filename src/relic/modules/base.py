"""
Base module interface for Relic pentesting modules.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from relic.core.engine import Engine


@dataclass
class ModuleResult:
    """Standardized result from a module execution."""
    module: str = ""
    success: bool = True
    output: str = ""
    findings: list[dict[str, Any]] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)


class BaseModule(ABC):
    """All pentesting modules inherit from this."""

    name: str = "base"
    description: str = ""
    category: str = ""  # recon | exploit | post-exploit | reporting

    @abstractmethod
    async def run(self, engine: "Engine", **kwargs: Any) -> ModuleResult:
        """Execute the module's primary function."""
        ...

    @abstractmethod
    def get_commands(self, **kwargs: Any) -> list[dict[str, str]]:
        """Return a list of commands this module would execute."""
        ...
