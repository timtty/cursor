import asyncio
import shutil
from pathlib import Path

from agent_feedback.adapters import get_adapter
from agent_feedback.prompt_builder import build_agent_prompt
from agent_feedback.store import JSONLStore
from agent_feedback.stream import StreamDisplay


async def run_demo(
    task_path: Path,
    adapter_name: str = "claude-code",
    num_agents: int = 3,
    store_path: Path = Path("feedback_data/feedback.jsonl"),
    workspace_dir: Path = Path("workspace"),
    reset: bool = True,
) -> None:
    store = JSONLStore(store_path)
    display = StreamDisplay()

    if reset:
        store.clear()
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir)
        workspace_dir.mkdir(parents=True, exist_ok=True)

    task = task_path.read_text()

    agent_tip_counts: list[int] = []

    for i in range(1, num_agents + 1):
        agent_id = f"agent-{i}"
        is_first = i == 1

        existing_feedback = store.query(exclude_agent=agent_id)
        tip_count = len(existing_feedback)

        display.show_agent_header(i, tip_count)

        prompt = build_agent_prompt(
            task=task,
            agent_id=agent_id,
            feedback_entries=existing_feedback,
            is_first_agent=is_first,
        )

        agent_work_dir = workspace_dir / agent_id
        agent_work_dir.mkdir(parents=True, exist_ok=True)

        adapter = get_adapter(adapter_name)

        agent_env = {"AGENT_FEEDBACK_STORE": str(store_path.resolve())}

        store_count_before = len(store.get_all())

        display.start_heartbeat()
        result = await adapter.run(
            prompt=prompt,
            work_dir=agent_work_dir,
            on_stream=display.on_stream,
            env=agent_env,
        )
        await display.stop_heartbeat()

        tips_submitted = len(store.get_all()) - store_count_before
        agent_tip_counts.append(tips_submitted)

        display.show_agent_footer(
            agent_num=i,
            tips_consumed=tip_count,
            tips_submitted=tips_submitted,
        )

        if i < num_agents:
            await asyncio.sleep(2)

    total_tips = len(store.get_all())
    display.show_demo_summary(agent_tip_counts, total_tips)
