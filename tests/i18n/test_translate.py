from pathlib import Path

import pytest

from reception.config import I18nConfig
from reception.i18n.translate import NllbTranslator, digits_kept

MODEL = Path(I18nConfig().model_dir)
needs_model = pytest.mark.skipif(not (MODEL / "model.bin").exists(), reason="NLLB model not downloaded")


@pytest.fixture(scope="module")
def tr() -> NllbTranslator:
    return NllbTranslator(I18nConfig())


def test_digits_kept() -> None:
    assert digits_kept("Room 812 on the 8th floor", "कमरा 812 8वीं मंजिल")
    assert not digits_kept("Room 812", "कमरा 81")


@needs_model
def test_hindi_question_to_english(tr: NllbTranslator) -> None:
    assert "library" in tr.translate("पुस्तकालय कहाँ है?", "hi", "en").lower()


@needs_model
def test_kannada_question_to_english(tr: NllbTranslator) -> None:
    assert "library" in tr.translate("ಗ್ರಂಥಾಲಯ ಎಲ್ಲಿದೆ?", "kn", "en").lower()


@needs_model
def test_english_answer_to_hindi_keeps_numbers(tr: NllbTranslator) -> None:
    out = tr.translate("Room 812 is on this floor. It opens at 8 am.", "en", "hi")
    assert any("ऀ" <= ch <= "ॿ" for ch in out) and "812" in out and "8" in out


@needs_model
def test_english_answer_to_kannada(tr: NllbTranslator) -> None:
    out = tr.translate("The Health Centre is in the Basement.", "en", "kn")
    assert any("ಀ" <= ch <= "೿" for ch in out)


def test_same_language_and_empty_are_untouched(tr: NllbTranslator) -> None:
    assert tr.translate("Where is room 812?", "en", "en") == "Where is room 812?"
    assert tr.translate("  ", "en", "hi") == "  "


@needs_model
def test_results_are_cached(tr: NllbTranslator) -> None:
    tr.translate("Good morning!", "en", "hi")
    size = len(tr._cache)
    tr.translate("Good morning!", "en", "hi")
    assert len(tr._cache) == size
