"""
Relic TUI Application — the main Textual-based terminal interface.

Pure black aesthetic with white text. All interaction flows through here.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Static,
    Button,
    DataTable,
)

from relic import BANNER, DISCLAIMER_SHORT, __version__
from relic.core.config import RelicConfig, load_config
from relic.core.engine import (
    Engine,
    EngineEvent,
    LogEvent,
    CommandEvent,
    OutputEvent,
    PlanEvent,
    FindingEvent,
)
from relic.core.session import SessionManager
from relic.llm.ollama_client import OllamaClient
from relic.ui.theme import RELIC_CSS
from relic.vm.manager import VMManager


class Sidebar(Container):
    """Left sidebar showing session and VM status."""

    def compose(self) -> ComposeResult:
        yield Static("[b]RELIC[/b]", classes="sidebar-label")
        yield Static(f"v{__version__}", classes="sidebar-item")
        yield Static("", id="spacer-1")
        yield Static("[b]SESSION[/b]", classes="sidebar-label")
        yield Static("No active session", id="session-info", classes="sidebar-item")
        yield Static("", id="spacer-2")
        yield Static("[b]VM STATUS[/b]", classes="sidebar-label")
        yield Static("● Disconnected", id="vm-status", classes="sidebar-item status-disconnected")
        yield Static("", id="spacer-3")
        yield Static("[b]LLM[/b]", classes="sidebar-label")
        yield Static("● Checking...", id="llm-status", classes="sidebar-item status-working")
        yield Static("", id="spacer-4")
        yield Static("[b]MODULES[/b]", classes="sidebar-label")
        yield Static("  recon", classes="sidebar-item")
        yield Static("  exploit", classes="sidebar-item")
        yield Static("  reporting", classes="sidebar-item")
        yield Static("", id="spacer-5")
        yield Static("[b]ACTIONS[/b]", classes="sidebar-label")
        yield Button("New Session", id="btn-new-session", classes="btn-primary")
        yield Button("Connect VM", id="btn-connect-vm")
        yield Button("Generate Report", id="btn-report")
        yield Button("Stop", id="btn-stop", classes="btn-danger")


class RelicApp(App):
    """Main Relic TUI application."""

    TITLE = "RELIC"
    SUB_TITLE = "Local LLM Pentesting Automation"
    CSS = RELIC_CSS

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+n", "new_session", "New Session", show=True),
        Binding("ctrl+s", "save_session", "Save", show=True),
        Binding("escape", "stop_engine", "Stop", show=True),
        Binding("ctrl+l", "clear_log", "Clear Log", show=True),
    ]

    def __init__(self, config: RelicConfig | None = None) -> None:
        super().__init__()
        self.config = config or load_config()
        self.session_mgr = SessionManager(self.config.session.workspace_dir)
        self.llm_client: OllamaClient | None = None
        self.vm_manager: VMManager | None = None
        self.engine: Engine | None = None

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Sidebar(id="sidebar")
            with Vertical(id="main-area"):
                yield Static(
                    DISCLAIMER_SHORT,
                    id="disclaimer",
                )
                yield RichLog(id="output-log", highlight=True, markup=True, wrap=True)
                with Horizontal(id="input-bar"):
                    yield Input(
                        placeholder="Enter objective, command, or /help ...",
                        id="prompt-input",
                    )
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def on_mount(self) -> None:
        log = self.query_one("#output-log", RichLog)
        log.write(Text(BANNER, style="bold white"))
        log.write("")
        log.write(Text("  ⚠  AUTHORIZED SECURITY TESTING ONLY  ⚠", style="bold red"))
        log.write(Text("  Unauthorized use is illegal. You accept full responsibility.", style="red"))
        log.write("")
        log.write(Text("  Type /help for commands, or enter a pentesting objective.", style="dim"))
        log.write(Text("  ─" * 35, style="dim"))
        log.write("")

        # Initialize components
        self._init_llm()
        self._init_engine()

    def _init_llm(self) -> None:
        self.llm_client = OllamaClient(self.config.llm)
        self._check_llm_status()

    def _init_engine(self) -> None:
        self.engine = Engine(
            config=self.config,
            session_manager=self.session_mgr,
            llm_client=self.llm_client,
            vm_manager=self.vm_manager,
        )
        self.engine.on_event(self._handle_engine_event)

    @work(thread=False)
    async def _check_llm_status(self) -> None:
        status = self.query_one("#llm-status", Static)
        if self.llm_client and await self.llm_client.health_check():
            try:
                active = await self.llm_client.ensure_model()
                status.update(f"[green]● {active}[/green]")
                self._log_system(f"LLM ready: [bold]{active}[/bold]")

                # Show all available models
                models = await self.llm_client.list_models()
                model_names = [m.get("name", "?") for m in models]
                self._log_system(f"Available models: {', '.join(model_names)}")
            except RuntimeError as e:
                status.update("[red]● No models[/red]")
                self._log_error(str(e))
        else:
            status.update("[red]● Offline[/red]")
            self._log_system("[yellow]LLM offline — start Ollama to enable AI features[/yellow]")

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    @on(Input.Submitted, "#prompt-input")
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        if text.startswith("/"):
            await self._handle_command(text)
        elif text.startswith("!"):
            # Direct VM command
            await self._run_vm_command(text[1:].strip())
        else:
            # Treat as an objective for the LLM
            await self._run_objective(text)

    async def _handle_command(self, text: str) -> None:
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        match cmd:
            case "/help":
                self._show_help()
            case "/session" | "/new":
                self._new_session(arg)
            case "/sessions":
                self._list_sessions()
            case "/vm":
                await self._vm_action(arg)
            case "/models":
                await self._list_models()
            case "/module":
                await self._run_module(arg)
            case "/report":
                await self._generate_report()
            case "/clear":
                self.query_one("#output-log", RichLog).clear()
            case "/quit" | "/exit":
                self.exit()
            case _:
                self._log_system(f"Unknown command: {cmd}. Type /help for available commands.")

    def _show_help(self) -> None:
        log = self.query_one("#output-log", RichLog)
        help_text = """
[bold white]═══ RELIC COMMANDS ═══[/bold white]

[bold]General:[/bold]
  [white]/help[/white]              Show this help
  [white]/clear[/white]             Clear output log
  [white]/quit[/white]              Exit Relic

[bold]Sessions:[/bold]
  [white]/session <name>[/white]    Create new session
  [white]/sessions[/white]          List saved sessions

[bold]VM Management:[/bold]
  [white]/vm start[/white]          Provision and start the VM
  [white]/vm stop[/white]           Stop the VM
  [white]/vm status[/white]         Show VM status
  [white]/vm reset[/white]          Reset VM to initial snapshot

[bold]LLM:[/bold]
  [white]/models[/white]            List available Ollama models

[bold]Modules:[/bold]
  [white]/module port-scan <target>[/white]
  [white]/module subdomain-enum <domain>[/white]
  [white]/module dns-recon <domain>[/white]
  [white]/module web-recon <url>[/white]
  [white]/module sqli <url>[/white]
  [white]/module brute-force <target>[/white]

[bold]Reporting:[/bold]
  [white]/report[/white]            Generate pentest report

[bold]Shortcuts:[/bold]
  [white]!<command>[/white]         Execute command directly in VM
  [white]<objective>[/white]        Send objective to LLM for planning

[bold]Keys:[/bold]
  [white]Ctrl+N[/white]   New Session    [white]Ctrl+S[/white]   Save Session
  [white]Ctrl+L[/white]   Clear Log      [white]Escape[/white]   Stop Engine
  [white]Ctrl+C[/white]   Quit
"""
        log.write(help_text)

    # ------------------------------------------------------------------
    # Session actions
    # ------------------------------------------------------------------

    def _new_session(self, name: str = "") -> None:
        session = self.session_mgr.new_session(name=name or "relic-session")
        info = self.query_one("#session-info", Static)
        info.update(f"{session.meta.name}\n  {session.meta.id}")
        self._log_system(f"New session: [bold]{session.meta.name}[/bold] ({session.meta.id})")

    def _list_sessions(self) -> None:
        sessions = self.session_mgr.list_sessions()
        if not sessions:
            self._log_system("No saved sessions.")
            return
        log = self.query_one("#output-log", RichLog)
        log.write(Text("═══ SAVED SESSIONS ═══", style="bold white"))
        for s in sessions:
            log.write(f"  {s.id}  {s.name}  [{s.status}]  {s.target or 'no target'}")

    # ------------------------------------------------------------------
    # VM actions
    # ------------------------------------------------------------------

    async def _vm_action(self, action: str) -> None:
        match action.split()[0] if action else "":
            case "start":
                await self._start_vm()
            case "stop":
                await self._stop_vm()
            case "status":
                await self._vm_status()
            case "reset":
                await self._reset_vm()
            case _:
                self._log_system("Usage: /vm [start|stop|status|reset]")

    @work(thread=False)
    async def _start_vm(self) -> None:
        self._log_system("Provisioning VM...")
        status = self.query_one("#vm-status", Static)
        status.update("[yellow]● Provisioning...[/yellow]")

        try:
            self.vm_manager = VMManager(self.config.vm)
            info = await self.vm_manager.provision()
            status.update(f"[green]● Running[/green] ({info.ip})")
            self._log_system(f"VM running: {info.ip}:{info.ssh_port}")

            # Update engine
            if self.engine:
                self.engine.vm = self.vm_manager
        except Exception as e:
            status.update("[red]● Error[/red]")
            self._log_error(f"VM provisioning failed: {e}")

    @work(thread=False)
    async def _stop_vm(self) -> None:
        if self.vm_manager:
            await self.vm_manager.teardown()
            self.query_one("#vm-status", Static).update("[red]● Stopped[/red]")
            self._log_system("VM stopped.")

    @work(thread=False)
    async def _vm_status(self) -> None:
        if self.vm_manager:
            info = await self.vm_manager.status()
            self._log_system(f"VM: {info.state.value} ({info.ip})")
        else:
            self._log_system("No VM configured. Use /vm start")

    @work(thread=False)
    async def _reset_vm(self) -> None:
        if self.vm_manager:
            await self.vm_manager.reset()
            self._log_system("VM reset to initial snapshot.")

    async def _run_vm_command(self, command: str) -> None:
        if not self.engine:
            self._log_error("Engine not initialized")
            return
        self._log_command(command, source="user")
        output = await self.engine.run_single_command(command)
        self._log_output(output)

    # ------------------------------------------------------------------
    # LLM actions
    # ------------------------------------------------------------------

    @work(thread=False)
    async def _list_models(self) -> None:
        if not self.llm_client:
            self._log_error("LLM client not initialized")
            return
        try:
            models = await self.llm_client.list_models()
            log = self.query_one("#output-log", RichLog)
            log.write(Text("═══ AVAILABLE MODELS ═══", style="bold white"))
            for m in models:
                size = m.get("size", 0)
                size_gb = size / (1024**3) if size else 0
                log.write(f"  {m.get('name', '?'):30s}  {size_gb:.1f} GB")
        except Exception as e:
            self._log_error(f"Failed to list models: {e}")

    # ------------------------------------------------------------------
    # Objective execution
    # ------------------------------------------------------------------

    @work(thread=False)
    async def _run_objective(self, objective: str) -> None:
        if not self.engine:
            self._log_error("Engine not initialized")
            return

        # Ensure we have an active session
        if not self.session_mgr.active:
            self._new_session()

        self._log_system(f"[bold]Objective:[/bold] {objective}")
        await self.engine.run_objective(objective)

    # ------------------------------------------------------------------
    # Module execution
    # ------------------------------------------------------------------

    async def _run_module(self, arg: str) -> None:
        parts = arg.split(maxsplit=1)
        if not parts:
            self._log_system("Usage: /module <module-name> <target>")
            return

        module_name = parts[0]
        target = parts[1] if len(parts) > 1 else ""

        from relic.modules.recon import RECON_MODULES
        from relic.modules.exploit import EXPLOIT_MODULES

        all_modules = {**RECON_MODULES, **EXPLOIT_MODULES}

        if module_name not in all_modules:
            self._log_error(f"Unknown module: {module_name}")
            self._log_system(f"Available: {', '.join(all_modules.keys())}")
            return

        if not self.engine:
            self._log_error("Engine not initialized")
            return

        module = all_modules[module_name]()
        self._log_system(f"Running module: [bold]{module.name}[/bold] — {module.description}")

        result = await module.run(
            self.engine,
            target=target,
            domain=target,
            url=target,
        )

        if result.findings:
            for f in result.findings:
                self._log_finding(f)

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    @work(thread=False)
    async def _generate_report(self) -> None:
        from relic.modules.reporting import ReportModule

        if not self.engine:
            self._log_error("Engine not initialized")
            return

        module = ReportModule()
        result = await module.run(self.engine, output_dir=self.config.modules.reporting.output_dir)
        self._log_system(result.output)

    # ------------------------------------------------------------------
    # Engine event handler
    # ------------------------------------------------------------------

    def _handle_engine_event(self, event: EngineEvent) -> None:
        match event:
            case LogEvent(level=level, message=msg):
                if level == "error":
                    self._log_error(msg)
                elif level == "warn":
                    self._log_warning(msg)
                else:
                    self._log_system(msg)
            case CommandEvent(command=cmd, source=src):
                self._log_command(cmd, source=src)
            case OutputEvent(text=text):
                self._log_output(text)
            case PlanEvent(tasks=tasks):
                log = self.query_one("#output-log", RichLog)
                log.write(Text(f"  ┌─ Plan ({len(tasks)} steps)", style="bold white"))
                for i, t in enumerate(tasks, 1):
                    log.write(f"  │ {i}. {t.get('description', '')} → {t.get('command', '')}")
                log.write(Text("  └─", style="dim"))
            case FindingEvent(finding=f):
                self._log_finding(f)

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def _log_system(self, msg: str) -> None:
        log = self.query_one("#output-log", RichLog)
        ts = datetime.now().strftime("%H:%M:%S")
        log.write(f"[dim]{ts}[/dim]  {msg}")

    def _log_command(self, cmd: str, source: str = "user") -> None:
        log = self.query_one("#output-log", RichLog)
        ts = datetime.now().strftime("%H:%M:%S")
        style = "log-command-llm" if source == "llm" else "log-command"
        prefix = "🤖" if source == "llm" else "$"
        log.write(f"[dim]{ts}[/dim]  [bold white]{prefix}[/bold white] {cmd}")

    def _log_output(self, text: str) -> None:
        log = self.query_one("#output-log", RichLog)
        for line in text.splitlines():
            log.write(f"     {line}")

    def _log_error(self, msg: str) -> None:
        log = self.query_one("#output-log", RichLog)
        ts = datetime.now().strftime("%H:%M:%S")
        log.write(f"[dim]{ts}[/dim]  [bold red]✗[/bold red] {msg}")

    def _log_warning(self, msg: str) -> None:
        log = self.query_one("#output-log", RichLog)
        ts = datetime.now().strftime("%H:%M:%S")
        log.write(f"[dim]{ts}[/dim]  [yellow]⚠[/yellow] {msg}")

    def _log_finding(self, finding: dict) -> None:
        log = self.query_one("#output-log", RichLog)
        ts = datetime.now().strftime("%H:%M:%S")
        sev = finding.get("severity", "info").upper()
        color = {"CRITICAL": "red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "white"}.get(sev, "dim")
        log.write(
            f"[dim]{ts}[/dim]  [{color}]◆ FINDING [{sev}][/{color}]: "
            f"{finding.get('title', finding.get('type', 'Unknown'))}"
        )

    # ------------------------------------------------------------------
    # Actions (keybindings)
    # ------------------------------------------------------------------

    def action_new_session(self) -> None:
        self._new_session()

    def action_save_session(self) -> None:
        path = self.session_mgr.save_active()
        if path:
            self._log_system(f"Session saved to {path}")
        else:
            self._log_system("No active session to save.")

    def action_stop_engine(self) -> None:
        if self.engine:
            self.engine.stop()

    def action_clear_log(self) -> None:
        self.query_one("#output-log", RichLog).clear()

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    @on(Button.Pressed, "#btn-new-session")
    def on_new_session_btn(self) -> None:
        self._new_session()

    @on(Button.Pressed, "#btn-connect-vm")
    async def on_connect_vm_btn(self) -> None:
        await self._start_vm()

    @on(Button.Pressed, "#btn-report")
    async def on_report_btn(self) -> None:
        await self._generate_report()

    @on(Button.Pressed, "#btn-stop")
    def on_stop_btn(self) -> None:
        if self.engine:
            self.engine.stop()
            self._log_system("Engine stopped.")
