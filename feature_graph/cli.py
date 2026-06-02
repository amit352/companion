import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def cli():
    """FeatureGraph — AI-native code intelligence platform."""


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True, path_type=Path))
@click.option("--incremental", is_flag=True, default=False, help="Only re-analyze changed files")
@click.option("--host", default="localhost")
@click.option("--port", default=8000)
def analyze(repo_path: Path, incremental: bool, host: str, port: int):
    """Analyze a repository and build its feature graph."""
    import httpx

    with console.status(f"Analyzing [bold]{repo_path.name}[/bold]..."):
        resp = httpx.post(
            f"http://{host}:{port}/api/v1/analysis/",
            json={"repo_path": str(repo_path.resolve()), "incremental": incremental},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

    console.print(f"[green]Job submitted:[/green] {data['job_id']}")
    console.print(f"[dim]Poll status: fg status {data['job_id']}[/dim]")


@cli.command()
@click.argument("job_id")
@click.option("--host", default="localhost")
@click.option("--port", default=8000)
def status(job_id: str, host: str, port: int):
    """Check the status of an analysis job."""
    import httpx

    resp = httpx.get(f"http://{host}:{port}/api/v1/analysis/{job_id}/status", timeout=5)
    resp.raise_for_status()
    data = resp.json()
    color = {"completed": "green", "running": "yellow", "failed": "red"}.get(data["status"], "white")
    console.print(f"[{color}]{data['status'].upper()}[/{color}]  job={job_id[:8]}")
    if data.get("error"):
        console.print(f"[red]Error:[/red] {data['error']}")


@cli.command()
@click.option("--host", default="localhost")
@click.option("--port", default=8000)
def plugins(host: str, port: int):
    """List all loaded plugins."""
    import httpx

    resp = httpx.get(f"http://{host}:{port}/api/v1/plugins/", timeout=5)
    resp.raise_for_status()
    data = resp.json()

    table = Table("Name", "Type", "Version", title="Loaded Plugins")
    for p in data["plugins"]:
        table.add_row(p["name"], p["type"], p["version"])
    console.print(table)


@cli.command()
@click.argument("question")
@click.option("--host", default="localhost")
@click.option("--port", default=8000)
def ask(question: str, host: str, port: int):
    """Ask a natural language question about the codebase."""
    import httpx

    console.print(f"[dim]Q: {question}[/dim]\n")
    with httpx.stream(
        "POST",
        f"http://{host}:{port}/api/v1/chat/",
        json={"question": question},
        timeout=60,
    ) as r:
        for chunk in r.iter_text():
            console.print(chunk, end="")
    console.print()


@cli.command()
def serve():
    """Start the FeatureGraph API server."""
    import uvicorn
    uvicorn.run(
        "feature_graph.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
