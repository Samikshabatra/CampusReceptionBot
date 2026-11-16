import asyncio

import pytest

from reception.config import TtsConfig
from reception.speech.tts import TtsUnavailable, VoiceService


class FakeSpeaker:
    def __init__(self, audio: bytes = b"ID3fake", delay: float = 0.0, fail: bool = False) -> None:
        self.audio, self.delay, self.fail = audio, delay, fail
        self.calls: list[tuple[str, str]] = []

    async def synthesize(self, text: str, voice: str) -> bytes:
        self.calls.append((text, voice))
        await asyncio.sleep(self.delay)
        if self.fail:
            raise OSError("offline")
        return self.audio


def test_uses_the_voice_for_the_language() -> None:
    sp = FakeSpeaker()
    assert asyncio.run(VoiceService(TtsConfig(), sp).speak("नमस्ते", "hi")) == b"ID3fake"
    assert sp.calls == [("नमस्ते", "hi-IN-SwaraNeural")]


def test_repeated_text_is_cached() -> None:
    sp = FakeSpeaker()
    svc = VoiceService(TtsConfig(), sp)

    async def twice() -> None:
        await svc.speak("ನಮಸ್ಕಾರ", "kn")
        await svc.speak("ನಮಸ್ಕಾರ", "kn")

    asyncio.run(twice())
    assert len(sp.calls) == 1


@pytest.mark.parametrize(
    "cfg,speaker,lang",
    [
        (TtsConfig(enabled=False), FakeSpeaker(), "hi"),
        (TtsConfig(), FakeSpeaker(), "fr"),
        (TtsConfig(), FakeSpeaker(fail=True), "hi"),
        (TtsConfig(), FakeSpeaker(audio=b""), "hi"),
        (TtsConfig(timeout_s=0.01), FakeSpeaker(delay=0.5), "hi"),
    ],
)
def test_failures_raise_unavailable(cfg: TtsConfig, speaker: FakeSpeaker, lang: str) -> None:
    with pytest.raises(TtsUnavailable):
        asyncio.run(VoiceService(cfg, speaker).speak("text", lang))
