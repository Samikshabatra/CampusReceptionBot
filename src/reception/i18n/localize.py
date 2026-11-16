"""Carry a conversation in Hindi or Kannada around the English answer engines.

Questions are translated to English before understanding; answers are translated
back before they are shown and spoken. Facts must never change in translation, so
any sentence whose numbers do not survive is kept in English.
"""

import re

from reception.i18n.translate import LANGS, Lang, Translator, digits_kept
from reception.types import Response

_SENTENCE = re.compile(r"(?<=[.!?।])\s+")
_ORDINAL = re.compile(r"\b(\d+)(?:st|nd|rd|th)\b")
# NLLB writes some Hindi floor numbers as words ("छठी मंजिल"); put the digit back.
_HINDI_ORDINALS = {
    "पहली": 1, "दूसरी": 2, "तीसरी": 3, "चौथी": 4, "पांचवीं": 5, "पाँचवीं": 5,
    "छठी": 6, "सातवीं": 7, "आठवीं": 8, "नौवीं": 9, "दसवीं": 10,
}  # fmt: skip
_HINDI_FLOOR = re.compile("(" + "|".join(_HINDI_ORDINALS) + r")(?=\s+मंजिल)")


def as_lang(code: object) -> Lang:
    """Return a supported language code, falling back to English."""
    return code if code in LANGS else "en"  # type: ignore[return-value]


def to_english(text: str, lang: Lang, tr: Translator) -> str:
    """Translate a visitor's question to English (typed English passes through).

    Args:
        text: What the visitor typed or said.
        lang: The conversation language.
        tr: Translator.

    Returns:
        English text for the understanding pipeline.
    """
    if lang == "en" or text.isascii():
        return text
    return tr.translate(text, lang, "en")


def localize_text(text: str, lang: Lang, tr: Translator) -> str:
    """Translate an English answer sentence by sentence, keeping every number.

    "6th floor" is written "floor 6" first so the digit survives translation; a
    sentence whose numbers still go missing stays in English.

    Args:
        text: English text.
        lang: Target language.
        tr: Translator.

    Returns:
        Translated text (unchanged for English or blank text).
    """
    if lang == "en" or not text.strip():
        return text
    out = []
    for sentence in _SENTENCE.split(text.strip()):
        if not sentence:
            continue
        plain = _ORDINAL.sub(r"\1", sentence)
        translated = tr.translate(plain, "en", lang)
        if lang == "hi":
            translated = _HINDI_FLOOR.sub(lambda m: f"{_HINDI_ORDINALS[m.group(1)]}वीं", translated)
        out.append(translated if translated.strip() and digits_kept(plain, translated) else sentence)
    return " ".join(out)


def localize_response(r: Response, lang: Lang, tr: Translator) -> Response:
    """Return a copy of ``r`` whose spoken and shown words are in ``lang``.

    Translated: the speech, route steps, and labels for tap options (the options
    themselves stay English because tapping one sends it back as a question).
    Names, links, fees tables and other data stay as published.

    Args:
        r: English response from the assistant.
        lang: Conversation language.
        tr: Translator.

    Returns:
        A localized copy; ``card.data["lang"]`` records the language.
    """
    if lang == "en":
        return r
    out = r.model_copy(deep=True)
    out.speech = localize_text(r.speech, lang, tr)
    data = out.card.data
    if isinstance(data.get("steps"), list):
        data["steps"] = [localize_text(str(s), lang, tr) for s in data["steps"]]
    if isinstance(data.get("options"), list):
        data["option_labels"] = [localize_text(str(o), lang, tr) for o in data["options"]]
    data["lang"] = lang
    return out
