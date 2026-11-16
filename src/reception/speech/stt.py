"""Speech-to-text with faster-whisper (local, CPU)."""

import base64
import binascii
from dataclasses import dataclass
from pathlib import Path
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
    is_noise: bool = False


def speech_seconds(audio: np.ndarray, cfg: SpeechConfig) -> float:
    """Seconds of real human voice in ``audio`` (Silero VAD, bundled with faster-whisper).

    Background hum, clatter and music score low, so they add little or nothing.
    """
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    stamps = get_speech_timestamps(audio, VadOptions(threshold=cfg.voice_threshold))
    return sum(s["end"] - s["start"] for s in stamps) / SAMPLE_RATE


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
        self._models: dict[str, Any] = {}

    def model_for(self, language: str) -> str:
        """Whisper model (name or local folder) used for ``language``."""
        if language == "en":
            return self.cfg.model
        local = self.cfg.language_models.get(language)
        if local and (Path(local) / "model.bin").exists():
            return local
        return self.cfg.fallback_model

    def _load(self, language: str) -> Any:
        name = self.model_for(language)
        if name not in self._models:
            from faster_whisper import WhisperModel

            self._models[name] = WhisperModel(
                name, device="cpu", compute_type=self.cfg.compute_type
            )
        return self._models[name]

    def prompt_for(self, language: str) -> str | None:
        """Vocabulary hint for Whisper in ``language`` (English names, or native script)."""
        if language == "en":
            return self.cfg.vocabulary
        return self.cfg.native_hints.get(language)

    def transcribe(self, audio: np.ndarray, language: str = "en") -> Transcript:
        """Transcribe one utterance.

        Args:
            audio: float32 mono samples at 16 kHz.
            language: Language the visitor chose ("en", "hi" or "kn").

        Returns:
            Text (empty when nothing was said) with mean log-probability.
        """
        duration = len(audio) / SAMPLE_RATE
        if len(audio) < _MIN_SAMPLES:
            return Transcript("", 0.0, duration)
        if speech_seconds(audio, self.cfg) < self.cfg.min_voice_s:
            return Transcript("", 0.0, duration, is_noise=True)  # noise only: never reaches Whisper
        lead_in = np.zeros(int(self.cfg.lead_in_s * SAMPLE_RATE), dtype=np.float32)
        segments, _ = self._load(language).transcribe(
            np.concatenate([lead_in, audio]),
            language=language,
            beam_size=self.cfg.beam_size,
            vad_filter=True,
            initial_prompt=self.prompt_for(language),
            condition_on_previous_text=False,
            temperature=0.0,
            max_new_tokens=self.cfg.max_new_tokens,
        )
        segs = [
            s
            for s in segments
            if s.no_speech_prob < self.cfg.no_speech_threshold
            and s.avg_logprob >= self.cfg.min_avg_logprob
        ]
        text = " ".join(s.text.strip() for s in segs).strip()
        logprob = float(np.mean([s.avg_logprob for s in segs])) if segs else 0.0
        return Transcript(text, logprob, duration)
