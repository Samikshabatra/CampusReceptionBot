from pathlib import Path

import numpy as np

from reception.config import SpeechConfig
from reception.eval.run import read_wav
from reception.speech.stt import Transcriber, speech_seconds

SPEECH = read_wav(Path("tests/fixtures/speech_library.wav"))  # "how do I get to the library"
RNG = np.random.default_rng(0)


def noise(seconds: float, level: float) -> np.ndarray:
    return (RNG.normal(0, level, int(16000 * seconds))).astype(np.float32)


def test_real_speech_has_voice() -> None:
    assert speech_seconds(SPEECH, SpeechConfig()) > 0.5


def test_background_noise_has_no_voice() -> None:
    assert speech_seconds(noise(2.0, 0.05), SpeechConfig()) < 0.3


def test_clatter_has_no_voice() -> None:
    clatter = np.zeros(32000, dtype=np.float32)
    for start in range(0, 32000, 4000):  # short loud bangs
        clatter[start : start + 300] = RNG.uniform(-0.8, 0.8, 300)
    assert speech_seconds(clatter, SpeechConfig()) < 0.3


def test_noise_rejected_before_loading_whisper() -> None:
    t = Transcriber(SpeechConfig())
    out = t.transcribe(noise(2.0, 0.05))
    assert out.text == "" and out.is_noise and t._model is None
