from agent_feedback.models import FeedbackCategory, FeedbackEntry
from agent_feedback.prompt_builder import build_agent_prompt


def _make_entry(**kwargs: object) -> FeedbackEntry:
    defaults: dict[str, object] = {
        "agent_id": "agent-1",
        "task_type": "build-todo-app",
        "category": FeedbackCategory.TIP,
        "title": "A tip",
        "detail": "Some detail",
        "tags": ["python"],
    }
    defaults.update(kwargs)
    return FeedbackEntry(**defaults)  # type: ignore[arg-type]


class TestBuildAgentPrompt:
    def test_first_agent_no_tips(self):
        prompt = build_agent_prompt(
            task="Build a thing",
            agent_id="agent-1",
            feedback_entries=[],
            is_first_agent=True,
        )
        assert "## Your Task" in prompt
        assert "Build a thing" in prompt
        assert "Tips & Experiences" not in prompt
        assert "Feedback Obligation" in prompt
        assert "Think Out Loud" in prompt

    def test_second_agent_gets_tips(self):
        entries = [
            _make_entry(agent_id="agent-1", title="Use Click", detail="It helps"),
            _make_entry(agent_id="agent-1", category=FeedbackCategory.GOTCHA, title="Watch dates", detail="Tricky"),
        ]
        prompt = build_agent_prompt(
            task="Build a thing",
            agent_id="agent-2",
            feedback_entries=entries,
            is_first_agent=False,
        )
        assert "## Tips & Experiences from Previous Agents" in prompt
        assert "Use Click" in prompt
        assert "Watch dates" in prompt
        assert "agent-1" in prompt

    def test_feedback_obligation_has_agent_id(self):
        prompt = build_agent_prompt(
            task="Task",
            agent_id="agent-3",
            feedback_entries=[],
            is_first_agent=True,
        )
        assert "agent-3" in prompt
        assert "agent-feedback submit" in prompt

    def test_tip_reference_instructions_always_present(self):
        prompt = build_agent_prompt(
            task="Task",
            agent_id="agent-1",
            feedback_entries=[],
            is_first_agent=True,
        )
        assert "Think Out Loud" in prompt
        assert "PRIMARY GOAL" in prompt

    def test_special_characters_in_feedback(self):
        entry = _make_entry(
            title='Use "quotes" & <brackets>',
            detail="Line1\nLine2\n```code```",
            tags=["special!@#"],
        )
        prompt = build_agent_prompt(
            task="Task",
            agent_id="agent-2",
            feedback_entries=[entry],
            is_first_agent=False,
        )
        assert '"quotes"' in prompt
        assert "<brackets>" in prompt
        assert "```code```" in prompt
