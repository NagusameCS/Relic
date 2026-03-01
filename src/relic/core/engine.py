"""
Relic Engine — the orchestration core that ties LLM, VM, and modules together.

The engine receives user goals, consults the LLM for a plan, executes
commands inside the target VM, feeds results back to the LLM, and iterates
until the objective is met or the user intervenes.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable

from relic.core.config import RelicConfig
from relic.core.session import Session, SessionManager

log = logging.getLogger("relic.engine")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a discrete unit of work the engine will execute."""

    id: str
    description: str
    command: str = ""
    status: TaskStatus = TaskStatus.PENDING
    output: str = ""
    exit_code: int | None = None
    subtasks: list["Task"] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class EngineEvent:
    """Base class for engine events pushed to the UI."""
    pass


@dataclass
class LogEvent(EngineEvent):
    level: str = "info"
    message: str = ""


@dataclass
class CommandEvent(EngineEvent):
    command: str = ""
    source: str = "llm"


@dataclass
class OutputEvent(EngineEvent):
    text: str = ""
    stream: str = "stdout"


@dataclass
class PlanEvent(EngineEvent):
    tasks: list[dict[str, str]] = field(default_factory=list)


@dataclass
class FindingEvent(EngineEvent):
    finding: dict[str, Any] = field(default_factory=dict)


class Engine:
    """
    Core orchestration engine.

    Workflow:
        1. User provides a high-level objective (e.g. "enumerate open ports on 10.0.0.5").
        2. Engine sends the objective + context to the LLM.
        3. LLM returns a structured plan (list of commands / reasoning).
        4. Engine executes each command inside the VM via SSH.
        5. Output is captured, fed back to the LLM for analysis.
        6. Steps 3-5 repeat until the objective is fulfilled.
        7. Findings are recorded in the session.
    """

    def __init__(
        self,
        config: RelicConfig,
        session_manager: SessionManager,
        llm_client: Any = None,      # relic.llm.OllamaClient
        vm_manager: Any = None,       # relic.vm.VMManager
    ) -> None:
        self.config = config
        self.sessions = session_manager
        self.llm = llm_client
        self.vm = vm_manager
        self._running = False
        self._event_listeners: list[Callable[[EngineEvent], Any]] = []

    # ------------------------------------------------------------------
    # Event system
    # ------------------------------------------------------------------

    def on_event(self, callback: Callable[[EngineEvent], Any]) -> None:
        self._event_listeners.append(callback)

    def _emit(self, event: EngineEvent) -> None:
        for cb in self._event_listeners:
            try:
                cb(event)
            except Exception:
                log.exception("Event listener error")

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------

    async def run_objective(self, objective: str) -> None:
        """Execute a user-specified objective end-to-end."""
        session = self.sessions.active
        if session is None:
            session = self.sessions.new_session(name="auto", target=objective)

        self._running = True
        self._emit(LogEvent(level="info", message=f"Objective: {objective}"))

        iteration = 0
        max_iterations = 50  # safety cap

        while self._running and iteration < max_iterations:
            iteration += 1
            self._emit(LogEvent(level="info", message=f"--- Iteration {iteration} ---"))

            # 1. Build chat messages from session state and ask the LLM
            messages = self._build_messages(session, objective)
            llm_response = await self._ask_llm(messages)
            if llm_response is None:
                self._emit(LogEvent(level="error", message="LLM returned empty response"))
                break

            # 2. Parse commands from response
            plan = self._parse_plan(llm_response)
            if not plan:
                self._emit(LogEvent(level="info", message="LLM indicates objective complete."))
                break

            self._emit(PlanEvent(tasks=[{"command": t.command, "description": t.description} for t in plan]))

            # 3. Execute each task
            for task in plan:
                if not self._running:
                    break
                await self._execute_task(task, session)

        self._running = False
        self.sessions.save_active()
        self._emit(LogEvent(level="info", message="Objective processing complete."))

    async def run_single_command(self, command: str) -> str:
        """Execute a single command in the VM and return output."""
        # Scope guard applies to single commands too
        if not self._is_in_scope(command):
            blocked_msg = (
                f"[relic] BLOCKED — command targets a host/path outside the "
                f"authorized scope ({', '.join(self.config.scope.authorized_targets)}). "
                f"Command: {command}"
            )
            self._emit(LogEvent(level="warn", message=blocked_msg))
            return blocked_msg

        session = self.sessions.active
        self._emit(CommandEvent(command=command, source="user"))

        output, exit_code = await self._vm_exec(command)
        self._emit(OutputEvent(text=output))

        if session:
            session.add_command(command=command, output=output, exit_code=exit_code, source="user")
            self.sessions.save_active()

        return output

    def stop(self) -> None:
        """Cancel the current objective loop."""
        self._running = False
        self._emit(LogEvent(level="warn", message="Engine stopped by user."))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    _SYSTEM_MESSAGE_TEMPLATE: str = (
        "You are Relic, an expert penetration testing AI assistant operating "
        "inside an isolated virtual machine. You have full access to the VM "
        "and all installed security tools. Your role is to assist a licensed "
        "penetration tester in conducting an authorized security assessment.\n\n"
        "AUTHORIZED SCOPE (STRICT):\n"
        "  Target: {scope}\n"
        "  Authorization: {auth_url}\n"
        "  You MUST confine ALL commands to the target above.\n"
        "  Do NOT scan, enumerate, or interact with any other host, path, or \n"
        "  subdomain — even on the same domain. Anything outside the exact \n"
        "  target URL is OUT OF SCOPE and must be refused.\n\n"
        "Rules:\n"
        '- Always output your next actions as a JSON array of objects: '
        '[{{"command": "...", "description": "..."}}]\n'
        "- If the objective is complete, return an empty array: []\n"
        "- Be precise and methodical. Prefer targeted commands over broad scans.\n"
        "- Interpret tool output carefully and adapt your strategy.\n"
        "- Note any findings (open ports, vulnerabilities, credentials, etc.) clearly.\n"
        "- When uncertain, explain your reasoning before proposing commands.\n"
        "- NEVER target hosts or paths outside the authorized scope above."
    )

    @property
    def _SYSTEM_MESSAGE(self) -> str:
        """Build system message with the configured scope baked in."""
        scope_cfg = self.config.scope
        return self._SYSTEM_MESSAGE_TEMPLATE.format(
            scope=", ".join(scope_cfg.authorized_targets),
            auth_url=scope_cfg.authorization_url,
        )

    def _build_messages(self, session: Session, objective: str) -> list[dict[str, str]]:
        """Build a chat-style messages array from session history."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._SYSTEM_MESSAGE},
        ]

        # Seed with the objective as the first user message
        messages.append({
            "role": "user",
            "content": f"OBJECTIVE: {objective}\n\nProvide a structured penetration "
                       "testing plan as a JSON array.",
        })

        # Replay recent history as alternating assistant/user turns
        recent = session.recent_history(20)
        for entry in recent:
            # The command the LLM proposed → assistant turn
            messages.append({
                "role": "assistant",
                "content": f'{{"command": "{entry.command}", "description": ""}}',
            })
            # The resulting output → user turn (tool/environment feedback)
            output_trunc = entry.output[:3000] if entry.output else "(no output)"
            messages.append({
                "role": "user",
                "content": (
                    f"COMMAND: {entry.command}\n"
                    f"EXIT CODE: {entry.exit_code}\n"
                    f"OUTPUT:\n{output_trunc}\n\n"
                    "Analyze the output and provide the next commands as a JSON array, "
                    "or an empty array [] if the objective is met."
                ),
            })

        return messages

    async def _ask_llm(self, messages: list[dict[str, str]]) -> str | None:
        if self.llm is None:
            self._emit(LogEvent(level="error", message="No LLM client configured"))
            return None
        try:
            return await self.llm.chat(messages)
        except Exception as exc:
            self._emit(LogEvent(level="error", message=f"LLM error: {exc}"))
            return None

    def _parse_plan(self, response: str) -> list[Task]:
        """Extract a list of Tasks from the LLM JSON response."""
        import json as _json

        # Try to find JSON array in the response
        tasks: list[Task] = []
        try:
            # Find the first [ ... ] block
            start = response.index("[")
            end = response.rindex("]") + 1
            items = _json.loads(response[start:end])
            for i, item in enumerate(items):
                tasks.append(Task(
                    id=f"task-{i}",
                    description=item.get("description", ""),
                    command=item.get("command", ""),
                ))
        except (ValueError, _json.JSONDecodeError):
            log.warning("Could not parse LLM plan as JSON")
        return tasks

    # ------------------------------------------------------------------
    # Scope enforcement
    # ------------------------------------------------------------------

    # Domains / IPs that are always safe (loopback, VM-internal)
    _ALWAYS_ALLOWED = {"127.0.0.1", "localhost", "0.0.0.0", "::1"}

    def _is_in_scope(self, command: str) -> bool:
        """Return True only if *command* targets an authorized host/path.

        This is a conservative allowlist approach:
        - Pure-local commands (no host argument) are allowed.
        - Commands that reference an authorized target or localhost pass.
        - Everything else is blocked when ``scope.strict`` is True.
        """
        if not self.config.scope.strict:
            return True

        cmd_lower = command.lower()

        # Allow purely local / informational commands
        _LOCAL_PREFIXES = (
            "echo ", "cat ", "ls ", "head ", "tail ", "grep ",
            "sort ", "wc ", "awk ", "sed ", "python", "which ",
            "find ", "file ", "id", "whoami", "uname", "pwd",
            "mkdir ", "cp ", "mv ", "rm ", "chmod ", "export ",
            "cd ", "source ", "pip ",
        )
        if any(cmd_lower.startswith(p) for p in _LOCAL_PREFIXES):
            return True

        # Check against authorized targets + always-allowed
        allowed = set(self.config.scope.authorized_targets) | self._ALWAYS_ALLOWED
        for target in allowed:
            if target.lower() in cmd_lower:
                return True

        # If command doesn't mention *any* external host, it's likely local
        # (e.g. "jq ." or "sleep 2") — allow it.
        import re
        has_host_like = re.search(
            r'(?:https?://|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|[a-z0-9-]+\.[a-z]{2,})',
            cmd_lower,
        )
        if not has_host_like:
            return True

        return False

    async def _execute_task(self, task: Task, session: Session) -> None:
        # ── Scope guard ──────────────────────────────────────────────
        if not self._is_in_scope(task.command):
            blocked_msg = (
                f"[relic] BLOCKED — command targets a host/path outside the "
                f"authorized scope ({', '.join(self.config.scope.authorized_targets)}). "
                f"Command: {task.command}"
            )
            task.status = TaskStatus.FAILED
            task.output = blocked_msg
            task.exit_code = 1
            self._emit(LogEvent(level="warn", message=blocked_msg))
            session.add_command(
                command=task.command,
                output=blocked_msg,
                exit_code=1,
                source="llm",
                module=task.metadata.get("module", ""),
            )
            return

        task.status = TaskStatus.RUNNING
        self._emit(CommandEvent(command=task.command, source="llm"))
        self._emit(LogEvent(level="info", message=f"Executing: {task.description}"))

        output, exit_code = await self._vm_exec(task.command)
        task.output = output
        task.exit_code = exit_code
        task.status = TaskStatus.COMPLETED if exit_code == 0 else TaskStatus.FAILED

        self._emit(OutputEvent(text=output))
        session.add_command(
            command=task.command,
            output=output,
            exit_code=exit_code,
            source="llm",
            module=task.metadata.get("module", ""),
        )

    async def _vm_exec(self, command: str) -> tuple[str, int]:
        """Execute a command in the VM. Returns (output, exit_code)."""
        if self.vm is None:
            return ("[relic] No VM connected — command not executed.", 1)
        try:
            return await self.vm.execute(command)
        except Exception as exc:
            return (f"[relic] VM execution error: {exc}", 1)
