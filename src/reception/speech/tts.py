"""Natural Hindi and Kannada voices (Microsoft neural voices via edge-tts).

Only the kiosk's own answer text is sent to the voice service, never what the
visitor said. If the service is unreachable the browser's built-in voice is used.
"""

import asyncio
from collections import OrderedDict
from typing import Protocol

from reception.config import TtsConfig

_CACHE_MAX = 300


class Speaker(Protocol):
    """Anything that turns text into MP3 audio."""

    async def synthesize(self, text: str, voice: str) -> bytes:
        """Return MP3 bytes of ``text`` read by ``voice``."""
        ...


class EdgeSpeaker:
    """Microsoft Edge online neural voices."""

    async def synthesize(self, text: str, voice: str) -> bytes:
        """Stream the voice service's audio into one MP3 blob."""
        import edge_tts

        audio = bytearray()
        async for chunk in edge_tts.Communicate(text, voice).stream():
            if chunk.get("type") == "audio":
                audio.extend(chunk["data"])
        return bytes(audio)


class TtsUnavailable(Exception):
    """No audio could be produced; the kiosk falls back to the browser voice."""


class VoiceService:
    """Language-aware speech synthesis with a small cache of recent answers."""

    def __init__(self, cfg: TtsConfig, speaker: Speaker | None = None) -> None:
        """Use ``speaker`` (default: Microsoft voices) with the configured voices."""
        self.cfg = cfg
        self.speaker = speaker or EdgeSpeaker()
        self._cache: OrderedDict[tuple[str, str], bytes] = OrderedDict()

    async def speak(self, text: str, lang: str) -> bytes:
        """MP3 audio of ``text`` in ``lang``.

        Args:
            text: Answer text, already in ``lang``.
            lang: "en", "hi" or "kn".

        Returns:
            MP3 bytes.

        Raises:
            TtsUnavailable: Disabled, unknown language, timeout or service error.
        """
        voice = self.cfg.voices.get(lang)
        if not self.cfg.enabled or not voice:
            raise TtsUnavailable(f"no voice for {lang}")
        key = (voice, text)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        try:
            audio = await asyncio.wait_for(
                self.speaker.synthesize(text, voice), timeout=self.cfg.timeout_s
            )
        except Exception as e:  # network down, service change, timeout
            raise TtsUnavailable(str(e) or type(e).__name__) from e
        if not audio:
            raise TtsUnavailable("empty audio")
        self._cache[key] = audio
        if len(self._cache) > _CACHE_MAX:
            self._cache.popitem(last=False)
        return audio
