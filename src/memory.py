import json
import os

from src.ai import generate_response
from src.logs import get_logger

logger = get_logger(__name__)

memory_file = "memory.json"
MAX_MESSAGES_BEFORE_SUMMARY = 5


def _load_messages() -> list[str]:
    """Read memory.json and return the list of messages. Returns [] if file missing or invalid."""
    if not os.path.isfile(memory_file):
        return []

    with open(memory_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return data.get("messages", []) if isinstance(data, dict) else []


def _save_messages(messages: list[str]) -> None:
    """Write the list of messages to memory.json."""
    with open(memory_file, "w", encoding="utf-8") as f:
        json.dump({"messages": messages}, f, ensure_ascii=False, indent=2)


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
    """Append a message to memory. If there are more than MAX_MESSAGES_BEFORE_SUMMARY messages, summarize and replace with one summary."""
    messages = _load_messages()
    messages.append(message.strip())
    count = len(messages)

    if count > MAX_MESSAGES_BEFORE_SUMMARY:
        logger.info("Memory has %d messages; summarizing via agent", count)
        summary = _summarize_messages(messages)
        summary = summary.strip()
        if summary:
            messages = [summary]
            _save_messages(messages)
            logger.info("Memory replaced with 1 summary entry")
        else:
            # Summarization failed; keep recent messages only
            messages = messages[-MAX_MESSAGES_BEFORE_SUMMARY:]
            _save_messages(messages)
            logger.warning("Summarization returned empty; kept last %d messages", len(messages))
    else:
        _save_messages(messages)


def get_message_count() -> int:
    """Return the number of messages currently in memory."""
    return len(_load_messages())
