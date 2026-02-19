import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path

from agent_feedback.adapters.base import AgentAdapter, AgentResult


class CursorAdapter(AgentAdapter):
    """Subprocess adapter invoking Cursor Agent CLI with stream-json output."""

    async def run(
        self,
        prompt: str,
        work_dir: Path,
        on_stream: Callable[[str, str], Awaitable[None] | None],
        env: dict[str, str] | None = None,
    ) -> AgentResult:
        full_output: list[str] = []
        feedback_count = 0

        proc_env = {**__import__("os").environ, **(env or {})}

        abs_work_dir = str(work_dir.resolve())

        proc = await asyncio.create_subprocess_exec(
            "cursor-agent",
            "-p", prompt,
            "--output-format", "stream-json",
            "--stream-partial-output",
            "--workspace", abs_work_dir,
            "--force",
            "--trust",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=abs_work_dir,
            env=proc_env,
            limit=10 * 1024 * 1024,
        )

        assert proc.stdout is not None

        seen_text_deltas = False

        async for raw_line in proc.stdout:
            line = raw_line.decode().strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("type") == "assistant":
                if "text_delta" in event:
                    seen_text_deltas = True
                elif seen_text_deltas and event.get("message", {}).get("content"):
                    seen_text_deltas = False
                    continue

            for chunk_type, text in _parse_event(event):
                if not text:
                    continue
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


def _parse_event(event: dict) -> list[tuple[str, str]]:
    """Parse a cursor-agent stream-json event into (chunk_type, text) pairs.

    With --stream-partial-output, cursor-agent emits partial text deltas that
    may contain only a 'text_delta' field instead of a full message.
    """
    event_type = event.get("type", "")

    if event_type in ("system", "user"):
        return []

    if event_type == "assistant":
        message = event.get("message", {})
        content = message.get("content", [])
        chunks: list[tuple[str, str]] = []
        for block in content:
            block_type = block.get("type", "")
            if block_type == "thinking":
                chunks.append(("thinking", block.get("thinking", "")))
            elif block_type == "text":
                chunks.append(("text", block.get("text", "")))
        if not chunks:
            text_delta = event.get("text_delta", "")
            if text_delta:
                chunks.append(("text", text_delta))
        return chunks

    if event_type == "tool_use":
        tool_name = event.get("name", "unknown")
        tool_input = json.dumps(event.get("input", {}), indent=2)
        return [("tool", f"[{tool_name}] {tool_input}")]

    if event_type == "result":
        result_text = event.get("result", "")
        return [("text", result_text)] if result_text else []

    return []


async def _call_stream(
    on_stream: Callable[[str, str], Awaitable[None] | None],
    chunk_type: str,
    text: str,
) -> None:
    result = on_stream(chunk_type, text)
    if result is not None:
        await result
