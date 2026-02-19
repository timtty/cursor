from pathlib import Path
from typing import Protocol, runtime_checkable

from agent_feedback.models import FeedbackEntry


@runtime_checkable
class FeedbackStore(Protocol):
    def save(self, entry: FeedbackEntry) -> None: ...
    def query(
        self,
        task_type: str | None = None,
        tags: list[str] | None = None,
        exclude_agent: str | None = None,
    ) -> list[FeedbackEntry]: ...
    def get_all(self) -> list[FeedbackEntry]: ...
    def clear(self) -> None: ...


class JSONLStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, entry: FeedbackEntry) -> None:
        with self.path.open("a") as f:
            f.write(entry.model_dump_json() + "\n")

    def query(
        self,
        task_type: str | None = None,
        tags: list[str] | None = None,
        exclude_agent: str | None = None,
    ) -> list[FeedbackEntry]:
        entries = self.get_all()
        if task_type is not None:
            entries = [e for e in entries if e.task_type == task_type]
        if tags is not None:
            tag_set = set(tags)
            entries = [e for e in entries if tag_set & set(e.tags)]
        if exclude_agent is not None:
            entries = [e for e in entries if e.agent_id != exclude_agent]
        return entries

    def get_all(self) -> list[FeedbackEntry]:
        if not self.path.exists():
            return []
        entries: list[FeedbackEntry] = []
        for line in self.path.read_text().splitlines():
            line = line.strip()
            if line:
                entries.append(FeedbackEntry.model_validate_json(line))
        return entries

    def clear(self) -> None:
        if self.path.exists():
            self.path.write_text("")
