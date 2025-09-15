from __future__ import annotations

import os

import typer

app = typer.Typer(name="dvol-ingest", help="DVOL data ingestion CLI")


@app.callback()
def main() -> None:  # pragma: no cover - simple CLI entrypoint
    """Entrypoint for dvol-ingest CLI."""
    # Callback can initialize env/config if needed later
    os.environ.setdefault("TZ", "UTC")


@app.command()
def version() -> None:
    """Print version information."""
    # Avoid importing the package version to keep this stub lightweight
    typer.echo("dvol-ingest version 0.1.0")


if __name__ == "__main__":
    app()

