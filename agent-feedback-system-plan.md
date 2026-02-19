# Agent Feedback & Experience System — Build Plan

Python application where agents learn from each other through a shared feedback/experience system. Agents perform coding tasks, submit tips and experiences to a shared JSONL backend, and subsequent agents receive those tips injected into their prompt. Agents stream their reasoning so observers see them actively referencing tips from previous agents.

The feedback mechanism is prompt-level injection: accumulated tips are prepended to each agent's task prompt. Agent harness adapters invoke coding agent CLIs (Claude Code, Cursor, Pi) via subprocess, or use the Anthropic API directly as the default.

---

## Project Structure

```
agent-feedback-system/
├── README.md
├── pyproject.toml
├── AGENTS.md
├── .claude/
│   └── commands/
│       └── submit-feedback.md
├── .cursorrules
├── src/
│   └── agent_feedback/
│       ├── __init__.py
│       ├── __main__.py          # Entry point: python -m agent_feedback
│       ├── models.py            # Pydantic models for feedback entries
│       ├── store.py             # FeedbackStore Protocol + JSONL implementation
│       ├── cli.py               # CLI tool agents invoke to submit/query feedback
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── base.py          # Abstract AgentAdapter + AgentResult
│       │   ├── claude_code.py   # Claude Code subprocess adapter
│       │   ├── cursor.py        # Cursor subprocess adapter
│       │   ├── direct_api.py    # Anthropic SDK adapter (default)
│       │   └── pi.py            # Pi coding agent adapter
│       ├── prompt_builder.py    # Builds prompts with injected feedback
│       ├── orchestrator.py      # Runs sequential multi-agent demo
│       └── stream.py            # Rich console streaming display
├── tasks/
│   └── example_task.md          # Demo task all agents attempt
├── feedback_data/
│   └── .gitkeep                 # JSONL files land here
├── workspace/
│   └── .gitkeep                 # Scratch dir for agent work
└── tests/
    ├── test_store.py
    ├── test_prompt_builder.py
    └── test_models.py
```

---

## Dependencies

```toml
[project]
name = "agent-feedback-system"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.52.0",
    "click>=8.1",
    "pydantic>=2.0",
    "rich>=13.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[project.scripts]
agent-feedback = "agent_feedback.cli:main"
```

---

## Build Order

Build files in this exact order. Each file should be complete and working before moving to the next.

### Step 1: `src/agent_feedback/models.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from uuid import uuid4

class FeedbackCategory(str, Enum):
    TIP = "tip"                    # Actionable advice for future agents
    DIFFICULTY = "difficulty"      # What was hard / went wrong
    APPROACH = "approach"          # Strategy that worked
    GOTCHA = "gotcha"              # Non-obvious pitfall
    TOOL_USAGE = "tool_usage"      # Effective tool/command patterns

class FeedbackEntry(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    agent_id: str                  # e.g. "agent-1"
    task_type: str                 # e.g. "build-todo-app"
    category: FeedbackCategory
    title: str                     # One-line summary
    detail: str                    # Full explanation
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    harness: str = ""              # Which agent harness produced this
    parent_tips_used: list[str] = Field(default_factory=list)  # IDs of tips consumed
```

### Step 2: `src/agent_feedback/store.py`

Implement a `FeedbackStore` Protocol and a `JSONLStore` concrete class.

- `JSONLStore.__init__(self, path: Path)` — creates parent dirs if needed
- `save(self, entry: FeedbackEntry) -> None` — appends one JSON line
- `query(self, task_type: str | None = None, tags: list[str] | None = None, exclude_agent: str | None = None) -> list[FeedbackEntry]` — reads all lines, filters by params
- `get_all(self) -> list[FeedbackEntry]` — returns everything
- `clear(self) -> None` — truncates the file (useful for demo resets)

The store must handle the file not existing yet (return empty list). All reads re-parse the full file (acceptable for demo scale).

### Step 3: `src/agent_feedback/cli.py`

Click-based CLI with three commands. This is what agents invoke via bash during their runs.

```bash
# Submit feedback
agent-feedback submit \
  --agent-id "agent-1" \
  --task-type "build-todo-app" \
  --category tip \
  --title "Use Click groups for subcommands" \
  --detail "Organizing commands into groups early prevents refactoring later" \
  --tags "click,architecture" \
  --confidence 0.9

# Query tips (returns JSON by default, --format pretty for human-readable)
agent-feedback query --task-type "build-todo-app"
agent-feedback query --task-type "build-todo-app" --format pretty

# List all feedback
agent-feedback list
agent-feedback list --format pretty

# Reset feedback store (for demo reruns)
agent-feedback reset --confirm
```

Use `AGENT_FEEDBACK_STORE` env var for store path, defaulting to `./feedback_data/feedback.jsonl`.

Output confirmation on submit: `✓ Feedback saved: [id] "title"`. Query output as JSON array for agent consumption, or Rich table for `--format pretty`.

### Step 4: `src/agent_feedback/prompt_builder.py`

Single function: `build_agent_prompt(task: str, agent_id: str, feedback_entries: list[FeedbackEntry], is_first_agent: bool = False) -> str`

The returned prompt must have these sections in order:

1. **Your Task** — the task description verbatim
2. **Tips & Experiences from Previous Agents** (omitted if `is_first_agent`). For each entry, render:
   ```
   ### [category] from {agent_id} (confidence: {confidence})
   **"{title}"**
   {detail}
   Tags: {tags}
   ```
3. **Your Feedback Obligation** — instructions telling the agent to submit its own tips after completing the task, with the exact CLI syntax including `--agent-id {agent_id}`. Tell the agent to submit at least 2-3 tips covering: what approach worked, what pitfalls to avoid, and any non-obvious gotchas.
4. **CRITICAL: Think Out Loud About Tips** — instruct the agent that when it encounters a situation where a previous agent's tip is relevant, it MUST explicitly say so in its reasoning. Examples:
   - "Agent-1 mentioned X, so I'll do Y instead..."
   - "I see a tip about Z — let me try that approach..."
   - "Interesting, agent-2 warned about this exact issue, let me avoid that..."
   
   This section should emphasize that visible tip-referencing is the PRIMARY GOAL of the demo. The agent should narrate its decision-making process, especially when tips influence its choices.

### Step 5: `src/agent_feedback/adapters/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Awaitable

@dataclass
class AgentResult:
    success: bool
    output: str                           # Full captured output
    feedback_submitted: int = 0           # Number of feedback entries the agent submitted
    error: str | None = None

class AgentAdapter(ABC):
    """Abstract base for any coding agent harness."""

    @abstractmethod
    async def run(
        self,
        prompt: str,
        work_dir: Path,
        on_stream: Callable[[str, str], Awaitable[None] | None],
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
```

### Step 6: `src/agent_feedback/adapters/direct_api.py`

Default adapter using the `anthropic` Python SDK. This must work without any external CLI installed.

Implementation requirements:
- Use `anthropic.AsyncAnthropic()` client
- Model: `claude-sonnet-4-20250514` (configurable)
- Enable extended thinking with `thinking` parameter (budget_tokens ~10000) so reasoning is visible
- Stream the response using `client.messages.stream()`
- Parse streaming events:
  - `thinking` blocks → `on_stream("thinking", text)`
  - `text` blocks → `on_stream("text", text)`
- The agent won't have actual bash access, so the feedback submission is simulated: parse the agent's output for `agent-feedback submit` commands, extract the arguments, and execute them against the store directly
- For the demo, this adapter should give the agent a system prompt saying: "You are a coding agent. You cannot execute code, but you should write out your complete solution and reasoning. When submitting feedback, write the exact `agent-feedback submit` CLI command you would run."
- After the agent responds, scan its output for `agent-feedback submit` commands, parse them, and actually save them to the store
- Return `AgentResult` with the feedback count

### Step 7: `src/agent_feedback/adapters/claude_code.py`

Subprocess adapter invoking Claude Code CLI.

```bash
claude -p "<prompt>" --output-format stream-json
```

Parse the streaming JSON lines from stdout. Each line is a JSON object with a `type` field. Key types:
- `assistant` with `message.content[].type == "thinking"` → `on_stream("thinking", ...)`
- `assistant` with `message.content[].type == "text"` → `on_stream("text", ...)`
- `tool_use` → `on_stream("tool", ...)`
- `result` → final message

The prompt should include instructions to run `agent-feedback submit` via bash tool. The agent has real bash access in Claude Code, so feedback submission happens naturally.

Set `--max-turns 20` to limit runaway agents. Pass `--cwd <work_dir>` to set working directory.

### Step 8: `src/agent_feedback/adapters/cursor.py`

Stub adapter for Cursor. Cursor's CLI/API integration is less standardized, so implement as:
- A placeholder that raises `NotImplementedError("Cursor adapter requires Cursor IDE running. Use --adapter direct-api for demos.")`
- Include a docstring explaining the integration path: Cursor's Agent mode can be driven via its extension API or by placing instructions in `.cursorrules`

### Step 9: `src/agent_feedback/adapters/pi.py`

Subprocess adapter invoking Pi CLI.

```bash
pi -p "<prompt>" --mode json
```

Similar to Claude Code adapter — parse streaming JSON events from stdout. Map pi's event types to our `on_stream` callback types.

Include fallback: if `pi` is not on PATH, raise a clear error with install instructions.

### Step 10: `src/agent_feedback/adapters/__init__.py`

Registry mapping adapter names to classes:

```python
ADAPTERS = {
    "direct-api": DirectAPIAdapter,
    "claude-code": ClaudeCodeAdapter,
    "cursor": CursorAdapter,
    "pi": PiAdapter,
}

def get_adapter(name: str, **kwargs) -> AgentAdapter:
    ...
```

### Step 11: `src/agent_feedback/stream.py`

Rich-based streaming display. This is the UI the human observer watches.

Requirements:
- Use `rich.console.Console` and `rich.live.Live` for streaming updates
- Display agent header with Rich rule: `═══ AGENT {n} — Starting ({tip_count} tips available) ═══`
- Color-code chunk types:
  - `thinking` → dim italic cyan, prefixed with `[thinking]`
  - `text` → default white
  - `tool` → yellow, prefixed with `[action]`
  - `feedback` → green, prefixed with `[feedback]`
  - `error` → red bold
- **Critical feature**: Detect tip-reference patterns in thinking/text output and highlight them. Scan for patterns like:
  - "agent-1 mentioned" / "agent-2 recommended" / "previous agent"
  - "tip about" / "tip from" / "based on feedback"
  - "I see a tip" / "I noticed a tip" / "according to"
  When detected, render that line in bold yellow with a `★ TIP REFERENCE` prefix.
- Show a running summary panel at the bottom: agent name, elapsed time, tips referenced so far, feedback submitted so far
- After each agent completes, show a summary: tips consumed, tips submitted, duration

### Step 12: `src/agent_feedback/orchestrator.py`

The main demo runner.

```python
async def run_demo(
    task_path: Path,
    adapter_name: str = "direct-api",
    num_agents: int = 3,
    store_path: Path = Path("feedback_data/feedback.jsonl"),
    workspace_dir: Path = Path("workspace"),
    reset: bool = True,
) -> None:
```

Flow:
1. If `reset`, clear the feedback store and workspace directory
2. Read task from `task_path`
3. For each agent `i` in `1..num_agents`:
   a. Query store for all feedback (excluding current agent's ID)
   b. Build prompt via `prompt_builder.build_agent_prompt()`
   c. Create agent workspace subdirectory: `workspace/agent-{i}/`
   d. Display header via `stream.py`
   e. Run adapter with streaming display callback
   f. Display completion summary
   g. Brief pause between agents (2 seconds) for readability
4. After all agents complete, display a final summary:
   - Total tips in store
   - Tip flow: "Agent 1 → 3 tips → Agent 2 → 4 tips → Agent 3 → 2 tips"
   - Any tips that were referenced by multiple agents

### Step 13: `src/agent_feedback/__main__.py`

Entry point using Click:

```bash
# Run the full demo
python -m agent_feedback demo --task tasks/example_task.md --agents 3 --adapter direct-api

# Run with Claude Code
python -m agent_feedback demo --task tasks/example_task.md --adapter claude-code

# Reset feedback store
python -m agent_feedback reset
```

Options for `demo`:
- `--task` (required) — path to task markdown file
- `--agents` (default 3) — number of agents to run sequentially
- `--adapter` (default "direct-api") — adapter name
- `--store` (default "feedback_data/feedback.jsonl") — store path
- `--workspace` (default "workspace") — workspace directory
- `--no-reset` — don't clear store/workspace before running
- `--model` — override model for direct-api adapter

### Step 14: `tasks/example_task.md`

```markdown
# Task: Build a Python CLI Todo Application

Build a complete command-line todo application in Python.

## Features Required
1. Add todos with a title and optional description
2. List all todos with status indicators
3. Mark todos as complete
4. Delete todos
5. Persistent storage using a JSON file
6. Priority levels: high, medium, low
7. Due dates with overdue highlighting (items past due shown in red)
8. Search todos by keyword
9. Filter by status (complete/incomplete) and priority

## Technical Requirements
- Use Click for the CLI framework
- Use Rich for terminal output (tables, colors, status indicators)
- Store data in a `todos.json` file in the current directory
- Each todo needs: id, title, description, priority, due_date, completed, created_at
- Use Pydantic for the data model
- Handle edge cases: duplicate IDs, missing file, invalid dates, empty list

## Example Usage
    todo add "Buy groceries" --priority high --due 2025-01-15
    todo add "Write report" --description "Q4 summary" --priority medium
    todo list
    todo list --filter incomplete --priority high
    todo complete 1
    todo search "groceries"
    todo delete 1

## Quality Bar
- The app should feel polished — good error messages, helpful --help text
- Use Rich tables for the list view with color-coded priorities and overdue dates
- Include at least 3 basic tests using pytest
```

### Step 15: Harness Integration Files

**`AGENTS.md`** (project root):
```markdown
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
```

**`.claude/commands/submit-feedback.md`**:
```markdown
Submit your feedback and tips about the task you just completed.

Run these commands to share what you learned:

agent-feedback submit --agent-id "$ARGUMENTS" --task-type "build-todo-app" \
  --category tip --title "Describe your tip" \
  --detail "Explain in detail what you learned and why it matters"

Submit at least 2-3 tips covering: what worked, what to avoid, and gotchas.
```

**`.cursorrules`**:
```
When working on tasks in this project:
1. First check for tips: agent-feedback query --task-type <relevant-type>
2. Reference tips from other agents in your reasoning
3. After completing work, submit your own tips:
   agent-feedback submit --agent-id cursor-agent --task-type <type> \
     --category tip --title "..." --detail "..."
```

### Step 16: `src/agent_feedback/__init__.py`

Minimal init with version:
```python
__version__ = "0.1.0"
```

### Step 17: Tests

**`tests/test_models.py`** — Test FeedbackEntry creation, serialization to/from JSON, validation of confidence bounds, category enum values.

**`tests/test_store.py`** — Test JSONLStore: save and retrieve, query with filters, exclude_agent filter, clear, empty store returns empty list, concurrent-safe append.

**`tests/test_prompt_builder.py`** — Test prompt building: first agent gets no tips section, second agent gets formatted tips, tip reference instructions are always present, special characters in feedback don't break formatting.

---

## Usage

```bash
# Install
pip install -e .

# Run the 3-agent demo (default: direct API adapter)
python -m agent_feedback demo --task tasks/example_task.md

# Run with Claude Code as the agent harness
python -m agent_feedback demo --task tasks/example_task.md --adapter claude-code

# Run with more agents
python -m agent_feedback demo --task tasks/example_task.md --agents 5

# Manual CLI usage
agent-feedback submit --agent-id me --task-type "build-todo-app" \
  --category tip --title "Use Click groups" --detail "..."
agent-feedback query --task-type "build-todo-app"
agent-feedback list --format pretty
agent-feedback reset --confirm
```

## Expected Demo Output

```
═══════════════════════════════════════════════════
  AGENT 1 — Starting (0 tips available)
═══════════════════════════════════════════════════

[thinking] I need to build a todo CLI app with Click and Rich.
Let me start with the data model using Pydantic...

[text] Creating the todo data model with fields for id, title,
description, priority, due_date, completed, created_at...

[thinking] For date handling, I should be careful with parsing.
I'll use dateutil.parser for flexible input formats...

[feedback] ✓ Submitted: "Use python-dateutil for flexible date parsing"
[feedback] ✓ Submitted: "Rich Table column widths need explicit setting"
[feedback] ✓ Submitted: "Store JSON with indent=2 for debuggability"

═══════════════════════════════════════════════════
  AGENT 1 — Complete (3 tips submitted)
═══════════════════════════════════════════════════

═══════════════════════════════════════════════════
  AGENT 2 — Starting (3 tips available)
═══════════════════════════════════════════════════

[thinking] Let me review what Agent 1 learned before I start...

★ TIP REFERENCE: "Agent-1 recommended python-dateutil for date
  parsing — I'll use that instead of manually parsing with strptime"

★ TIP REFERENCE: "Agent-1 warned about Rich Table column widths.
  I'll set explicit widths from the start to avoid alignment issues"

[thinking] Based on Agent-1's tips, I'll also store JSON with
indent=2. Now let me think about the overall architecture...

[feedback] ✓ Submitted: "Separate CLI layer from business logic"
[feedback] ✓ Submitted: "Add --format json flag for machine-readable output"

═══════════════════════════════════════════════════
  AGENT 2 — Complete (2 tips submitted)
═══════════════════════════════════════════════════

═══════════════════════════════════════════════════
  AGENT 3 — Starting (5 tips available)
═══════════════════════════════════════════════════

[thinking] I have 5 tips from Agents 1 and 2. Let me go through them...

★ TIP REFERENCE: "Agent-1's tip about python-dateutil is solid.
  Agent-2 also mentioned separating CLI from business logic —
  I'll use that pattern to make testing easier"

★ TIP REFERENCE: "Agent-2 suggested adding --format json. That's
  a great idea for composability, I'll include it"

...

══════════════════════════════════════════════════════════
  DEMO COMPLETE
  Agent 1 → 3 tips → Agent 2 → 2 tips → Agent 3 → 3 tips
  Total tips in knowledge base: 8
══════════════════════════════════════════════════════════
```
