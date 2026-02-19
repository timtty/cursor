import pytest
from pydantic import ValidationError

from agent_feedback.models import FeedbackCategory, FeedbackEntry


class TestFeedbackCategory:
    def test_all_members_exist(self):
        assert set(FeedbackCategory.__members__) == {
            "TIP", "DIFFICULTY", "APPROACH", "GOTCHA", "TOOL_USAGE"
        }

    def test_values(self):
        assert FeedbackCategory.TIP.value == "tip"
        assert FeedbackCategory.GOTCHA.value == "gotcha"
        assert FeedbackCategory.TOOL_USAGE.value == "tool_usage"


class TestFeedbackEntry:
    def test_creation_with_defaults(self):
        entry = FeedbackEntry(
            agent_id="agent-1",
            task_type="build-todo-app",
            category=FeedbackCategory.TIP,
            title="Use Click",
            detail="Click is great for CLIs",
        )
        assert len(entry.id) == 12
        assert entry.confidence == 1.0
        assert entry.tags == []
        assert entry.harness == ""
        assert entry.parent_tips_used == []

    def test_json_roundtrip(self):
        entry = FeedbackEntry(
            agent_id="agent-2",
            task_type="refactor",
            category=FeedbackCategory.APPROACH,
            title="Start with tests",
            detail="TDD worked well",
            tags=["testing", "tdd"],
            confidence=0.85,
        )
        json_str = entry.model_dump_json()
        restored = FeedbackEntry.model_validate_json(json_str)
        assert restored.id == entry.id
        assert restored.agent_id == entry.agent_id
        assert restored.tags == ["testing", "tdd"]
        assert restored.confidence == 0.85

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            FeedbackEntry(
                agent_id="a", task_type="t",
                category=FeedbackCategory.TIP,
                title="T", detail="D",
                confidence=1.5,
            )
        with pytest.raises(ValidationError):
            FeedbackEntry(
                agent_id="a", task_type="t",
                category=FeedbackCategory.TIP,
                title="T", detail="D",
                confidence=-0.1,
            )

    def test_confidence_edge_values(self):
        e0 = FeedbackEntry(
            agent_id="a", task_type="t",
            category=FeedbackCategory.TIP,
            title="T", detail="D",
            confidence=0.0,
        )
        assert e0.confidence == 0.0
        e1 = FeedbackEntry(
            agent_id="a", task_type="t",
            category=FeedbackCategory.TIP,
            title="T", detail="D",
            confidence=1.0,
        )
        assert e1.confidence == 1.0

    def test_unique_ids(self):
        entries = [
            FeedbackEntry(
                agent_id="a", task_type="t",
                category=FeedbackCategory.TIP,
                title="T", detail="D",
            )
            for _ in range(100)
        ]
        ids = {e.id for e in entries}
        assert len(ids) == 100
