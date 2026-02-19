import tempfile
from pathlib import Path

import pytest

from agent_feedback.models import FeedbackCategory, FeedbackEntry
from agent_feedback.store import JSONLStore


@pytest.fixture
def store(tmp_path: Path) -> JSONLStore:
    return JSONLStore(tmp_path / "feedback.jsonl")


def _make_entry(**kwargs: object) -> FeedbackEntry:
    defaults: dict[str, object] = {
        "agent_id": "agent-1",
        "task_type": "build-todo-app",
        "category": FeedbackCategory.TIP,
        "title": "A tip",
        "detail": "Some detail",
    }
    defaults.update(kwargs)
    return FeedbackEntry(**defaults)  # type: ignore[arg-type]


class TestJSONLStore:
    def test_empty_store_returns_empty(self, store: JSONLStore):
        assert store.get_all() == []

    def test_save_and_retrieve(self, store: JSONLStore):
        entry = _make_entry()
        store.save(entry)
        results = store.get_all()
        assert len(results) == 1
        assert results[0].id == entry.id
        assert results[0].title == entry.title

    def test_multiple_saves(self, store: JSONLStore):
        for i in range(5):
            store.save(_make_entry(title=f"Tip {i}"))
        assert len(store.get_all()) == 5

    def test_query_by_task_type(self, store: JSONLStore):
        store.save(_make_entry(task_type="t1"))
        store.save(_make_entry(task_type="t2"))
        store.save(_make_entry(task_type="t1"))
        assert len(store.query(task_type="t1")) == 2
        assert len(store.query(task_type="t2")) == 1
        assert len(store.query(task_type="t3")) == 0

    def test_query_by_tags(self, store: JSONLStore):
        store.save(_make_entry(tags=["python", "click"]))
        store.save(_make_entry(tags=["rust"]))
        store.save(_make_entry(tags=["python", "pydantic"]))
        assert len(store.query(tags=["python"])) == 2
        assert len(store.query(tags=["rust"])) == 1
        assert len(store.query(tags=["go"])) == 0

    def test_query_exclude_agent(self, store: JSONLStore):
        store.save(_make_entry(agent_id="agent-1"))
        store.save(_make_entry(agent_id="agent-2"))
        store.save(_make_entry(agent_id="agent-1"))
        assert len(store.query(exclude_agent="agent-1")) == 1
        assert len(store.query(exclude_agent="agent-2")) == 2
        assert len(store.query(exclude_agent="agent-3")) == 3

    def test_query_combined_filters(self, store: JSONLStore):
        store.save(_make_entry(agent_id="a1", task_type="t1", tags=["x"]))
        store.save(_make_entry(agent_id="a2", task_type="t1", tags=["x"]))
        store.save(_make_entry(agent_id="a1", task_type="t2", tags=["y"]))
        result = store.query(task_type="t1", exclude_agent="a1")
        assert len(result) == 1
        assert result[0].agent_id == "a2"

    def test_clear(self, store: JSONLStore):
        store.save(_make_entry())
        store.save(_make_entry())
        assert len(store.get_all()) == 2
        store.clear()
        assert store.get_all() == []

    def test_nonexistent_file(self, tmp_path: Path):
        store = JSONLStore(tmp_path / "does_not_exist" / "fb.jsonl")
        assert store.get_all() == []

    def test_parent_dirs_created(self, tmp_path: Path):
        store = JSONLStore(tmp_path / "a" / "b" / "c" / "fb.jsonl")
        store.save(_make_entry())
        assert len(store.get_all()) == 1
