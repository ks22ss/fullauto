import os
import re
import subprocess

from src.logs import get_logger
from src.schema import AgentError, EmptyPromptError, EnvironmentVariablesNotFoundError

logger = get_logger(__name__)

def _find_repo_root() -> str:
    """Return the repo root by walking up until .git is found; fallback to parent of src/."""
    path = os.path.abspath(os.path.dirname(__file__))
    while path and path != os.path.dirname(path):
        if os.path.isdir(os.path.join(path, ".git")):
            return path
        path = os.path.dirname(path)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_repo_path() -> str:
    """Use REPO_PATH env if absolute+existing, else repo root."""
    env_path = os.getenv("REPO_PATH")
    if env_path and os.path.isabs(env_path) and os.path.isdir(env_path):
        return env_path
    return _find_repo_root()


# Mutable so it can be updated at runtime (e.g., via /cwd command).
repo_path = _resolve_repo_path()


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
        raise EmptyPromptError("Please send a non-empty message.")

    model = os.getenv("CURSOR_MODEL", "composer-1.5")
    cmd = [
        "agent",
        "-p", "--force", "--model", model,
        sanitized,
        "--output-format=text",
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=1800,
        cwd=repo_path,
    )
    logger.info("Return code: %s", result.returncode)
    logger.info("STDOUT: %s", result.stdout)
    logger.info("STDERR: %s", result.stderr)
    output = result.stdout
    if result.returncode == 0:
        logger.info(f"Successfully generated response: bytes: {len(output)}")
        return output
    logger.error(f"Error generating response: {result.stderr}")
    raise AgentError("Sorry, I encountered an error. Please try again later.", stderr=result.stderr or "")