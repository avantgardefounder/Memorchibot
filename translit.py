"""Узбекский: латиница → кириллица. Используется для интерфейса и отчётов на «Ўзбекча (кирилл)»."""
import re

_APOS = "'ʻʼ’‘`"
_MULTI = [("o'", "ў"), ("g'", "ғ"), ("sh", "ш"), ("ch", "ч"), ("yo", "ё"), ("yu", "ю"), ("ya", "я"), ("ye", "е")]
_SINGLE = {
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "ҳ", "i": "и", "j": "ж", "k": "к",
    "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "q": "қ", "r": "р", "s": "с", "t": "т", "u": "у",
    "v": "в", "x": "х", "y": "й", "z": "з", "c": "с", "w": "в",
}
# Слова, которые не трогаем: команды, упоминания, хэштеги, аббревиатуры, слова с цифрами, плейсхолдеры
_SKIP = re.compile(r"^(/|@|#|\{|https?:)|^[A-Z]{2,}$|\d")
_WORD = re.compile(r"\{[^}]*\}|[/@#]?[A-Za-z" + _APOS + r"]+(?:[\-.][A-Za-z" + _APOS + r"]+)*|\S")


def _word(w):
    if _SKIP.search(w):
        return w
    src = w
    for a in _APOS[1:]:
        src = src.replace(a, "'")
    low = src.lower()
    out, i = [], 0
    while i < len(low):
        ch = low[i]
        if i == 0 and ch == "e":
            out.append("э")
            i += 1
            continue
        pair = low[i:i + 2]
        hit = next((c for p, c in _MULTI if pair == p), None)
        if hit:
            # «obyekt» → «объект»: йотированная гласная после согласной пишется через ъ
            if pair[0] == "y" and i > 0 and low[i - 1] in "bcdfghjklmnpqrstvxz":
                out.append("ъ")
            out.append(hit)
            i += 2
            continue
        if ch == "'":
            out.append("ъ")
        else:
            out.append(_SINGLE.get(ch, ch))
        i += 1
    res = "".join(out)
    letters = [c for c in src if c.isalpha()]
    if letters and all(c.isupper() for c in letters) and len(letters) > 1:
        return res.upper()
    if src[:1].isupper():
        return res[:1].upper() + res[1:]
    return res


def to_cyr(text):
    """Транслитерация строки (или вложенной структуры) с узбекской латиницы на кириллицу."""
    if isinstance(text, dict):
        return {k: to_cyr(v) for k, v in text.items()}
    if isinstance(text, (list, tuple)):
        return type(text)(to_cyr(v) for v in text)
    if not isinstance(text, str):
        return text
    return _WORD.sub(lambda m: _word(m.group(0)) if m.group(0)[:1].isalpha() else m.group(0), text)
