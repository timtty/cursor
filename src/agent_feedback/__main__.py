import asyncio
from pathlib import Path

import click

from agent_feedback.orchestrator import run_demo
from agent_feedback.store import JSONLStore


@click.group()
def cli() -> None:
    """Agent Feedback System — multi-agent demo with shared learning."""


@cli.command()
@click.option("--task", required=True, type=click.Path(exists=True, path_type=Path), help="Path to task markdown file")
@click.option("--agents", default=3, type=int, help="Number of agents to run sequentially")
@click.option("--adapter", "adapter_name", default="claude-code", help="Adapter name (claude-code, cursor, pi)")
@click.option("--store", "store_path", default="feedback_data/feedback.jsonl", type=click.Path(path_type=Path), help="Store path")
@click.option("--workspace", "workspace_dir", default="workspace", type=click.Path(path_type=Path), help="Workspace directory")
@click.option("--no-reset", is_flag=True, help="Don't clear store/workspace before running")
def demo(
    task: Path,
    agents: int,
    adapter_name: str,
    store_path: Path,
    workspace_dir: Path,
    no_reset: bool,
) -> None:
    """Run the multi-agent demo."""
    asyncio.run(
        run_demo(
            task_path=task,
            adapter_name=adapter_name,
            num_agents=agents,
            store_path=store_path,
            workspace_dir=workspace_dir,
            reset=not no_reset,
        )
    )


@cli.command()
@click.option("--store", "store_path", default="feedback_data/feedback.jsonl", type=click.Path(path_type=Path))
def reset(store_path: Path) -> None:
    """Reset the feedback store."""
    store = JSONLStore(store_path)
    store.clear()
    click.echo("✓ Feedback store cleared.")


if __name__ == "__main__":
    cli()
