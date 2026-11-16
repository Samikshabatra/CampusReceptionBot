"""Speech-to-text with faster-whisper (local, CPU)."""

import base64
import binascii
from dataclasses import dataclass
from typing import Any

import numpy as np

from reception.config import SpeechConfig

SAMPLE_RATE = 16_000
_MIN_SAMPLES = SAMPLE_RATE // 4


@dataclass(frozen=True)
class Transcript:
    """What the visitor said."""

    text: str
    avg_logprob: float
    duration_s: float


def decode_pcm(b64: str) -> np.ndarray:
    """Base64 little-endian float32 mono 16 kHz -> array.

    Raises:
        ValueError: Not valid base64 / float32 data.
    """
    try:
        raw = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError) as e:
        raise ValueError("audio is not valid base64") from e
    if len(raw) % 4:
        raise ValueError("audio is not float32")
    return np.frombuffer(raw, dtype="<f4").astype(np.float32)


class Transcriber:
    """Lazy-loading Whisper transcriber."""

    def __init__(self, cfg: SpeechConfig) -> None:
        """Remember settings; the model loads on first real audio."""
        self.cfg = cfg
        self._model: Any = None

    def _load(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.cfg.model, device="cpu", compute_type=self.cfg.compute_type
            )
        return self._model

    def transcribe(self, audio: np.ndarray) -> Transcript:
        """Transcribe one utterance.

        Args:
            audio: float32 mono samples at 16 kHz.

        Returns:
            Text (empty when nothing was said) with mean log-probability.
        """
        duration = len(audio) / SAMPLE_RATE
        if len(audio) < _MIN_SAMPLES:
            return Transcript("", 0.0, duration)
        segments, _ = self._load().transcribe(
            audio,
            language="en",
            beam_size=self.cfg.beam_size,
            vad_filter=True,
            initial_prompt=self.cfg.vocabulary,
            condition_on_previous_text=False,
        )
        segs = list(segments)
        text = " ".join(s.text.strip() for s in segs).strip()
        logprob = float(np.mean([s.avg_logprob for s in segs])) if segs else 0.0
        return Transcript(text, logprob, duration)
