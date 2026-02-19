from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentResult:
    success: bool
    output: str
    feedback_submitted: int = 0
    error: str | None = None


class AgentAdapter(ABC):
    """Abstract base for any coding agent harness."""

    @abstractmethod
    async def run(
        self,
        prompt: str,
        work_dir: Path,
        on_stream: Callable[[str, str], Awaitable[None] | None],
        env: dict[str, str] | None = None,
    ) -> AgentResult:
        """
        Execute a task with streaming output.

        on_stream(chunk_type, text) where chunk_type is one of:
          "thinking" — internal reasoning (extended thinking, chain of thought)
          "text"     — normal assistant output
          "tool"     — tool use / action being taken
          "feedback" — agent submitting feedback
          "error"    — error output
        """
        ...
