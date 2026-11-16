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


def _voice_stamps(audio: np.ndarray, cfg: SpeechConfig) -> list[dict[str, int]]:
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    return list(get_speech_timestamps(audio, VadOptions(threshold=cfg.voice_threshold)))


def speech_seconds(audio: np.ndarray, cfg: SpeechConfig) -> float:
    """Seconds of real human voice in ``audio`` (Silero VAD, bundled with faster-whisper).

    Background hum, clatter and music score low, so they add little or nothing.
    """
    return sum(s["end"] - s["start"] for s in _voice_stamps(audio, cfg)) / SAMPLE_RATE


def crop_to_voice(audio: np.ndarray, stamps: list[dict[str, int]], cfg: SpeechConfig) -> np.ndarray:
    """Keep only the stretch with voice, plus a short margin, behind a silent lead-in.

    Whisper tends to invent words in long trailing silence; the lead-in keeps the
    first syllable from being clipped.
    """
    margin = int(cfg.voice_margin_s * SAMPLE_RATE)
    start = max(0, stamps[0]["start"] - margin)
    end = min(len(audio), stamps[-1]["end"] + margin)
    lead_in = np.zeros(int(cfg.lead_in_s * SAMPLE_RATE), dtype=np.float32)
    return np.concatenate([lead_in, audio[start:end]])


def drop_repeats(text: str) -> str:
    """Collapse a transcript that is the same phrase said twice ("X X" -> "X")."""
    words = text.split()
    n = len(words)
    if n >= 2 and n % 2 == 0 and words[: n // 2] == words[n // 2 :]:
        return " ".join(words[: n // 2])
    return text


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
        stamps = _voice_stamps(audio, self.cfg)
        voiced = sum(s["end"] - s["start"] for s in stamps) / SAMPLE_RATE
        if voiced < self.cfg.min_voice_s:
            return Transcript("", 0.0, duration, is_noise=True)  # noise only: never reaches Whisper
        segments, _ = self._load(language).transcribe(
            crop_to_voice(audio, stamps, self.cfg),
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
        text = drop_repeats(" ".join(s.text.strip() for s in segs).strip())
        logprob = float(np.mean([s.avg_logprob for s in segs])) if segs else 0.0
        return Transcript(text, logprob, duration)
