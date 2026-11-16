"""Local LLM via the Ollama HTTP API."""

import httpx

from reception.config import LLMConfig
from reception.llm.base import LLMUnavailable


class OllamaLLM:
    """Chat completion against a local Ollama server (temperature 0)."""

    def __init__(self, cfg: LLMConfig) -> None:
        """Create a client from config."""
        self.cfg = cfg

    def complete(self, system: str, user: str) -> str:
        """Send one chat turn and return the reply text.

        Raises:
            LLMUnavailable: Server unreachable, timed out, or malformed reply.
        """
        try:
            r = httpx.post(
                f"{self.cfg.base_url.rstrip('/')}/api/chat",
                json={
                    "model": self.cfg.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "stream": False,
                    "options": {"temperature": 0},
                },
                timeout=self.cfg.timeout_s,
            )
            r.raise_for_status()
            return str(r.json()["message"]["content"])
        except (httpx.HTTPError, KeyError, ValueError) as e:
            raise LLMUnavailable(str(e)) from e
