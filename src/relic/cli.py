"""
Relic CLI entry point.

Usage:
    relic              Launch the TUI
    relic --config     Specify config file
    relic --version    Show version
    relic accept       Accept disclaimer and launch
"""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from relic import BANNER, __version__

console = Console()


FULL_DISCLAIMER = """
[bold red]╔══════════════════════════════════════════════════════════════════════════════╗
║                          ⚠  LEGAL DISCLAIMER  ⚠                           ║
╚══════════════════════════════════════════════════════════════════════════════╝[/bold red]

[bold white]Relic[/bold white] is a penetration testing automation framework intended [bold]EXCLUSIVELY[/bold]
for [bold green]authorized security testing[/bold green] and [bold green]educational purposes[/bold green].

[bold yellow]By using this software, you acknowledge and agree to the following:[/bold yellow]

  [white]1.[/white] You have [bold]EXPLICIT WRITTEN AUTHORIZATION[/bold] from the owner(s) of any
     system you test. Testing without authorization is [bold red]illegal[/bold red].

  [white]2.[/white] Unauthorized access to computer systems violates the [bold]Computer Fraud
     and Abuse Act (CFAA)[/bold], the [bold]Computer Misuse Act[/bold], and equivalent laws
     in jurisdictions worldwide. Penalties include [bold red]imprisonment and fines[/bold red].

  [white]3.[/white] The developers and contributors of Relic accept [bold]NO LIABILITY[/bold]
     whatsoever for any damage, loss, or legal consequences arising from
     the use or misuse of this tool.

  [white]4.[/white] You accept [bold]FULL PERSONAL RESPONSIBILITY[/bold] for all actions performed
     with this tool.

  [white]5.[/white] This tool should [bold]ONLY[/bold] be used within [bold]isolated, virtualized
     environments[/bold] (VMs, containers, lab networks) or against systems
     you explicitly own.

  [white]6.[/white] You agree to comply with all applicable local, state, national,
     and international laws and regulations.

[bold red]  USE RESPONSIBLY  ·  HACK ETHICALLY  ·  RESPECT THE LAW[/bold red]
"""


def _show_banner() -> None:
    console.print(Text(BANNER, style="bold white"))
    console.print()


def _show_disclaimer() -> None:
    console.print(Panel(
        FULL_DISCLAIMER,
        border_style="red",
        title="[bold red] RELIC — RESPONSIBLE USE POLICY [/bold red]",
        title_align="center",
        padding=(1, 2),
    ))


@click.group(invoke_without_command=True)
@click.option("--config", "-c", default=None, help="Path to config YAML")
@click.option("--version", "-v", is_flag=True, help="Show version")
@click.option("--no-disclaimer", is_flag=True, help="Skip disclaimer (for automation)")
@click.pass_context
def main(ctx: click.Context, config: str | None, version: bool, no_disclaimer: bool) -> None:
    """Relic — Local LLM-Powered Pentesting Automation."""
    if version:
        console.print(f"Relic v{__version__}")
        return

    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config

    if ctx.invoked_subcommand is None:
        # Default: show disclaimer → launch TUI
        _show_banner()

        if not no_disclaimer:
            _show_disclaimer()
            console.print()
            accepted = click.confirm(
                click.style("  Do you accept these terms and confirm you have authorization?", fg="yellow"),
                default=False,
            )
            if not accepted:
                console.print("[red]  Declined. Exiting.[/red]")
                sys.exit(0)
            console.print()
            console.print("[green]  ✓ Terms accepted. Launching Relic...[/green]")
            console.print()

        _launch_tui(config)


@main.command()
@click.pass_context
def accept(ctx: click.Context) -> None:
    """Accept disclaimer and launch immediately."""
    _show_banner()
    console.print("[yellow]  Disclaimer auto-accepted via CLI flag.[/yellow]")
    _launch_tui(ctx.obj.get("config_path"))


@main.command()
def disclaimer() -> None:
    """Show the full disclaimer."""
    _show_banner()
    _show_disclaimer()


@main.command(name="config")
@click.option("--show", is_flag=True, help="Show current config")
def config_cmd(show: bool) -> None:
    """Manage Relic configuration."""
    if show:
        from relic.core.config import load_config
        cfg = load_config()
        console.print_json(cfg.model_dump_json(indent=2))
    else:
        console.print("Use --show to display current config, or edit ~/.relic/config.yaml")


def _launch_tui(config_path: str | None = None) -> None:
    from relic.core.config import load_config
    from relic.ui.app import RelicApp

    cfg = load_config(config_path)
    app = RelicApp(config=cfg)
    app.run()


if __name__ == "__main__":
    main()
