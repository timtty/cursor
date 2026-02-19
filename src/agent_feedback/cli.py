import json
import os
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from agent_feedback.models import FeedbackCategory, FeedbackEntry
from agent_feedback.store import JSONLStore

console = Console()

DEFAULT_STORE_PATH = Path("./feedback_data/feedback.jsonl")


def _get_store() -> JSONLStore:
    path = Path(os.environ.get("AGENT_FEEDBACK_STORE", str(DEFAULT_STORE_PATH)))
    return JSONLStore(path)


@click.group()
def main() -> None:
    """Agent Feedback System — share tips between coding agents."""


@main.command()
@click.option("--agent-id", required=True, help="Agent identifier")
@click.option("--task-type", required=True, help="Task type identifier")
@click.option(
    "--category",
    required=True,
    type=click.Choice([c.value for c in FeedbackCategory], case_sensitive=False),
    help="Feedback category",
)
@click.option("--title", required=True, help="One-line summary")
@click.option("--detail", required=True, help="Full explanation")
@click.option("--tags", default="", help="Comma-separated tags")
@click.option("--confidence", default=1.0, type=float, help="Confidence 0.0-1.0")
def submit(
    agent_id: str,
    task_type: str,
    category: str,
    title: str,
    detail: str,
    tags: str,
    confidence: float,
) -> None:
    """Submit feedback to the shared store."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    entry = FeedbackEntry(
        agent_id=agent_id,
        task_type=task_type,
        category=FeedbackCategory(category),
        title=title,
        detail=detail,
        tags=tag_list,
        confidence=confidence,
    )
    store = _get_store()
    store.save(entry)
    console.print(f'✓ Feedback saved: [{entry.id}] "{entry.title}"')


@main.command()
@click.option("--task-type", default=None, help="Filter by task type")
@click.option("--tags", default=None, help="Comma-separated tags to filter by")
@click.option("--exclude-agent", default=None, help="Exclude feedback from this agent")
@click.option(
    "--format",
    "output_format",
    default="json",
    type=click.Choice(["json", "pretty"]),
    help="Output format",
)
def query(
    task_type: str | None,
    tags: str | None,
    exclude_agent: str | None,
    output_format: str,
) -> None:
    """Query feedback from the store."""
    store = _get_store()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    entries = store.query(task_type=task_type, tags=tag_list, exclude_agent=exclude_agent)
    if output_format == "json":
        click.echo(json.dumps([e.model_dump(mode="json") for e in entries], indent=2))
    else:
        _print_table(entries)


@main.command(name="list")
@click.option(
    "--format",
    "output_format",
    default="json",
    type=click.Choice(["json", "pretty"]),
    help="Output format",
)
def list_all(output_format: str) -> None:
    """List all feedback entries."""
    store = _get_store()
    entries = store.get_all()
    if output_format == "json":
        click.echo(json.dumps([e.model_dump(mode="json") for e in entries], indent=2))
    else:
        _print_table(entries)


@main.command()
@click.option("--confirm", is_flag=True, required=True, help="Confirm reset")
def reset(confirm: bool) -> None:
    """Reset the feedback store."""
    store = _get_store()
    store.clear()
    console.print("✓ Feedback store cleared.")


def _print_table(entries: list[FeedbackEntry]) -> None:
    if not entries:
        console.print("[dim]No feedback entries found.[/dim]")
        return
    table = Table(title="Feedback Entries")
    table.add_column("ID", style="dim")
    table.add_column("Agent")
    table.add_column("Category", style="cyan")
    table.add_column("Title", style="bold")
    table.add_column("Confidence", justify="right")
    table.add_column("Tags")
    for e in entries:
        table.add_row(
            e.id,
            e.agent_id,
            e.category.value,
            e.title,
            f"{e.confidence:.1f}",
            ", ".join(e.tags) if e.tags else "",
        )
    console.print(table)
