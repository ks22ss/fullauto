import asyncio
import os

import discord
from dotenv import load_dotenv, set_key

load_dotenv()

import src.ai as ai
from src.config_store import get_repo_path, set_repo_path
from src.logs import get_logger
from src.memory import add_memory, list_messages
from src.schema import AgentError, EmptyPromptError, EnvironmentVariablesNotFoundError    
logger = get_logger(__name__)

token = os.getenv("DISCORD_TOKEN")
cursor_api_key = os.getenv("CURSOR_API_KEY")


def _get_discord_client():
    intents = discord.Intents.default()
    intents.message_content = True
    return discord.Client(intents=intents)


async def agent_run(prompt: str) -> str:
    """Run the agent on the prompt. On success returns the response and adds to memory. On error raises EmptyPromptError or AgentError; caller should send the error message (do not add to memory)."""
    # Run blocking generate_response in a thread so the event loop can process Discord heartbeats
    prior = list_messages()
    combined_prompt = f"{prompt}"
    if prior:
        combined_prompt = "\n".join(prior) + "\n\n" + prompt
    res_message = await asyncio.to_thread(ai.generate_response, combined_prompt)
    add_memory(f"User: {prompt}\n\n Agent: {res_message}\n\n")

    return res_message


client = _get_discord_client()


@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user}")

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