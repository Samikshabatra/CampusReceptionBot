import base64
from pathlib import Path

import numpy as np
import pytest

from reception.config import SpeechConfig
from reception.speech.stt import Transcriber, decode_pcm


def test_decode_pcm_roundtrip() -> None:
    audio = np.linspace(-0.5, 0.5, 1600, dtype=np.float32)
    assert np.allclose(decode_pcm(base64.b64encode(audio.tobytes()).decode()), audio)


def test_decode_pcm_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        decode_pcm("%%%not base64")


@pytest.mark.slow
def test_silence_transcribes_to_nothing() -> None:
    t = Transcriber(SpeechConfig())
    out = t.transcribe(np.zeros(16000, dtype=np.float32))
    assert out.text == "" and out.duration_s == pytest.approx(1.0, abs=0.01)


def test_too_short_audio_skipped_without_model() -> None:
    t = Transcriber(SpeechConfig())
    out = t.transcribe(np.zeros(100, dtype=np.float32))
    assert out.text == "" and not t._models


def test_prompt_matches_the_chosen_language() -> None:
    t = Transcriber(SpeechConfig())
    assert "CHRIST University" in (t.prompt_for("en") or "")
    assert "पुस्तकालय" in (t.prompt_for("hi") or "")
    assert "ಗ್ರಂಥಾಲಯ" in (t.prompt_for("kn") or "")
    assert t.prompt_for("fr") is None


def test_each_language_gets_its_own_model(tmp_path: Path) -> None:
    (tmp_path / "kn").mkdir()
    (tmp_path / "kn" / "model.bin").write_bytes(b"x")
    cfg = SpeechConfig(
        language_models={"kn": str(tmp_path / "kn"), "hi": str(tmp_path / "missing")}
    )
    t = Transcriber(cfg)
    assert t.model_for("en") == cfg.model
    assert t.model_for("kn") == str(tmp_path / "kn")
    assert t.model_for("hi") == cfg.fallback_model  # folder not downloaded
    assert not cfg.fallback_model.endswith(".en")
