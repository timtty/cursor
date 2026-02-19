from agent_feedback.models import FeedbackEntry


def build_agent_prompt(
    task: str,
    agent_id: str,
    feedback_entries: list[FeedbackEntry],
    is_first_agent: bool = False,
) -> str:
    sections: list[str] = []

    sections.append("## Your Task\n\n" + task.strip())

    if not is_first_agent and feedback_entries:
        tips_lines: list[str] = ["## Tips & Experiences from Previous Agents\n"]
        for entry in feedback_entries:
            tags_str = ", ".join(entry.tags) if entry.tags else "none"
            tips_lines.append(
                f"### [{entry.category.value}] from {entry.agent_id} "
                f"(confidence: {entry.confidence})\n"
                f'**"{entry.title}"**\n'
                f"{entry.detail}\n"
                f"Tags: {tags_str}\n"
            )
        sections.append("\n".join(tips_lines))

    sections.append(
        f"## Your Feedback Obligation\n\n"
        f"After completing the task, submit at least 2-3 tips covering: "
        f"what approach worked, what pitfalls to avoid, and any non-obvious gotchas.\n\n"
        f"Use the exact CLI syntax:\n\n"
        f"```bash\n"
        f"agent-feedback submit --agent-id {agent_id} --task-type <task-type> \\\n"
        f'  --category tip --title "Your tip title" \\\n'
        f'  --detail "Detailed explanation of your tip"\n'
        f"```\n\n"
        f"Submit tips for each of these categories where applicable:\n"
        f"- `tip` — Actionable advice for future agents\n"
        f"- `difficulty` — What was hard or went wrong\n"
        f"- `approach` — Strategy that worked\n"
        f"- `gotcha` — Non-obvious pitfall\n"
        f"- `tool_usage` — Effective tool/command patterns"
    )

    sections.append(
        "## CRITICAL: Think Out Loud About Tips\n\n"
        "When you encounter a situation where a previous agent's tip is relevant, "
        "you MUST explicitly say so in your reasoning. For example:\n\n"
        '- "Agent-1 mentioned X, so I\'ll do Y instead..."\n'
        '- "I see a tip about Z — let me try that approach..."\n'
        '- "Interesting, agent-2 warned about this exact issue, let me avoid that..."\n\n'
        "Visible tip-referencing is the PRIMARY GOAL of this demo. "
        "Narrate your decision-making process, especially when tips influence your choices."
    )

    return "\n\n".join(sections) + "\n"
