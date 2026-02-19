import asyncio
import json
import shutil
from collections.abc import Awaitable, Callable
from pathlib import Path

from agent_feedback.adapters.base import AgentAdapter, AgentResult


class PiAdapter(AgentAdapter):
    """Subprocess adapter invoking Pi CLI with JSON output mode."""

    async def run(
        self,
        prompt: str,
        work_dir: Path,
        on_stream: Callable[[str, str], Awaitable[None] | None],
        env: dict[str, str] | None = None,
    ) -> AgentResult:
        if not shutil.which("pi"):
            raise RuntimeError(
                "Pi CLI not found on PATH. Install from https://github.com/anthropics/pi "
                "or use --adapter direct-api for demos."
            )

        full_output: list[str] = []
        feedback_count = 0

        proc_env = {**__import__("os").environ, **(env or {})}

        proc = await asyncio.create_subprocess_exec(
            "pi",
            "-p", prompt,
            "--mode", "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(work_dir),
            env=proc_env,
            limit=10 * 1024 * 1024,
        )

        assert proc.stdout is not None

        async for raw_line in proc.stdout:
            line = raw_line.decode().strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            chunk_type, text = _parse_event(event)
            if text:
                full_output.append(text)
                if "agent-feedback submit" in text:
                    feedback_count += 1
                    await _call_stream(on_stream, "feedback", text)
                else:
                    await _call_stream(on_stream, chunk_type, text)

        await proc.wait()

        output_text = "".join(full_output)
        success = proc.returncode == 0
        error = None

        if not success and proc.stderr:
            error = (await proc.stderr.read()).decode()
            await _call_stream(on_stream, "error", error)

        return AgentResult(
            success=success,
            output=output_text,
            feedback_submitted=feedback_count,
            error=error,
        )


def _parse_event(event: dict) -> tuple[str, str]:
    event_type = event.get("type", "")

    if event_type == "thinking":
        return "thinking", event.get("text", "")
    if event_type == "text":
        return "text", event.get("text", "")
    if event_type == "tool_use":
        return "tool", event.get("text", json.dumps(event.get("input", {})))
    if event_type == "result":
        return "text", event.get("text", "")

    return "text", event.get("text", "")


async def _call_stream(
    on_stream: Callable[[str, str], Awaitable[None] | None],
    chunk_type: str,
    text: str,
) -> None:
    result = on_stream(chunk_type, text)
    if result is not None:
        await result
