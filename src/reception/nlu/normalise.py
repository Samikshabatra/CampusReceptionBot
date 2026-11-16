"""Lower-case, strip punctuation and turn spoken numbers into digits."""

import re

_UNITS = {
    "zero": 0, "oh": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}  # fmt: skip
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}  # fmt: skip
_SCALES = {"hundred": 100, "thousand": 1000}
_NUMBER_WORDS = set(_UNITS) | set(_TENS) | set(_SCALES)


def _run_to_digits(words: list[str]) -> str:
    if any(w in _SCALES for w in words):
        total, current = 0, 0
        for w in words:
            if w in _UNITS:
                current += _UNITS[w]
            elif w in _TENS:
                current += _TENS[w]
            elif w == "hundred":
                current = max(current, 1) * 100
            elif w == "thousand":
                total += max(current, 1) * 1000
                current = 0
        return str(total + current)
    out: list[str] = []
    i = 0
    while i < len(words):
        w = words[i]
        if w in _TENS:
            nxt = words[i + 1] if i + 1 < len(words) else ""
            if nxt in _UNITS and 0 < _UNITS[nxt] < 10:
                out.append(str(_TENS[w] + _UNITS[nxt]))
                i += 2
                continue
            out.append(str(_TENS[w]))
        elif w in _UNITS:
            out.append(str(_UNITS[w]))
        i += 1
    return "".join(out)


def _numbers_to_digits(tokens: list[str]) -> list[str]:
    out: list[str] = []
    run: list[str] = []

    def flush() -> None:
        while run and run[-1] == "and":
            run.pop()
            trailing_and.append("and")
        if run:
            out.append(_run_to_digits([w for w in run if w != "and"]))
        run.clear()

    trailing_and: list[str] = []
    for tok in tokens:
        if tok in _NUMBER_WORDS or (tok == "and" and run and any(w in _SCALES for w in run)):
            if tok == "oh" and not run:
                flush()
                out.extend(trailing_and)
                trailing_and.clear()
                out.append(tok)
                continue
            run.append(tok)
        else:
            flush()
            out.extend(trailing_and)
            trailing_and.clear()
            out.append(tok)
    flush()
    out.extend(trailing_and)
    return out


def normalise(text: str, max_chars: int) -> str:
    """Normalise visitor text for matching.

    Args:
        text: Raw typed or transcribed text.
        max_chars: Truncation limit (applied first).

    Returns:
        Lower-case words and digits separated by single spaces.
    """
    t = text[:max_chars].lower()
    t = t.replace("&", " and ")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    tokens = t.split()
    return " ".join(_numbers_to_digits(tokens))
