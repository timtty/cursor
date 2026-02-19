import asyncio
import re
import time

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

TIP_REFERENCE_PATTERNS = [
    re.compile(r"agent[-\s]?\d+\s+(mentioned|recommended|suggested|warned|said)", re.IGNORECASE),
    re.compile(r"previous agent", re.IGNORECASE),
    re.compile(r"tip (about|from|regarding)", re.IGNORECASE),
    re.compile(r"based on (feedback|tips?)", re.IGNORECASE),
    re.compile(r"I see a tip", re.IGNORECASE),
    re.compile(r"I noticed a tip", re.IGNORECASE),
    re.compile(r"according to", re.IGNORECASE),
]

STYLE_MAP = {
    "thinking": "dim italic cyan",
    "text": "white",
    "tool": "yellow",
    "feedback": "green",
    "error": "red bold",
}

PREFIX_MAP = {
    "thinking": "[thinking] ",
    "tool": "[action] ",
    "feedback": "[feedback] ",
    "error": "[error] ",
}

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class StreamDisplay:
    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self.tip_references: int = 0
        self.feedback_submitted: int = 0
        self._start_time: float = 0.0
        self._agent_name: str = ""
        self._line_buffer: str = ""
        self._current_chunk_type: str = ""
        self._last_activity: float = 0.0
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._active: bool = False

    def show_agent_header(self, agent_num: int, tip_count: int) -> None:
        self._agent_name = f"Agent {agent_num}"
        self._start_time = time.time()
        self._last_activity = self._start_time
        self.tip_references = 0
        self.feedback_submitted = 0
        self._line_buffer = ""
        self._current_chunk_type = ""
        self.console.rule(
            f"[bold] AGENT {agent_num} — Starting ({tip_count} tips available) [/bold]",
            characters="═",
            style="bold cyan",
        )

    def start_heartbeat(self) -> None:
        self._active = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop_heartbeat(self) -> None:
        self._active = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
        self.console.print("\r" + " " * 80 + "\r", end="")

    async def _heartbeat_loop(self) -> None:
        frame_idx = 0
        while self._active:
            elapsed = time.time() - self._start_time
            idle = time.time() - self._last_activity
            spinner = SPINNER_FRAMES[frame_idx % len(SPINNER_FRAMES)]
            frame_idx += 1

            status_parts = [
                f"  {spinner} {self._agent_name}",
                f"elapsed {elapsed:.0f}s",
                f"tips referenced: {self.tip_references}",
                f"feedback: {self.feedback_submitted}",
            ]
            if idle > 5:
                status_parts.append(f"working... ({idle:.0f}s since last output)")

            status_line = "  |  ".join(status_parts)
            self.console.print(
                f"\r[dim]{status_line}[/dim]",
                end="",
            )
            await asyncio.sleep(0.5)

    def show_agent_footer(self, agent_num: int, tips_consumed: int, tips_submitted: int) -> None:
        self._flush_buffer()
        elapsed = time.time() - self._start_time
        self.console.print()
        self.console.rule(
            f"[bold] AGENT {agent_num} — Complete ({tips_submitted} tips submitted) [/bold]",
            characters="═",
            style="bold green",
        )
        summary = Text()
        summary.append(f"  Duration: {elapsed:.1f}s", style="dim")
        summary.append(f"  |  Tips consumed: {tips_consumed}", style="dim")
        summary.append(f"  |  Tips submitted: {tips_submitted}", style="dim")
        summary.append(f"  |  Tip references: {self.tip_references}", style="dim")
        self.console.print(summary)
        self.console.print()

    async def on_stream(self, chunk_type: str, text: str) -> None:
        if not text:
            return

        self._last_activity = time.time()

        if chunk_type == "feedback":
            self.feedback_submitted += 1

        if chunk_type != self._current_chunk_type:
            self._flush_buffer()
            self._current_chunk_type = chunk_type

        self._line_buffer += text

        while "\n" in self._line_buffer:
            line, self._line_buffer = self._line_buffer.split("\n", 1)
            self._emit_line(line, chunk_type)

    def _flush_buffer(self) -> None:
        if self._line_buffer.strip():
            self._emit_line(self._line_buffer, self._current_chunk_type)
        self._line_buffer = ""

    def _emit_line(self, line: str, chunk_type: str) -> None:
        line = line.rstrip()
        if not line:
            self.console.print()
            return

        # Clear the heartbeat status line before printing content
        self.console.print("\r" + " " * 80 + "\r", end="")

        if _is_tip_reference(line):
            self.tip_references += 1
            self.console.print(f"★ TIP REFERENCE: {line}", style="bold yellow")
        else:
            style = STYLE_MAP.get(chunk_type, "white")
            prefix = PREFIX_MAP.get(chunk_type, "")
            self.console.print(Text(prefix + line, style=style))

    def show_demo_summary(
        self,
        agent_tip_counts: list[int],
        total_tips: int,
    ) -> None:
        self.console.print()
        flow_parts: list[str] = []
        for i, count in enumerate(agent_tip_counts, 1):
            flow_parts.append(f"Agent {i}")
            flow_parts.append(f"→ {count} tips")
        flow_str = " ".join(flow_parts)

        panel = Panel(
            f"{flow_str}\nTotal tips in knowledge base: {total_tips}",
            title="[bold]DEMO COMPLETE[/bold]",
            border_style="bold cyan",
        )
        self.console.print(panel)


def _is_tip_reference(text: str) -> bool:
    return any(p.search(text) for p in TIP_REFERENCE_PATTERNS)
