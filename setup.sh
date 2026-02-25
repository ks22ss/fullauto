#!/usr/bin/env bash
# Setup Cursor CLI for full-auto-agent (Linux/macOS, including headless VMs).
# Requires: bash, curl. For headless/VM use, set CURSOR_API_KEY in .env (app loads it) or export it.
set -e


# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

echo "Installing Cursor CLI..."
curl -fsSL https://cursor.com/install | bash

# Add ~/.local/bin to PATH if not already present (idempotent)
if ! grep -q '.local/bin' ~/.bashrc 2>/dev/null; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
  echo "Added PATH to ~/.bashrc"
fi

# Default Cursor CLI model (use Composer 1.5); set in .env for the app, or export in shell
if ! grep -q 'CURSOR_MODEL' ~/.bashrc 2>/dev/null; then
  echo 'export CURSOR_MODEL="composer-1.5"' >> ~/.bashrc
  echo "Added CURSOR_MODEL=composer-1.5 to ~/.bashrc"
fi

# Do NOT write a placeholder API key to .bashrc. Set CURSOR_API_KEY in .env for the app, or export it in your shell.
echo ""
echo "Next steps:"
echo "  1. Set CURSOR_API_KEY and DISCORD_TOKEN in this project's .env file (the app loads it), or export it in your shell."
echo "  2. Run: source ~/.bashrc   (or open a new terminal) so PATH takes effect."
echo "  3. On a headless VM: the app uses CURSOR_API_KEY from .env; no display needed."
echo "  4. If you run the app via systemd/cron, ensure CURSOR_API_KEY and DISCORD_TOKEN and PATH are set in that environment or use .env."

source ~/.bashrc 2>/dev/null || true
