import subprocess
from src.logs import get_logger
import re

logger = get_logger(__name__)

def _sanitize_prompt(prompt: str) -> str:
    """
    Sanitize user input before passing to agent. 
    No shell is used (list argv), 
    so shell injection is not possible; 
    this guards against other abuse.
    """
    if not prompt or not prompt.strip():
        return ""
    # Strip null bytes and other control characters that could confuse the CLI or downstream.
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", prompt)
    sanitized = sanitized.strip()
    return sanitized



def generate_response(prompt: str) -> str:
    sanitized = _sanitize_prompt(prompt)
    if not sanitized:
        return "Please send a non-empty message."
    # List form, no shell=True: prompt is passed as a single argument to the executable (no shell injection).
    cmd = [
        "agent",
        "-p", "--force", "--mode=agent",
        "--output-format", "json",
        sanitized,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    output = result.stdout
    if result.returncode == 0:
        logger.info(f"Successfully generated response: bytes: {len(output)}")
        return output
    else:
        logger.error(f"Error generating response: {result.stderr}")
        return f"Sorry, I encountered an error. Please try again later."