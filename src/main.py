import asyncio
import json
import os
from pathlib import Path

import typer
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.comm_service import agent_run, listen_to_discord, start_discord_client
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


def load_task_config():
    """Load task configuration from .config.json"""
    config_path = Path(__file__).parent / "tasks" / ".config.json"
    with open(config_path, "r") as f:
        return json.load(f)

def read_task_file(task_name: str) -> str:
    """Read the task markdown file content"""
    task_path = Path(__file__).parent / "tasks" / f"{task_name}.md"
    if not task_path.exists():
        logger.error(f"Task file not found: {task_path}")
        return ""
    with open(task_path, "r", encoding="utf-8") as f:
        return f.read()

async def run_task(task_name: str):
    """Run a specific task by reading its markdown file and executing it"""
    logger.info(f"Starting scheduled task: {task_name}")
    try:
        task_content = read_task_file(task_name)
        if not task_content:
            logger.error(f"Empty task content for {task_name}")
            return
        
        await agent_run(task_content)
        logger.info(f"Completed scheduled task: {task_name}")
    except Exception as e:
        logger.error(f"Error running task {task_name}: {e}", exc_info=True)

def parse_cron_expression(cron_str: str) -> dict:
    """Parse cron expression (minute hour day month day_of_week) into APScheduler format
    
    Standard cron: day_of_week 0-6 where 0=Sunday
    APScheduler: day_of_week 0-6 where 0=Monday
    Conversion: apscheduler_dow = (cron_dow + 6) % 7
    """
    parts = cron_str.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_str}. Expected 5 parts (minute hour day month day_of_week).")
    
    minute, hour, day, month, day_of_week = parts
    
    trigger_kwargs = {}
    
    if minute != "*":
        trigger_kwargs["minute"] = minute if minute.isdigit() else minute
    if hour != "*":
        trigger_kwargs["hour"] = hour if hour.isdigit() else hour
    if day != "*":
        trigger_kwargs["day"] = day if day.isdigit() else day
    if month != "*":
        trigger_kwargs["month"] = month if month.isdigit() else month
    if day_of_week != "*":
        # Convert day_of_week from standard cron (0=Sunday) to APScheduler (0=Monday)
        if day_of_week.isdigit():
            cron_dow = int(day_of_week)
            # Convert: cron 0(Sun)->6, 1(Mon)->0, 2(Tue)->1, ..., 6(Sat)->5
            apscheduler_dow = (cron_dow + 6) % 7
            trigger_kwargs["day_of_week"] = apscheduler_dow
        else:
            # Handle string values like "mon", "tue", etc. (APScheduler supports these)
            trigger_kwargs["day_of_week"] = day_of_week
    
    return trigger_kwargs

async def _run_scheduler():
    """Internal async function to run the scheduler"""
    logger.info("Starting task scheduler...")
    
    # Load task configuration
    config = load_task_config()
    tasks = config.get("tasks", {})
    
    if not tasks:
        logger.warning("No tasks found in configuration")
        return
    
    # Create async scheduler
    scheduler_instance = AsyncIOScheduler()
    
    # Schedule each task
    for task_name, task_config in tasks.items():
        schedule = task_config.get("schedule")
        description = task_config.get("description", "")
        
        if not schedule:
            logger.warning(f"No schedule found for task: {task_name}")
            continue
        
        try:
            # Parse cron expression
            trigger_kwargs = parse_cron_expression(schedule)
            trigger = CronTrigger(**trigger_kwargs)
            
            # Schedule the task
            scheduler_instance.add_job(
                run_task,
                trigger=trigger,
                args=[task_name],
                id=task_name,
                name=f"{task_name} - {description}",
                replace_existing=True
            )
            logger.info(f"Scheduled task '{task_name}': {schedule} ({description})")
        except Exception as e:
            logger.error(f"Failed to schedule task '{task_name}': {e}", exc_info=True)
    
    # Start the scheduler
    scheduler_instance.start()
    logger.info(f"Scheduler started with {len(scheduler_instance.get_jobs())} jobs")
    
    try:
        # Keep the scheduler running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        scheduler_instance.shutdown()
        logger.info("Scheduler stopped.")

@app.command()
def scheduler():
    """Run the scheduler to execute tasks based on their cron schedules."""
    asyncio.run(_run_scheduler())

async def _run_all():
    """Run both Discord client and scheduler concurrently"""
    logger.info("Starting fullauto services...")
    
    # Create tasks for both services
    discord_task = asyncio.create_task(start_discord_client())
    scheduler_task = asyncio.create_task(_run_scheduler())
    
    try:
        # Wait for both tasks (they run concurrently)
        await asyncio.gather(discord_task, scheduler_task)
    except KeyboardInterrupt:
        logger.info("Shutting down services...")
        # Cancel both tasks
        discord_task.cancel()
        scheduler_task.cancel()
        # Wait for cleanup
        try:
            await asyncio.gather(discord_task, scheduler_task, return_exceptions=True)
        except Exception:
            pass
        logger.info("Services stopped.")

@app.command()
def run():
    """Run both Discord client and scheduler concurrently."""
    asyncio.run(_run_all())

if __name__ == "__main__":
    app()