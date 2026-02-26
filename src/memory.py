"""
Persistent memory manager using FIFO queue with automatic summarization.

This module provides a disk-backed memory system that maintains conversation context
across agent sessions. Memory is stored in a FIFO (First-In-First-Out) queue that
persists to disk at `/root/.fullauto/memory`.

How it works:
1. **Message Storage**: Each agent interaction (user message + agent response) is
   stored as a single entry in the queue. Messages are automatically persisted to disk.

2. **Automatic Summarization**: When the queue exceeds MAX_MESSAGES_BEFORE_SUMMARY (5),
   all messages are extracted and sent to the agent for summarization. The agent
   creates a concise summary that captures key facts and decisions.

3. **Memory Replacement**: The original messages are replaced with a single summary
   entry, keeping memory compact while preserving important context.

4. **Persistence**: Memory persists across agent restarts. When the agent starts,
   previous memory is automatically loaded from disk.

5. **Thread/Process Safety**: Uses file locking to prevent race conditions when
   multiple processes access memory simultaneously.

Example flow:
    t=0: [msg_1, msg_2, msg_3, msg_4]           # 4 messages
    t=1: [msg_1, msg_2, msg_3, msg_4, msg_5]   # 5 messages (at threshold)
    t=2: [summary_of_1_to_5]                    # Summarized to 1 entry
    t=3: [summary_of_1_to_5, msg_6]            # New message added
    t=4: [summary_of_1_to_5, msg_6, msg_7, ...] # Continues...

Benefits:
- Maintains context across multiple interactions
- Prevents memory from growing unbounded
- Preserves important information through summarization
- Survives agent restarts and system reboots
- Thread-safe and process-safe with file locking
"""
import fcntl
import os
from contextlib import contextmanager
from pathlib import Path

import persistqueue

from src.ai import generate_response
from src.config_store import get_repo_path
from src.logs import get_logger

logger = get_logger(__name__)

# Fixed absolute storage directory
QUEUE_DIR = Path("/root/.fullauto/memory")
QUEUE_DIR.mkdir(parents=True, exist_ok=True)
queue = persistqueue.Queue(str(QUEUE_DIR))

# Lock file for synchronizing access across processes
LOCK_FILE = QUEUE_DIR / ".lock"
MAX_MESSAGES_BEFORE_SUMMARY = 5


@contextmanager
def _memory_lock():
    """Acquire an exclusive lock on the memory queue to prevent race conditions."""
    lock_fd = None
    try:
        # Open lock file in append mode (create if doesn't exist)
        lock_fd = open(LOCK_FILE, "a")
        # Acquire exclusive lock (blocks until available)
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if lock_fd:
            # Release lock
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()


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
    
    with _memory_lock():
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
    with _memory_lock():
        return queue.qsize()


def list_messages() -> list[str]:
    """Return all messages without removing them from the queue. Thread-safe."""
    with _memory_lock():
        messages: list[str] = []
        count = queue.qsize()
        for _ in range(count):
            item = queue.get()
            messages.append(item)
        # Requeue in original order
        for item in messages:
            queue.put(item)
        return messages


def reset_memory() -> None:
    """Clear all messages from memory. This permanently deletes all stored conversation history."""
    with _memory_lock():
        count = queue.qsize()
        try:
            while True:
                queue.get_nowait()
        except Exception:
            pass
        logger.info(f"Memory reset: {count} message(s) cleared")
