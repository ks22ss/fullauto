import asyncio
import os

import typer

from src.comm_service import agent_run, listen_to_discord
from src.logs import get_logger

logger = get_logger(__name__)

app = typer.Typer()

os.makedirs(".cursor", exist_ok=True)
os.makedirs(".cursor/rules", exist_ok=True)

@app.command()
def discord_client():
    """Run the Discord client."""
    logger.info("Starting Discord client...")
    listen_to_discord()

@app.command()
def job_runner():
    """Being Scheduled to run the job."""
    logger.info("Running job...")
    prompt = "TBC.."
    asyncio.run(agent_run(prompt))
    logger.info("Job completed.")

if __name__ == "__main__":
    app()