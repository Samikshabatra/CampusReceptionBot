import base64

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
    assert out.text == "" and t._model is None
