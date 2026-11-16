from reception.i18n.localize import as_lang, localize_response, localize_text, to_english
from reception.i18n.translate import Lang
from reception.types import Card, Response


class FakeTranslator:
    """Tags text with the target language; can drop or wordify digits on purpose."""

    def __init__(self, table: dict[str, str] | None = None) -> None:
        self.table = table or {}
        self.calls: list[tuple[str, str, str]] = []

    def translate(self, text: str, src: Lang, tgt: Lang) -> str:
        self.calls.append((text, src, tgt))
        return self.table.get(text, f"[{tgt}] {text}")


def test_as_lang_falls_back_to_english() -> None:
    assert as_lang("hi") == "hi" and as_lang("kn") == "kn"
    assert as_lang("fr") == "en" and as_lang(None) == "en"


def test_to_english_skips_english_and_ascii() -> None:
    tr = FakeTranslator({"पुस्तकालय कहाँ है?": "Where is the library?"})
    assert to_english("पुस्तकालय कहाँ है?", "hi", tr) == "Where is the library?"
    assert to_english("Where is room 812?", "hi", tr) == "Where is room 812?"
    assert to_english("anything", "en", tr) == "anything"
    assert len(tr.calls) == 1


def test_localize_text_keeps_english_when_numbers_are_lost() -> None:
    tr = FakeTranslator({"It opens at 8 am.": "यह सुबह खुलता है।"})
    out = localize_text("It opens at 8 am. Welcome!", "hi", tr)
    assert out == "It opens at 8 am. [hi] Welcome!"


def test_localize_text_writes_ordinals_as_digits() -> None:
    tr = FakeTranslator()
    assert localize_text("Go to the 6th floor.", "kn", tr) == "[kn] Go to the 6 floor."


def test_hindi_floor_words_become_digits() -> None:
    tr = FakeTranslator({"The Library is on the 6 floor.": "पुस्तकालय छठी मंजिल पर है।"})
    assert (
        localize_text("The Library is on the 6th floor.", "hi", tr) == "पुस्तकालय 6वीं मंजिल पर है।"
    )


def test_english_response_is_returned_untouched() -> None:
    r = Response(speech="Hi", card=Card(kind="text"), intent="greeting", confidence=1.0)
    assert localize_response(r, "en", FakeTranslator()) is r


def test_localize_response_translates_speech_steps_and_option_labels() -> None:
    r = Response(
        speech="The Library is on the 6th floor.",
        card=Card(
            kind="map", data={"steps": ["Walk to the nearest lift."], "options": ["Timings"]}
        ),
        intent="navigate",
        confidence=0.9,
    )
    out = localize_response(r, "kn", FakeTranslator())
    assert out.speech == "[kn] The Library is on the 6 floor."
    assert out.card.data["steps"] == ["[kn] Walk to the nearest lift."]
    assert out.card.data["options"] == ["Timings"]  # tapping still sends English
    assert out.card.data["option_labels"] == ["[kn] Timings"]
    assert out.card.data["lang"] == "kn"
    assert r.speech == "The Library is on the 6th floor."  # original untouched
