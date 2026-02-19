# Agent Feedback System

This project implements an agent feedback/experience sharing system.

## Feedback CLI
After completing any task, submit your tips and experiences:
    agent-feedback submit --agent-id <your-id> --task-type <type> \
      --category tip --title "..." --detail "..."

Query existing tips before starting work:
    agent-feedback query --task-type <type>

## Dev Commands
    pip install -e .
    python -m agent_feedback demo --task tasks/example_task.md
    pytest tests/
