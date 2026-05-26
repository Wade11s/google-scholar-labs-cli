"""CLI for Google Scholar Labs search."""

import asyncio
import json
import os
import sys
import webbrowser
from datetime import UTC, datetime

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from scholar_labs.core.auth import (
    AuthConfigError,
    AuthConfigStore,
    AuthError,
    ChromeProfileAuthConfig,
    LegacyAuthConfigError,
    ManualAuthConfig,
    ManualAuthProvider,
    ScholarLabsError,
)
from scholar_labs.core.browser_auth import (
    BrowserAuthError,
    create_browser_credential_extractor,
)
from scholar_labs.core.login import LoginError, LoginRateLimitError, LoginService
from scholar_labs.services.search import SearchResponse, SearchService

app = typer.Typer(
    help="Google Scholar Labs CLI — search academic papers from your terminal",
)
auth_app = typer.Typer(help="Inspect and manage authentication state")
app.add_typer(auth_app, name="auth")
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Search Google Scholar Labs from your terminal."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


@app.command()
def search(
    query: str = typer.Argument(..., help="Your research question or search query"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output results as JSON"),
):
    """Search Google Scholar Labs with a natural language query."""
    auth = ManualAuthProvider()

    try:
        auth.get_credentials()
    except AuthError as e:
        if _is_interactive(json_output):
            start_login = typer.confirm("No browser auth configured. Start browser login now?", default=True)
            if start_login:
                try:
                    _run_browser_login(
                        browser="chrome",
                        profile="auto",
                        hl=os.environ.get("SCHOLAR_HL", "en"),
                    )
                except (BrowserAuthError, LoginError) as login_error:
                    console.print(f"[red]Login failed:[/red] {login_error}")
                    raise typer.Exit(code=1)
                console.print("[green]Browser auth configured. Run the search again.[/green]")
                raise typer.Exit()
            raise typer.Exit(code=1)
        console.print(f"[red]Error:[/red] {e}")
        console.print(
            "\n[yellow]To configure authentication:[/yellow]\n"
            "  Run 'sls login' to configure browser auth.\n"
            "  Or run 'sls auth manual' to configure Manual Auth Fallback.\n"
            "  Set environment variables:\n"
            "    export SCHOLAR_COOKIE='your-google-cookie'\n"
            "    export SCHOLAR_XSRF_TOKEN='your-xsrf-token'\n"
        )
        raise typer.Exit(code=1)

    hl = os.environ.get("SCHOLAR_HL", "en")
    service = SearchService(auth, hl=hl)
    result = asyncio.run(_run_search(service, query))

    if json_output:
        console.print(json.dumps(_serialize_response(result), ensure_ascii=False, indent=2))
        return

    _render_response(result, query)


@app.command()
def login(
    browser: str = typer.Option("chrome", "--browser", help="Browser to read credentials from"),
    profile: str = typer.Option("auto", "--profile", help="Browser profile to read"),
):
    """Configure authentication for Google Scholar Labs."""
    hl = os.environ.get("SCHOLAR_HL", "en")
    try:
        config = _run_browser_login(browser=browser, profile=profile, hl=hl)
    except LoginRateLimitError as e:
        console.print(f"[red]Login failed:[/red] {e}")
        raise typer.Exit(code=1)
    except (BrowserAuthError, LoginError) as e:
        if _is_interactive(False):
            url = f"https://scholar.google.com/scholar_labs/search?hl={hl}"
            console.print(f"[yellow]Opening Scholar Labs:[/yellow] {url}")
            webbrowser.open(url)
            retry = typer.confirm(
                "Complete Google login or Scholar Labs initialization in the browser, then retry?",
                default=True,
            )
            if retry:
                try:
                    config = _run_browser_login(browser=browser, profile=profile, hl=hl)
                except (BrowserAuthError, LoginError) as retry_error:
                    console.print(f"[red]Login failed:[/red] {retry_error}")
                    raise typer.Exit(code=1)
            else:
                raise typer.Exit(code=1)
        else:
            console.print(f"[red]Login failed:[/red] {e}")
            raise typer.Exit(code=1)

    console.print(
        f"[green]Browser auth configured:[/green] {config.browser} / {config.profile}"
    )


def _run_browser_login(browser: str, profile: str, hl: str):
    extractor = create_browser_credential_extractor(browser=browser, profile=profile)
    return asyncio.run(
        LoginService(
            store=AuthConfigStore(),
            extractor=extractor,
            hl=hl,
        ).login()
    )


@auth_app.command("manual")
def auth_manual():
    """Configure Manual Auth Fallback."""
    cookie = typer.prompt("Cookie")
    xsrf_token = typer.prompt("XSRF token")
    AuthConfigStore().write(
        ManualAuthConfig(
            cookie=cookie,
            xsrf_token=xsrf_token,
            validated_at=datetime.now(UTC).isoformat(),
        )
    )
    console.print("[green]Manual auth configured.[/green]")


@auth_app.command("status")
def auth_status():
    """Show authentication status."""
    store = AuthConfigStore()
    try:
        config = store.read()
    except LegacyAuthConfigError as e:
        console.print(f"[red]Legacy auth config:[/red] {e}")
        raise typer.Exit(code=1)
    except AuthConfigError as e:
        console.print(f"[red]Invalid auth config:[/red] {e}")
        raise typer.Exit(code=1)

    if config is None:
        console.print("[yellow]No auth configured.[/yellow]")
        return

    if isinstance(config, ManualAuthConfig):
        console.print("[green]Auth method:[/green] manual")
        if config.validated_at:
            console.print(f"[green]Validated at:[/green] {config.validated_at}")
        return

    if isinstance(config, ChromeProfileAuthConfig):
        console.print("[green]Auth method:[/green] chrome-profile")
        console.print(f"[green]Browser:[/green] {config.browser}")
        console.print(f"[green]Profile:[/green] {config.profile}")
        if config.validated_at:
            console.print(f"[green]Validated at:[/green] {config.validated_at}")


@auth_app.command("logout")
def auth_logout():
    """Clear local CLI authentication state."""
    removed = AuthConfigStore().delete()
    if removed:
        console.print("[green]Local auth config removed.[/green]")
    else:
        console.print("[yellow]No auth config found.[/yellow]")


async def _run_search(service: SearchService, query: str):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Searching...", total=None)
        try:
            result = await service.search(query)
        except ScholarLabsError as e:
            progress.stop()
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(code=1)
        except Exception as e:
            progress.stop()
            console.print(f"[red]Connection error:[/red] {e}")
            console.print("[dim]Google may have closed the connection. Try a shorter query or wait a moment.[/dim]")
            raise typer.Exit(code=1)
        progress.update(task, description="[green]Search complete!")
        return result


def _render_response(response, query: str):
    console.print()
    console.print(Panel(f"[bold white]{query}[/bold white]", title="Query"))

    if response.status:
        console.print(f"[dim]{response.status}[/dim]")

    if response.results:
        console.print(f"\n[bold]Results ({len(response.results)}):[/bold]\n")
        for i, result in enumerate(response.results, 1):
            _render_result(i, result)

    if response.suggested_questions:
        console.print("\n[bold cyan]Suggested follow-up questions:[/bold cyan]")
        for q in response.suggested_questions:
            console.print(f"  [cyan]•[/cyan] {q}")


def _render_result(index: int, result):
    title = Text(result.get("title", "Untitled"), style="bold white")
    if result.get("url"):
        title = Text(result["title"] or "Untitled", style="bold white underline link " + result["url"])

    content = Text()
    if result.get("authors"):
        content.append(result["authors"] + "\n", style="dim")
    if result.get("abstract"):
        content.append("\n" + _truncate(result["abstract"], 500), style="white")
    if result.get("citation_count"):
        content.append(f"\n\nCited by: {result['citation_count']}", style="green")

    panel = Panel(content, title=title, title_align="left", border_style="blue")
    console.print(panel)


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def _is_interactive(json_output: bool) -> bool:
    return not json_output and sys.stdin.isatty() and sys.stdout.isatty()


def _serialize_response(response) -> dict:
    return {
        "status": response.status,
        "results": [
            {
                "title": r.get("title", ""),
                "authors": r.get("authors", ""),
                "abstract": r.get("abstract", ""),
                "citation_count": r.get("citation_count", 0),
                "url": r.get("url", ""),
                "paper_id": r.get("paper_id", ""),
            }
            for r in response.results
        ],
        "suggested_questions": response.suggested_questions,
    }


if __name__ == "__main__":
    app()
