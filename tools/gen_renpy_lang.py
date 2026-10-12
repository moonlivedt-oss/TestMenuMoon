#!/usr/bin/env python3
"""Собрать часть меню Ren'Py engines/renpy/engine/13_lang.rpy из словаря engines/renpy/lang_en.json.

    python tools/gen_renpy_lang.py           собрать 13_lang.rpy
    python tools/gen_renpy_lang.py --check   строки меню без перевода (их надо дописать в JSON)

Словарь — ключ: строка меню ровно как в коде (с %s / %d / [имя] и [[ ), значение: перевод.
Правится JSON, .rpy — пересобирается этой командой (тест сверяет, что он свежий).
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "engines", "renpy", "lang_en.json")
OUT = os.path.join(ROOT, "engines", "renpy", "engine", "13_lang.rpy")

HEAD = """
# ==================== язык меню: русский / English (Настройки) ====================
# Файл собран tools/gen_renpy_lang.py из engines/renpy/lang_en.json — правь JSON, не этот файл.
# Перевод — config.replace_text: заменяются только строки, целиком совпадающие со строкой меню
# (или её шаблоном с подстановками), и только когда выбран English. Язык самой игры не меняется.
init -3 python:
    import re as _tml_re

    TM_EN = {
"""

TAIL = r"""    }

    _TML_CYR = _tml_re.compile(u"[Ѐ-ӿ]")
    _TML_PH = _tml_re.compile(r"(%[sdr]|\[[^\[\]]+\])")

    def _tml_build():
        exact, pats = {}, []
        for ru, en in TM_EN.items():
            if not _TML_PH.search(ru.replace(u"[[", u"")):
                exact[ru.replace(u"[[", u"[").replace(u"%%", u"%")] = en.replace(u"[[", u"[").replace(u"%%", u"%")
                continue
            ru_parts = _TML_PH.split(ru.replace(u"[[", u"\x00"))
            en_parts = _TML_PH.split(en.replace(u"[[", u"\x00"))
            rx = u"".join(u"(.+?)" if i % 2 else _tml_re.escape(p.replace(u"\x00", u"[").replace(u"%%", u"%"))
                          for i, p in enumerate(ru_parts))
            pats.append((_tml_re.compile(u"^" + rx + u"$", _tml_re.S),
                         [p.replace(u"\x00", u"[").replace(u"%%", u"%") for p in en_parts]))
        return exact, pats

    _TML_EXACT, _TML_PATS = _tml_build()

    def tm_lang():
        try:
            return persistent.tm_lang or "ru"
        except Exception:
            return "ru"

    def tm_set_lang(lang):
        persistent.tm_lang = lang
        renpy.session["tm_auto"] = None          # понятные имена и группы — на новом языке
        renpy.session["tm_nice"] = None
        renpy.restart_interaction()

    def _tml_translate(s):
        r = _TML_EXACT.get(s)
        if r is not None:
            return r
        if not _TML_CYR.search(s):
            return s
        for rx, parts in _TML_PATS:
            m = rx.match(s)
            if m:
                g = m.groups()
                return u"".join(g[i // 2] if i % 2 else p for i, p in enumerate(parts))
        return s

    def tm_tr(s):
        # кусок составной строки на языке меню: tm_tr(u"меняется: ") + ...
        if tm_lang() != "en":
            return s
        try:
            return _tml_translate(s)
        except Exception:
            return s

    def _tml_replace_text(s):
        prev = _tml_state[0]
        if prev is not None:
            s = prev(s)
        if tm_lang() != "en" or not s:
            return s
        try:
            return _tml_translate(s)
        except Exception:
            return s

    _tml_state = [None]

    def _tml_register():
        # свой фильтр поверх фильтра игры (если он был), один раз
        try:
            cur = config.replace_text
        except Exception:
            return
        if cur is _tml_replace_text:
            return
        _tml_state[0] = cur
        config.replace_text = _tml_replace_text

init 999 python:
    _tml_register()
"""


def _tokens(text):
    """[(начало, конец, значение | None)] строковых литералов .rpy (учёт '…', "…", тройных, #)."""
    import ast

    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "#":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c in "\"'":
            pre = i - 1
            while pre >= 0 and text[pre] in "uUrRbB":
                pre -= 1
            prefix = text[pre + 1 : i]
            if pre >= 0 and (text[pre].isalnum() or text[pre] == "_"):
                prefix = ""
            q = text[i : i + 3] if text[i : i + 3] in ('"""', "'''") else c
            j = i + len(q)
            while j < n and not text.startswith(q, j):
                j += 2 if text[j] == "\\" else 1
            j += len(q)
            try:
                val = ast.literal_eval(("r" if "r" in prefix.lower() else "") + text[i:j])
            except Exception:
                val = None
            out.append((i - len(prefix), j, val))
            i = j
            continue
        i += 1
    return out


def menu_strings():
    """Русские строки меню (соседние литералы склеены, как в Python), без слов словаря имён."""
    import glob
    import re
    import sys

    sys.path.insert(0, ROOT)
    from tmkit import naming

    words, generic = naming.vocabulary()
    vocab = set(words.values()) | set(naming._cache["inflect"]) | set(naming._cache["stems"])
    vocab |= set(generic) | set(naming._cache["stat_words"])
    cyr = re.compile("[\u0400-\u04ff]")
    out, seen = [], set()
    files = sorted(glob.glob(os.path.join(ROOT, "engines", "renpy", "engine", "*.rpy")))
    files.append(os.path.join(ROOT, "engines", "renpy", "zzz_testmenu_translate.rpy"))  # модуль перевода реплик
    for p in files:
        if os.path.basename(p) == os.path.basename(OUT):
            continue
        text = open(p, encoding="utf-8").read()
        toks = _tokens(text)
        k = 0
        while k < len(toks):
            _s, e, v = toks[k]
            parts = [v]
            while k + 1 < len(toks) and text[e : toks[k + 1][0]].strip() == "":
                k += 1
                e = toks[k][1]
                parts.append(toks[k][2])
            k += 1
            if any(not isinstance(x, str) for x in parts):
                continue
            val = "".join(parts)
            in_vocab = val in vocab and os.path.basename(p) == "04_naming.rpy"
            if cyr.search(val) and not in_vocab and val not in seen:
                seen.add(val)
                out.append(val)
    return out


def missing():
    with open(SRC, encoding="utf-8") as f:
        d = json.load(f)
    return [s for s in menu_strings() if s not in d]


def py_str(s):
    return "u" + json.dumps(s, ensure_ascii=False)


def main():
    with open(SRC, encoding="utf-8") as f:
        d = json.load(f)
    rows = "".join("        %s: %s,\n" % (py_str(k), py_str(v)) for k, v in d.items())
    text = HEAD + rows + TAIL
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"[OK] {OUT}: строк {len(d)}")


if __name__ == "__main__":
    import sys

    if "--check" in sys.argv:
        m = missing()
        for s in m:
            print(json.dumps(s, ensure_ascii=False))
        print(f"без перевода: {len(m)}")
        sys.exit(1 if m else 0)
    main()
