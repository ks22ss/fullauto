class EnvironmentVariablesNotFoundError(Exception):
    pass


class EmptyPromptError(Exception):
    """Raised when the user prompt is empty or invalid after sanitization."""

    def __init__(self, message: str = "Please send a non-empty message."):
        super().__init__(message)
        self.message = message


class AgentError(Exception):
    """Raised when the Cursor CLI agent fails (non-zero exit)."""

    def __init__(self, message: str = "Sorry, I encountered an error. Please try again later.", stderr: str = ""):
        super().__init__(message)
        self.message = message
        self.stderr = stderr