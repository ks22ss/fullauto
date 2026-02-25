import discord
import os
from dotenv import load_dotenv
from src.memory import add_memory
from src.logs import get_logger
from src.ai import generate_response
from src.schema import AgentError, EmptyPromptError, EnvironmentVariablesNotFoundError    

load_dotenv()
logger = get_logger(__name__)

token = os.getenv("DISCORD_TOKEN")
cursor_api_key = os.getenv("CURSOR_API_KEY")


def _get_discord_client():
    intents = discord.Intents.default()
    intents.message_content = True
    return discord.Client(intents=intents)


async def agent_run(prompt: str) -> str:
    """Run the agent on the prompt. On success returns the response and adds to memory. On error raises EmptyPromptError or AgentError; caller should send the error message (do not add to memory)."""
    res_message = generate_response(prompt)
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
