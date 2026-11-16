"""LLM interface and a scripted fake for tests and offline mode."""

from typing import Protocol


class LLMUnavailable(Exception):
    """The language model could not be reached or answered badly."""


class LLM(Protocol):
    """Anything that completes a (system, user) prompt."""

    def complete(self, system: str, user: str) -> str:
        """Return the model's reply text."""
        ...


class FakeLLM:
    """Returns scripted replies in order, then ``NOT_FOUND``; records prompts."""

    def __init__(self, replies: list[str]) -> None:
        """Create a fake with scripted replies."""
        self.replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        """Record the prompt and return the next scripted reply."""
        self.calls.append((system, user))
        return self.replies.pop(0) if self.replies else "NOT_FOUND"
