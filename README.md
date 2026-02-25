# Full Auto Agent

A fully autonomous agent application that uses **Cursor CLI** to write code, design, build, test, and push to GitHub. Users interact via Discord; a scheduled job runner can invoke the agent for periodic tasks (e.g. read `sche_prompt.md`, process GitHub PRs/issues, build/test/maintain).

## Architecture

- **Two entrypoints**
  - **Discord client** — Listens for messages, runs the Cursor CLI agent with the user message as the prompt, and sends the agent’s output back to Discord. Each exchange is appended to shared memory.
  - **Job runner** — Invoked on a schedule (e.g. cron or APScheduler). Runs the agent with a fixed prompt (e.g. from `sche_prompt.md`) for periodic work.

- **Shared resources**
  - **Memory** — Stored in `memory.json`. When the number of messages exceeds 5, the agent is asked to summarize them and memory is replaced with a single summary so size stays bounded.
  - **Rules** — `.cursor/rules` define agent behavior (see Cursor docs). Recommended: always read the memory file.
  - **sche_prompt.md** — Can be written by the agent; read by the job runner as the source of periodic tasks.

## Prerequisites

- **Python 3.12+**
- **Cursor CLI** installed and on your `PATH` (Linux/macOS; for Windows see project notes)
- A **Discord server**, a **Discord bot**, and its **token**
- **Cursor API key** for headless/auth (create under Cursor → Integrations → User API Keys)

## Setup

1. **Clone and enter the repo**
   ```bash
   cd full_auto_agent
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate  # macOS/Linux
   pip install -e .
   # or with uv: uv pip install -e .
   ```

3. **Configure environment**
   - Copy `.env.example` to `.env`.
   - Set `DISCORD_TOKEN` and `CURSOR_API_KEY` (and any other variables).
   - Configure Cursor and repo settings as needed for the agent workspace.

4. **Cursor CLI**
   - Install Cursor CLI and ensure the `agent` command is available where you run the Discord client and job runner (Linux/macOS bash environment supported).

5. **Rules and memory**
   - Populate `.cursor/rules` to shape agent behavior.
   - Ensure the rule to read the memory file is present so the agent has shared context.

## Running the app

- **Discord client** (message handler; runs agent on each user message):
  ```bash
  python -m src.main discord-client
  ```
  Or with Typer CLI: `uv run python -m src.main discord-client`

- **Job runner** (scheduled agent run):
  ```bash
  python -m src.main job-runner
  ```

Run the Discord client in one process; schedule `job-runner` via cron, APScheduler, or your scheduler of choice.

## Testing

Install dev dependencies and run tests:

```bash
pip install -e ".[dev]"
# or: uv pip install -e ".[dev]"
pytest tests/ -v
```

Tests cover schema, logs, AI (sanitization and mocked agent), memory (load/save, summarization when > 5 messages), Discord comm service (env validation, `agent_run`, `on_message`), and main CLI commands. Mocks are used for subprocess, file I/O, and Discord so no real agent or Discord connection is required.

## Packages (dependencies)

| Package        | Purpose                                      |
|----------------|----------------------------------------------|
| `discord.py`   | Discord bot API; message handling.           |
| `APScheduler`  | Scheduling for periodic job runner.          |
| `python-dotenv`| Load `DISCORD_TOKEN`, `CURSOR_API_KEY` from `.env`. |
| `typer`       | CLI for `discord-client` and `job-runner`.   |

See `pyproject.toml` for versions. Optional dev deps: `pytest`, `pytest-asyncio`.

## Project layout

```
full_auto_agent/
├── README.md
├── pyproject.toml
├── .env.example
├── .cursor/
│   └── rules/           # Agent behavior rules
├── src/
│   ├── main.py          # Typer app: discord-client, job-runner
│   ├── comm_service.py  # Discord client + agent_run
│   ├── ai.py            # Cursor CLI agent invocation (sanitize + subprocess)
│   ├── memory.py        # memory.json load/save and summarization
│   ├── logs.py          # Logging config
│   └── schema.py        # EnvironmentVariablesNotFoundError
├── tests/
│   ├── test_schema.py
│   ├── test_logs.py
│   ├── test_ai.py
│   ├── test_memory.py
│   ├── test_comm_service.py
│   └── test_main.py
├── memory.json          # Created at runtime; conversation memory
└── sche_prompt.md       # Optional; prompt for job-runner
```

## Flow summary

1. User sends a message in Discord → Discord client receives it.
2. Client runs the Cursor CLI agent with the message as the prompt (no shell; prompt is sanitized). Agent may read/write memory and rules.
3. Agent output is sent back to the user and appended to `memory.json`. If message count > 5, the agent is asked to summarize and memory is replaced with one summary.
4. On a schedule, `job-runner` runs the agent (e.g. with prompt from `sche_prompt.md`) for periodic tasks, using the same memory and rules.

## License

MIT (or your choice).
