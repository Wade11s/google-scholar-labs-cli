"""CLI for Google Scholar Labs search."""

import asyncio
import json
import os
import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from scholar_labs.core.auth import ManualAuthProvider, AuthError, ScholarLabsError
from scholar_labs.services.search import SearchService

app = typer.Typer(help="Google Scholar Labs CLI — search academic papers from your terminal")
console = Console()


@app.callback(invoke_without_command=True)
def main(
    query: str = typer.Argument(..., help="Your research question or search query"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output results as JSON"),
):
    """Search Google Scholar Labs with a natural language query."""
    auth = ManualAuthProvider()

    try:
        auth.get_credentials()
    except AuthError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print(
            "\n[yellow]To configure authentication:[/yellow]\n"
            "  Set environment variables:\n"
            "    export SCHOLAR_COOKIE='your-google-cookie'\n"
            "    export SCHOLAR_XSRF_TOKEN='your-xsrf-token'\n"
            "\n  Or create ~/.scholar-labs-cli/auth.json:\n"
            '    {"cookie": "your-cookie", "xsrf_token": "your-xsrf-token"}'
        )
        raise typer.Exit(code=1)

    hl = os.environ.get("SCHOLAR_HL", "en")
    service = SearchService(auth, hl=hl)
    result = asyncio.run(_run_search(service, query))

    if json_output:
        console.print(json.dumps(_serialize_response(result), ensure_ascii=False, indent=2))
        return

    _render_response(result, query)


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
