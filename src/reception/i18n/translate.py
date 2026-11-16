"""Offline translation between English, Hindi and Kannada (NLLB-200 via CTranslate2)."""

import re
from pathlib import Path
from typing import Any, Literal, Protocol

from reception.config import I18nConfig

Lang = Literal["en", "hi", "kn"]
LANGS: tuple[Lang, ...] = ("en", "hi", "kn")
NLLB_CODES: dict[str, str] = {"en": "eng_Latn", "hi": "hin_Deva", "kn": "kan_Knda"}
_SENTENCE = re.compile(r"(?<=[.!?।])\s+")
_DIGITS = re.compile(r"\d+")
_CACHE_MAX = 2000


class Translator(Protocol):
    """Anything that translates text between the kiosk's languages."""

    def translate(self, text: str, src: Lang, tgt: Lang) -> str:
        """Return ``text`` translated from ``src`` to ``tgt``."""
        ...


def digits_kept(source: str, translated: str) -> bool:
    """True when every number in ``source`` still appears in ``translated``."""
    found = _DIGITS.findall(translated)
    return all(n in found for n in _DIGITS.findall(source))


class NllbTranslator:
    """NLLB-200 distilled 600M (int8) running locally on CPU; loads on first use."""

    def __init__(self, cfg: I18nConfig) -> None:
        """Remember settings; the model loads lazily."""
        self.cfg = cfg
        self._model: Any = None
        self._tok: Any = None
        self._cache: dict[tuple[str, str, str], str] = {}

    def _load(self) -> None:
        if self._model is None:
            import ctranslate2
            from tokenizers import Tokenizer

            d = Path(self.cfg.model_dir)
            self._tok = Tokenizer.from_file(str(d / "tokenizer.json"))
            self._model = ctranslate2.Translator(str(d), device="cpu", compute_type="int8")

    def _one(self, sentence: str, src: Lang, tgt: Lang) -> str:
        pieces = self._tok.encode(sentence, add_special_tokens=False).tokens
        out = self._model.translate_batch(
            [[NLLB_CODES[src], *pieces, "</s>"]],
            target_prefix=[[NLLB_CODES[tgt]]],
            beam_size=self.cfg.beam_size,
            max_decoding_length=self.cfg.max_tokens,
        )
        ids = [self._tok.token_to_id(t) for t in out[0].hypotheses[0][1:]]
        return str(self._tok.decode([i for i in ids if i is not None], skip_special_tokens=True))

    def translate(self, text: str, src: Lang, tgt: Lang) -> str:
        """Translate sentence by sentence (keeps long answers accurate), with a cache.

        Args:
            text: Text to translate.
            src: Source language.
            tgt: Target language.

        Returns:
            Translated text; unchanged when languages match or text is blank.
        """
        if src == tgt or not text.strip():
            return text
        key = (src, tgt, text)
        if key in self._cache:
            return self._cache[key]
        self._load()
        result = " ".join(self._one(s, src, tgt) for s in _SENTENCE.split(text.strip()) if s)
        if len(self._cache) >= _CACHE_MAX:
            self._cache.clear()
        self._cache[key] = result
        return result


class IdentityTranslator:
    """No-op translator (English-only deployments and tests)."""

    def translate(self, text: str, src: Lang, tgt: Lang) -> str:
        """Return the text unchanged."""
        return text
