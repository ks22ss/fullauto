import asyncio
import os
from typing import Optional

import discord
from dotenv import load_dotenv, set_key

load_dotenv()

import src.ai as ai
from src.config_store import get_repo_path, set_repo_path
from src.logs import get_logger
from src.memory import add_memory, list_messages, reset_memory
from src.schema import AgentError, EmptyPromptError, EnvironmentVariablesNotFoundError    
logger = get_logger(__name__)

token = os.getenv("DISCORD_TOKEN")
cursor_api_key = os.getenv("CURSOR_API_KEY")

# Proactive messaging settings (set via environment variables)
# - PROACTIVE_CHANNEL_ID: Discord channel ID to post into (integer as string)
# - PROACTIVE_INTERVAL_SECONDS: how often to post (default 3600)
# - PROACTIVE_PROMPT: prompt to feed the agent when generating proactive updates
PROACTIVE_CHANNEL_ID = os.getenv("PROACTIVE_CHANNEL_ID")
PROACTIVE_INTERVAL_SECONDS = int(os.getenv("PROACTIVE_INTERVAL_SECONDS", "3600"))
PROACTIVE_PROMPT = os.getenv(
    "PROACTIVE_PROMPT",
    "Send a short proactive update. If you have nothing useful, say 'No updates.'",
)
_proactive_task: Optional[asyncio.Task] = None  # prevent duplicate loops on reconnect

# Memory-to-prompt budgeting
# Caps how much stored memory is prepended to the agent prompt to keep latency/cost stable.
MAX_MEMORY_PROMPT_CHARS = int(os.getenv("MAX_MEMORY_PROMPT_CHARS", "12000"))
MAX_MEMORY_ITEMS = int(os.getenv("MAX_MEMORY_ITEMS", "12"))


def _get_discord_client():
    intents = discord.Intents.default()
    intents.message_content = True
    return discord.Client(intents=intents)

def _build_memory_prefix(prior: list[str]) -> str:
    """
    Build a bounded memory prefix string from stored messages.
    Strategy: take the most recent items up to MAX_MEMORY_ITEMS, then trim to MAX_MEMORY_PROMPT_CHARS.
    """
    if not prior:
        return ""
    recent = prior[-MAX_MEMORY_ITEMS:]
    joined = "\n".join(recent).strip()
    if not joined:
        return ""
    if len(joined) <= MAX_MEMORY_PROMPT_CHARS:
        return joined
    # Keep the most recent tail within budget.
    return joined[-MAX_MEMORY_PROMPT_CHARS:]


async def agent_run(prompt: str) -> str:
    """Run the agent on the prompt. On success returns the response and adds to memory. On error raises EmptyPromptError or AgentError; caller should send the error message (do not add to memory)."""
    # Run blocking generate_response in a thread so the event loop can process Discord heartbeats
    prior = list_messages()
    mem_prefix = _build_memory_prefix(prior)
    combined_prompt = prompt
    if mem_prefix:
        combined_prompt = mem_prefix + "\n\n" + prompt
    res_message = await asyncio.to_thread(ai.generate_response, combined_prompt)
    add_memory(f"User: {prompt}\n\n Agent: {res_message}\n\n")

    return res_message


client = _get_discord_client()

async def _get_target_channel() -> Optional[discord.abc.Messageable]:
    """Return the configured target channel (cached or fetched)."""
    if not PROACTIVE_CHANNEL_ID:
        return None
    try:
        channel_id = int(PROACTIVE_CHANNEL_ID)
    except ValueError:
        logger.error("PROACTIVE_CHANNEL_ID must be an integer string.")
        return None

    ch = client.get_channel(channel_id)
    if ch is not None:
        return ch

    try:
        return await client.fetch_channel(channel_id)
    except Exception:
        logger.exception("Failed to fetch channel %s", channel_id)
        return None


async def _proactive_loop() -> None:
    """Background loop that proactively sends messages to a configured channel."""
    await client.wait_until_ready()

    channel = await _get_target_channel()
    if channel is None:
        logger.info("Proactive loop disabled (no valid PROACTIVE_CHANNEL_ID).")
        return

    logger.info(
        "Proactive loop started: interval=%ss channel=%s",
        PROACTIVE_INTERVAL_SECONDS,
        PROACTIVE_CHANNEL_ID,
    )

    while not client.is_closed():
        try:
            async with channel.typing():
                msg = await agent_run(PROACTIVE_PROMPT)
            msg = (msg or "").strip()
            if msg:
                await channel.send(msg)
        except Exception:
            logger.exception("Proactive loop iteration failed")

        await asyncio.sleep(PROACTIVE_INTERVAL_SECONDS)


@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user}")

    # Start proactive background task once (avoid duplicates on reconnect).
    global _proactive_task
    if _proactive_task is None or _proactive_task.done():
        _proactive_task = asyncio.create_task(_proactive_loop())

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    logger.info(f"Message received, total bytes: {len(message.content)}")
    await message.add_reaction("🤖")

    prompt = message.content
    # Handle /cwd <absolute_path> to update working directory for the agent and persist to config.json
    if prompt.startswith("/cwd"):
        parts = prompt.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await message.channel.send("Usage: /cwd /absolute/path")
            return
        new_path = parts[1].strip()
        if not os.path.isabs(new_path):
            await message.channel.send("Path must be absolute.")
            return
        if not os.path.isdir(new_path):
            await message.channel.send("Path does not exist or is not a directory.")
            return
        set_repo_path(new_path)
        ai.repo_path = get_repo_path()
        await message.channel.send(f"Working directory set to: {new_path}")
        return
    
    # Handle /reset-memory to clear all stored conversation history
    if prompt.startswith("/reset-memory"):
        reset_memory()
        await message.channel.send("✅ Memory reset: All conversation history has been cleared.")
        return

    async with message.channel.typing():
        try:
            res_message = await agent_run(prompt)
            await message.channel.send(res_message)
        except (EmptyPromptError, AgentError) as e:
            await message.channel.send(str(e))
            # Do not add to memory on error

def listen_to_discord():
    if not token:
        raise EnvironmentVariablesNotFoundError("DISCORD_TOKEN is not set.")
    if not cursor_api_key:
        raise EnvironmentVariablesNotFoundError("CURSOR_API_KEY is not set.")

    client.run(token)

async def start_discord_client():
    """Start Discord client in async mode (for use with concurrent services)"""
    if not token:
        raise EnvironmentVariablesNotFoundError("DISCORD_TOKEN is not set.")
    if not cursor_api_key:
        raise EnvironmentVariablesNotFoundError("CURSOR_API_KEY is not set.")
    
    await client.start(token)