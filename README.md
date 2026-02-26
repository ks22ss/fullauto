# Full Auto Agent

A fully autonomous agent application that uses **Cursor CLI** to write code, design, build, test, and push to GitHub. Users interact via Discord, and scheduled tasks run automatically based on cron schedules.

> **Note:** This project currently only works on **Linux**. Windows and macOS are not tested.

## Features

- **Discord Integration** - Interact with the agent via Discord messages
- **Scheduled Tasks** - Automatically run tasks on a schedule (cleanup, PR reviews, security checks, etc.)
- **Shared Memory** - Agent maintains context across interactions
- **Task Scheduling** - Configure tasks with cron expressions in `src/tasks/.config.json`

## Prerequisites

- **Linux** operating system
- **Python 3.12+**
- **Cursor CLI** installed and on your `PATH`
- A **Discord server**, a **Discord bot**, and its **token**
- **Cursor API key** (create under Cursor → Integrations → User API Keys)

## Installation

1. **Setup the repository**
  clone the repository to your VM and run:
   ```bash
   git clone https://github.com/ks22ss/fullauto.git
   cd fullauto
   source setup.sh
   uv sync
   source .venv/bin/activate
   ```

2. **Configure environment variables**
   - Set the following variables:
     ```bash
     echo 'export DISCORD_TOKEN="paste_your_discord_bot_token"' >> ~/.bashrc
     echo 'export CURSOR_API_KEY="paste_your_cursor_api_key"' >> ~/.bashrc
     echo 'export GH_TOKEN="paste_your_github_token"' >> ~/.bashrc
     source ~/.bashrc  # or open a new terminal
     ```
   
   **Why these are needed:**
   
   - **Discord Token (`DISCORD_TOKEN`)**: Required for the Discord bot to connect and receive messages. The bot listens for your commands and sends agent responses back to Discord.
     - **Setup**: Go to [Discord Developer Portal](https://discord.com/developers/applications) → Create New Application → Bot → Copy Token
   
   - **Cursor API Key (`CURSOR_API_KEY`)**: Authenticates the agent with Cursor's API to execute code generation and analysis tasks. This is how the agent actually performs its work.
     - **Setup**: Open Cursor IDE → Settings → Integrations → User API Keys → Create New Key → Copy the key
   
   - **GitHub Token (`GH_TOKEN`)**: Allows the agent to interact with GitHub repositories (push code, create PRs, manage issues). Required for scheduled tasks that modify repositories.
     - **Setup**: Go to [GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)](https://github.com/settings/tokens) → Generate new token → Select `repo` scope → Copy token


## Usage

After installation, you can use the `fullauto` CLI command:

### Run Both Services (Recommended)

Run the Discord client and scheduler together:

```bash
fullauto run
```

This starts both:
- **Discord client** - Listens for messages and responds via Discord
- **Scheduler** - Runs scheduled tasks based on cron expressions

### Run Services Individually

**Discord client only:**
```bash
fullauto discord-client
```

**Scheduler only:**
```bash
fullauto scheduler
```

### Reset Memory

Clear all stored conversation history:

```bash
fullauto reset-memory-cmd
```

### View Available Commands

```bash
fullauto --help
```

## Task Configuration

Scheduled tasks are configured in `src/tasks/.config.json`. Each task has:
- A **schedule** (cron expression)
- A **description**
- A corresponding markdown file in `src/tasks/` with task instructions

Example configuration:
```json
{
  "tasks": {
    "cleanup": {
      "schedule": "0 1 * * *",
      "description": "Every day at 1am"
    },
    "pr_review": {
      "schedule": "20 * * * *",
      "description": "Every hour at 20 minutes"
    }
  }
}
```

### Available Tasks

- **cleanup** - Repository hygiene (stale issues/PRs, TODO comments, broken links)
- **increment** - Incremental code quality improvements
- **security_check** - Security vulnerability scanning
- **pr_review** - Automated PR reviews and fixes
- **issue_fixer** - Automatic issue resolution
- **health_check** - System health monitoring

Each task's instructions are defined in `src/tasks/<task_name>.md`.

## Discord Commands

When the Discord client is running, you can interact with the agent:

- **Send a message** - The agent will process your message and respond
- **`/cwd <absolute_path>`** - Change the working directory for the agent
- **`/reset-memory`** - Clear all stored conversation history (starts fresh)


## How It Works

1. **Discord Interaction**
   - User sends a message in Discord
   - Discord client receives it and runs the Cursor CLI agent
   - Agent output is sent back to Discord and stored in memory

2. **Scheduled Tasks**
   - Scheduler checks cron expressions from `src/tasks/.config.json`
   - When a task is due, it reads the corresponding markdown file
   - Task instructions are passed to the agent for execution
   - Results are logged

3. **Memory Management**
   - All interactions are stored in shared memory
   - When memory exceeds 5 messages, it's automatically summarized
   - Memory persists across sessions

## Testing

Install dev dependencies and run tests:

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Troubleshooting

- **Command not found**: Make sure you've installed the package with `pip install -e .`
- **Discord connection fails**: Verify `DISCORD_TOKEN` is set correctly in `.env`
- **Agent errors**: Ensure Cursor CLI is installed and `CURSOR_API_KEY` is valid
- **Tasks not running**: Check cron expressions in `src/tasks/.config.json` are valid

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.
