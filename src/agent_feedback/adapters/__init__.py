from agent_feedback.adapters.base import AgentAdapter, AgentResult
from agent_feedback.adapters.claude_code import ClaudeCodeAdapter
from agent_feedback.adapters.cursor import CursorAdapter
from agent_feedback.adapters.pi import PiAdapter

ADAPTERS: dict[str, type[AgentAdapter]] = {
    "claude-code": ClaudeCodeAdapter,
    "cursor": CursorAdapter,
    "pi": PiAdapter,
}


def get_adapter(name: str, **kwargs: object) -> AgentAdapter:
    cls = ADAPTERS.get(name)
    if cls is None:
        available = ", ".join(sorted(ADAPTERS))
        raise ValueError(f"Unknown adapter '{name}'. Available: {available}")
    return cls(**kwargs)  # type: ignore[arg-type]
