"""Persisted memory using persistqueue FIFO with summarization."""

import os
from pathlib import Path

import persistqueue

from src.ai import generate_response
from src.logs import get_logger

logger = get_logger(__name__)

# Fixed absolute storage directory
QUEUE_DIR = Path("/root/.fullauto_memory")
QUEUE_DIR.mkdir(parents=True, exist_ok=True)
queue = persistqueue.Queue(str(QUEUE_DIR))

MAX_MESSAGES_BEFORE_SUMMARY = 5


def _summarize_messages(messages: list[str]) -> str:
    """Use the agent to summarize the given messages into one concise summary."""
    combined = "\n".join(f"- {m}" for m in messages)
    prompt = (
        "Summarize the following messages into one short, concise summary paragraph. "
        "Keep only the main facts and decisions. Output only the summary text, no preamble.\n\n"
        f"{combined}"
    )
    return generate_response(prompt)


def add_memory(message: str) -> None:
    """Append a message; if total > MAX, summarize and replace with one summary."""
    msg = (message or "").strip()
    if not msg:
        return
    queue.put(msg)
    if queue.qsize() > MAX_MESSAGES_BEFORE_SUMMARY:
        logger.info("Memory has %d messages; summarizing via agent", queue.qsize())
        items: list[str] = []
        try:
            while True:
                items.append(queue.get_nowait())
        except Exception:
            pass
        if not items:
            return
        summary = (_summarize_messages(items) or "").strip()
        if summary:
            queue.put(summary)
            logger.info("Memory replaced with 1 summary entry")
        else:
            # summarization failed; keep last MAX messages
            for m in items[-MAX_MESSAGES_BEFORE_SUMMARY:]:
                queue.put(m)
            logger.warning(
                "Summarization returned empty; kept last %d messages",
                queue.qsize(),
            )


def get_message_count() -> int:
    """Return the number of messages currently in memory."""
    return queue.qsize()
