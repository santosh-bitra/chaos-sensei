"""Command-line interface for Chaos Sensei."""

import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from chaos_sensei.core.engine import ChaosSenseiEngine
from chaos_sensei.core.exceptions import ChaosSenseiException

app = typer.Typer(
    help="Repo-aware chaos engineering and incident training agent",
    no_args_is_help=True,
)

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@app.command()
def init(
    path: str = typer.Argument(".", help="Repository path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Create default chaos-sensei.yaml configuration."""
    if verbose:
        logging.getLogger("chaos_sensei").setLevel(logging.DEBUG)

    try:
        engine = ChaosSenseiEngine(Path(path))
        result = engine.init_config()
        console.print(f"[green]✓[/green] {result}")
    except ChaosSenseiException as e:
        console.print(f"[red]✗[/red] {e}", file=sys.stderr)
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def scan(
    path: str = typer.Argument(".", help="Repository path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Scan repository and detect supported technologies."""
    if verbose:
        logging.getLogger("chaos_sensei").setLevel(logging.DEBUG)

    try:
        engine = ChaosSenseiEngine(Path(path))
        result = engine.scan()
        console.print(Syntax(result, "json", theme="monokai", line_numbers=False))
    except ChaosSenseiException as e:
        console.print(f"[red]✗[/red] {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def plan(
    path: str = typer.Argument(".", help="Repository path"),
    env: str = typer.Option("staging", "--env", "-e", help="Target environment"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Generate available training scenarios."""
    if verbose:
        logging.getLogger("chaos_sensei").setLevel(logging.DEBUG)

    try:
        engine = ChaosSenseiEngine(Path(path), environment=env)
        result = engine.plan()
        console.print(Syntax(result, "json", theme="monokai", line_numbers=False))
    except ChaosSenseiException as e:
        console.print(f"[red]✗[/red] {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def start(
    scenario: str = typer.Option(
        "hidden", "--scenario", "-s", help="Scenario ID or 'hidden' for random"
    ),
    path: str = typer.Argument(".", help="Repository path"),
    env: str = typer.Option("staging", "--env", "-e", help="Target environment"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Start an incident training session."""
    if verbose:
        logging.getLogger("chaos_sensei").setLevel(logging.DEBUG)

    try:
        engine = ChaosSenseiEngine(Path(path), environment=env)
        result = engine.start(scenario_id=scenario)
        console.print(Syntax(result, "json", theme="monokai", line_numbers=False))
        console.print(
            "\n[cyan]Next steps:[/cyan]"
            "\n  chaos-sensei hint   - Get the next hint"
            "\n  chaos-sensei check  - Check if fixed"
            "\n  chaos-sensei give-up - Reveal answer and rollback"
        )
    except ChaosSenseiException as e:
        console.print(f"[red]✗[/red] {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def hint(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Get the next hint."""
    if verbose:
        logging.getLogger("chaos_sensei").setLevel(logging.DEBUG)

    try:
        engine = ChaosSenseiEngine.from_current_session()
        result = engine.hint()
        console.print(f"\n[yellow]💡 Hint[/yellow]\n\n{result}\n")
    except ChaosSenseiException as e:
        console.print(f"[red]✗[/red] {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def check(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Check whether the incident has been fixed."""
    if verbose:
        logging.getLogger("chaos_sensei").setLevel(logging.DEBUG)

    try:
        engine = ChaosSenseiEngine.from_current_session()
        result = engine.check()
        console.print(f"\n{result}\n")
    except ChaosSenseiException as e:
        console.print(f"[red]✗[/red] {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command("give-up")
def give_up(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Reveal root cause, fix the issue, and generate report."""
    if verbose:
        logging.getLogger("chaos_sensei").setLevel(logging.DEBUG)

    try:
        engine = ChaosSenseiEngine.from_current_session()
        console.print("\n[yellow]Rolling back...[/yellow]")
        engine.rollback()

        console.print("[yellow]Generating report...[/yellow]\n")
        report = engine.report()

        console.print(Syntax(report, "markdown", theme="monokai", line_numbers=False))
        console.print("\n[cyan]Report saved to .chaos-sensei/report.md[/cyan]")
    except ChaosSenseiException as e:
        console.print(f"[red]✗[/red] {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def rollback(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Rollback the current experiment."""
    if verbose:
        logging.getLogger("chaos_sensei").setLevel(logging.DEBUG)

    try:
        engine = ChaosSenseiEngine.from_current_session()
        result = engine.rollback()
        console.print(f"[green]✓[/green] Rollback complete")
        console.print(Syntax(result, "json", theme="monokai", line_numbers=False))
    except ChaosSenseiException as e:
        console.print(f"[red]✗[/red] {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def report(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Generate or display the incident report."""
    if verbose:
        logging.getLogger("chaos_sensei").setLevel(logging.DEBUG)

    try:
        engine = ChaosSenseiEngine.from_current_session()
        report_text = engine.report()
        console.print(Syntax(report_text, "markdown", theme="monokai", line_numbers=False))
    except ChaosSenseiException as e:
        console.print(f"[red]✗[/red] {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-v", help="Show version and exit"
    ),
) -> None:
    """Chaos Sensei: Incident training and chaos engineering agent."""
    if version:
        from chaos_sensei import __version__

        console.print(f"chaos-sensei {__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
