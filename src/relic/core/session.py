"""
Session management — tracks pentest engagement state, history, and artifacts.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class CommandEntry(BaseModel):
    """A single command executed during the session."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "user"          # user | llm | system
    command: str = ""
    output: str = ""
    exit_code: int | None = None
    module: str = ""
    notes: str = ""


class SessionMeta(BaseModel):
    """Metadata for a pentest session."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "unnamed-session"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    target: str = ""
    scope: str = ""
    status: str = "active"        # active | paused | completed
    tags: list[str] = Field(default_factory=list)


class Session(BaseModel):
    """Full session object including history."""

    meta: SessionMeta = Field(default_factory=SessionMeta)
    history: list[CommandEntry] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    # ------------------------------------------------------------------
    # History helpers
    # ------------------------------------------------------------------

    def add_command(
        self,
        command: str,
        output: str = "",
        exit_code: int | None = None,
        source: str = "user",
        module: str = "",
    ) -> CommandEntry:
        entry = CommandEntry(
            command=command,
            output=output,
            exit_code=exit_code,
            source=source,
            module=module,
        )
        self.history.append(entry)
        self.meta.updated_at = datetime.now(timezone.utc).isoformat()
        return entry

    def add_finding(self, finding: dict[str, Any]) -> None:
        finding.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        self.findings.append(finding)

    def recent_history(self, n: int = 20) -> list[CommandEntry]:
        return self.history[-n:]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, directory: str | Path) -> Path:
        path = Path(directory).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        file = path / f"{self.meta.id}.json"
        file.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return file

    @classmethod
    def load(cls, filepath: str | Path) -> "Session":
        data = json.loads(Path(filepath).read_text(encoding="utf-8"))
        return cls(**data)


class SessionManager:
    """Manages multiple sessions and provides quick access."""

    def __init__(self, workspace_dir: str | Path = "~/.relic/sessions") -> None:
        self.workspace = Path(workspace_dir).expanduser()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._active: Session | None = None

    @property
    def active(self) -> Session | None:
        return self._active

    def new_session(self, name: str = "", target: str = "", scope: str = "") -> Session:
        session = Session(
            meta=SessionMeta(name=name or f"session-{uuid.uuid4().hex[:6]}", target=target, scope=scope)
        )
        self._active = session
        session.save(self.workspace)
        return session

    def load_session(self, session_id: str) -> Session:
        path = self.workspace / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Session {session_id} not found at {path}")
        session = Session.load(path)
        self._active = session
        return session

    def list_sessions(self) -> list[SessionMeta]:
        sessions: list[SessionMeta] = []
        for file in sorted(self.workspace.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                s = Session.load(file)
                sessions.append(s.meta)
            except Exception:
                continue
        return sessions

    def save_active(self) -> Path | None:
        if self._active:
            return self._active.save(self.workspace)
        return None
