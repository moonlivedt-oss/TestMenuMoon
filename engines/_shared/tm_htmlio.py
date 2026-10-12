"""Чтение/запись HTML и JS игр в их родной кодировке (общее для web-инжекторов).

Раньше файлы читались строго как UTF-8: HTML в cp1251/Shift_JIS/latin-1 ронял внедрение
UnicodeDecodeError. Теперь кодировка определяется (BOM -> валидный UTF-8 -> <meta charset>
-> latin-1 как обратимый запасной вариант), файл пишется в той же кодировке с теми же
концами строк, а внедряемый скрипт для не-UTF файлов переводится в чистый ASCII
(\\uXXXX-экранирование) — кириллица меню не ломается ни в какой кодировке страницы.
"""

import codecs
import re

_META = re.compile(rb"<meta[^>]+charset\s*=\s*[\"']?\s*([A-Za-z0-9_.:-]+)", re.I)


def detect_encoding(raw):
    """Кодировка байтов HTML/JS. Всегда возвращает имя, которым raw декодируется без ошибок."""
    if raw.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return "utf-16"
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    m = _META.search(raw[:8192])
    if m:
        name = m.group(1).decode("ascii", "replace")
        try:
            info = codecs.lookup(name)
        except LookupError:
            info = None
        if info is not None and not info.name.startswith("utf"):
            try:
                raw.decode(info.name)
                return info.name
            except UnicodeDecodeError:
                pass
    return "latin-1"  # байт в байт обратимо: чужой текст страницы не портится


def is_unicode(enc):
    return codecs.lookup(enc).name.startswith("utf")


def read(path):
    """(текст, кодировка). Концы строк не трогаются."""
    with open(path, "rb") as f:
        raw = f.read()
    enc = detect_encoding(raw)
    return raw.decode(enc), enc


def write(path, text, enc):
    with open(path, "wb") as f:
        f.write(text.encode(enc))


def ascii_js(js):
    """JS только из ASCII: не-ASCII символы -> \\uXXXX (суррогатные пары для > U+FFFF).
    В строках JS это тот же символ, в комментариях — безвредный текст."""
    out = []
    for ch in js:
        o = ord(ch)
        if o < 128:
            out.append(ch)
        elif o <= 0xFFFF:
            out.append("\\u%04x" % o)
        else:
            o -= 0x10000
            out.append("\\u%04x\\u%04x" % (0xD800 + (o >> 10), 0xDC00 + (o & 0x3FF)))
    return "".join(out)


def js_for(enc, js):
    """Скрипт, пригодный для вставки в страницу с кодировкой enc."""
    return js if is_unicode(enc) else ascii_js(js)
