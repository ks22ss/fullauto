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
import json
import os
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Tuple

import persistqueue
import portalocker

from src.ai import generate_response
from src.config_store import get_repo_path
from src.logs import get_logger

logger = get_logger(__name__)

# Prefix to distinguish structured JSON entries from legacy plain strings.
_STRUCTURED_PREFIX = "__fullauto_msg__:"


@dataclass(frozen=True)
class Message:
    """
    Structured memory message.

    role: "user" | "assistant" | "system"
    kind: "turn" | "summary" | "note"
    """

    role: str
    content: str
    ts: float
    kind: str = "turn"
    meta: Optional[dict[str, Any]] = None


# Fixed storage directory (cross-platform). Override with FULLAUTO_HOME if needed.
FULLAUTO_HOME = Path(os.getenv("FULLAUTO_HOME", str(Path.home() / ".fullauto"))).expanduser()
QUEUE_DIR = FULLAUTO_HOME / "memory"
QUEUE_DIR.mkdir(parents=True, exist_ok=True)
queue = persistqueue.Queue(str(QUEUE_DIR))

# Lock file for synchronizing access across processes
LOCK_FILE = QUEUE_DIR / ".lock"
MAX_MESSAGES_BEFORE_SUMMARY = 5  # legacy name; counts queue entries
MAX_ENTRIES_BEFORE_SUMMARY = int(os.getenv("MAX_MEMORY_ENTRIES_BEFORE_SUMMARY", str(MAX_MESSAGES_BEFORE_SUMMARY)))
MAX_ENTRY_CHARS = int(os.getenv("MAX_MEMORY_ENTRY_CHARS", "8000"))


_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Common env-var style secrets
    (re.compile(r'(?i)\b(DISCORD_TOKEN|CURSOR_API_KEY|GH_TOKEN)\s*=\s*["\']?[^"\'\s]+["\']?'), r"\1=<redacted>"),
    # Generic token-ish strings (very conservative: only redact long contiguous tokens)
    (re.compile(r"(?i)\b(token|api[_-]?key|secret)\b\s*[:=]\s*([A-Za-z0-9_\-]{16,})"), r"\1=<redacted>"),
]


def _sanitize_for_storage(text: str) -> str:
    """Bound and lightly redact sensitive-looking strings before persisting to disk."""
    s = (text or "").strip()
    if not s:
        return ""
    for pattern, repl in _SECRET_PATTERNS:
        s = pattern.sub(repl, s)
    if len(s) > MAX_ENTRY_CHARS:
        s = s[:MAX_ENTRY_CHARS].rstrip() + "\n\n[...truncated...]"
    return s


def _encode_message(msg: Message) -> str:
    payload = {
        "v": 1,
        "role": msg.role,
        "content": msg.content,
        "ts": msg.ts,
        "kind": msg.kind,
        "meta": msg.meta or {},
    }
    return _STRUCTURED_PREFIX + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _try_decode_item(item: Any) -> Tuple[Optional[Message], Optional[str]]:
    """
    Decode a queue item.
    Returns (Message|None, legacy_text|None).
    """
    if isinstance(item, str) and item.startswith(_STRUCTURED_PREFIX):
        raw = item[len(_STRUCTURED_PREFIX) :]
        try:
            payload = json.loads(raw)
            role = str(payload.get("role", "system"))
            content = str(payload.get("content", ""))
            ts = float(payload.get("ts", time.time()))
            kind = str(payload.get("kind", "turn"))
            meta = payload.get("meta") or {}
            if not isinstance(meta, dict):
                meta = {}
            return Message(role=role, content=content, ts=ts, kind=kind, meta=meta), None
        except Exception:
            return None, item
    if isinstance(item, str):
        return None, item
    return None, str(item)


def _render_for_context(msg: Message) -> str:
    if msg.kind == "summary":
        return f"Summary: {msg.content}".strip()
    if msg.role == "user":
        return f"User: {msg.content}".strip()
    if msg.role == "assistant":
        return f"Agent: {msg.content}".strip()
    return msg.content.strip()


def _summarize_items(items: list[Any]) -> str:
    rendered: list[str] = []
    for it in items:
        msg, legacy = _try_decode_item(it)
        if msg is not None:
            rendered.append(_render_for_context(msg))
        elif legacy is not None and legacy.strip():
            rendered.append(legacy.strip())
    return _summarize_messages(rendered)


@contextmanager
def _memory_lock():
    """Acquire an exclusive lock on the memory queue to prevent race conditions."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with portalocker.Lock(str(LOCK_FILE), timeout=30):
        yield


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
    """
    Append a legacy string message; if total > threshold, summarize and replace with one summary.

    Prefer using add_turn(...) for new code so memory stays structured.
    """
    msg = _sanitize_for_storage(message)
    if not msg:
        return
    
    with _memory_lock():
        queue.put(msg)
        if queue.qsize() > MAX_ENTRIES_BEFORE_SUMMARY:
            logger.info("Memory has %d messages; summarizing via agent", queue.qsize())
            items: list[Any] = []
            try:
                while True:
                    items.append(queue.get_nowait())
            except Exception:
                pass
            if not items:
                return
            summary = (_summarize_items(items) or "").strip()
            if summary:
                queue.put(_encode_message(Message(role="system", content=summary, ts=time.time(), kind="summary")))
                logger.info("Memory replaced with 1 summary entry")
            else:
                # summarization failed; keep last MAX messages
                for m in items[-MAX_ENTRIES_BEFORE_SUMMARY:]:
                    queue.put(m)
                logger.warning(
                    "Summarization returned empty; kept last %d messages",
                    queue.qsize(),
                )


def add_turn(
    user_text: str,
    assistant_text: str,
    *,
    source: str = "discord",
    meta: Optional[dict[str, Any]] = None,
) -> None:
    """Add a structured user+assistant turn to memory."""
    u = _sanitize_for_storage(user_text)
    a = _sanitize_for_storage(assistant_text)
    if not u and not a:
        return

    base_meta: dict[str, Any] = {"source": source}
    if meta:
        base_meta.update(meta)

    with _memory_lock():
        now = time.time()
        if u:
            queue.put(_encode_message(Message(role="user", content=u, ts=now, kind="turn", meta=base_meta)))
        if a:
            queue.put(_encode_message(Message(role="assistant", content=a, ts=now, kind="turn", meta=base_meta)))

        if queue.qsize() > MAX_ENTRIES_BEFORE_SUMMARY:
            logger.info("Memory has %d entries; summarizing via agent", queue.qsize())
            items: list[Any] = []
            try:
                while True:
                    items.append(queue.get_nowait())
            except Exception:
                pass
            if not items:
                return
            summary = (_summarize_items(items) or "").strip()
            if summary:
                queue.put(_encode_message(Message(role="system", content=summary, ts=time.time(), kind="summary")))
                logger.info("Memory replaced with 1 summary entry")
            else:
                for m in items[-MAX_ENTRIES_BEFORE_SUMMARY:]:
                    queue.put(m)
                logger.warning(
                    "Summarization returned empty; kept last %d entries",
                    queue.qsize(),
                )


def get_message_count() -> int:
    """Return the number of messages currently in memory."""
    with _memory_lock():
        return queue.qsize()

def list_message_objects() -> list[Message]:
    """Return structured messages (legacy strings are converted to system notes)."""
    with _memory_lock():
        objs: list[Message] = []
        count = queue.qsize()
        originals: list[Any] = []
        for _ in range(count):
            it = queue.get()
            originals.append(it)
            msg, legacy = _try_decode_item(it)
            if msg is not None:
                objs.append(msg)
            elif legacy is not None and legacy.strip():
                objs.append(Message(role="system", content=legacy.strip(), ts=time.time(), kind="note"))
        for it in originals:
            queue.put(it)
        return objs


def list_messages() -> list[str]:
    """Return all messages as rendered strings without removing them from the queue. Thread-safe."""
    with _memory_lock():
        rendered: list[str] = []
        count = queue.qsize()
        originals: list[Any] = []
        for _ in range(count):
            it = queue.get()
            originals.append(it)
            msg, legacy = _try_decode_item(it)
            if msg is not None:
                rendered.append(_render_for_context(msg))
            elif legacy is not None and legacy.strip():
                rendered.append(legacy.strip())
        # Requeue in original order
        for it in originals:
            queue.put(it)
        return rendered


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
