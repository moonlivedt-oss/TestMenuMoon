"""Понятные имена переменных для студии — те же правила, что у движка в игре.

Словарь перевода (TM_WORDS) и служебные слова (TM_GENERIC) берутся прямо из
engines/renpy/engine/04_naming.rpy: источник один, движок и студия не расходятся.
Персонажи — из `define x = Character("Имя")` в исходниках игры; свои имена,
заданные в игре щелчком по имени, — из game/tm_names.json.

    nice("alice_love", "alice_love", chars={"alice": "Alice"}) -> ("Alice | Симпатия", True)
"""

import ast
import glob
import json
import os
import re

from tmkit.paths import ENGINE_SRC, read_source, source_stamp

_CHAR_RE = re.compile(
    r'^\s*define\s+(\w+)\s*=\s*(?:\w+\.)*\w*Character\(\s*(?:_\(\s*)?[urbURB]?(["\'])([^"\'\[{]+)\2'
)
_IDENT = re.compile(r"^[A-Za-z_][\w.\[\]\"']*$")
_cache = {}


def _literal(text, start, end):
    """Литерал Python из движка: от последнего символа start до end включительно."""
    i = text.index(start) + len(start) - 1
    j = text.index(end, i) + len(end)
    return ast.literal_eval(text[i:j])


def vocabulary(engine_src=ENGINE_SRC):
    """(слова {en: ru}, служебные frozenset) из движка; кэш по mtime частей."""
    key = source_stamp(engine_src)
    if key is None:
        raise FileNotFoundError(engine_src)
    if _cache.get("vocab_key") != key:
        text = read_source(engine_src).replace("\r\n", "\n")
        words = _literal(text, "TM_WORDS = {", "\n    }")
        generic = _literal(text, "TM_GENERIC = frozenset((", ")")
        _cache["inflect"] = _literal(text, "TM_INFLECT = (", ")")
        _cache["stems"] = frozenset(_literal(text, "TM_STEMS = frozenset((", ")"))
        _cache["stat_words"] = tuple(_literal(text, "TM_STAT_WORDS = (", ")"))
        _cache["vocab_key"] = key
        _cache["vocab"] = (words, frozenset(generic))
    return _cache["vocab"]


def words_json():
    """Словарь имён для меню Godot и Unity (tm_words.json) — тот же, что у движка Ren'Py."""
    words, generic = vocabulary()
    return json.dumps(
        {
            "words": words,
            "generic": sorted(generic),
            "inflect": list(_cache["inflect"]),
            "stems": sorted(_cache["stems"]),
            "stat_words": list(_cache["stat_words"]),
        },
        ensure_ascii=False,
        indent=0,
        sort_keys=True,
    )


def tokens(text):
    """«girls[Anna].loveLevel» -> [("girls", False), ("anna", True), ("love", False), ("level", False)]."""
    out = []
    for part in re.split(r"(\[[^\]]*\])", text or ""):
        if not part:
            continue
        is_key = part.startswith("[")
        s = part.strip("[]").strip("\"'")
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
        for t in re.split(r"[^0-9A-Za-zÀ-￿]+", s):
            if t and (is_key or not t.isdigit()):
                out.append((t.lower(), is_key))
    return out


def word(tok, words):
    """Перевод токена: точное слово, иначе самое длинное слово-префикс (>= 4 букв), если
    остаток — окончание (TM_INFLECT) или ключ — основа (TM_STEMS); как tm_word в движке."""
    if tok in words:
        return words[tok]
    vocabulary()
    inflect, stems = _cache["inflect"], _cache["stems"]
    best = max(
        (k for k in words if len(k) >= 4 and tok.startswith(k)
         and (k in stems or tok[len(k):] in inflect)),
        key=len,
        default=None,
    )
    return words[best] if best else None


def characters(*dirs):
    """{ключ в нижнем регистре: имя} из define ... = Character("Имя") в .rpy папок."""
    out = {}
    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        for f in glob.glob(os.path.join(glob.escape(d), "**", "*.rpy"), recursive=True):
            if os.path.basename(f).startswith("zzz_testmenu_") or "/tl/" in f.replace(
                "\\", "/"
            ):
                continue
            try:
                with open(f, encoding="utf-8", errors="ignore") as fh:
                    for line in fh:
                        m = _CHAR_RE.match(line)
                        if not m:
                            continue
                        var, name = m.group(1), m.group(3).strip()
                        for k in (var.lower(), name.lower(), name.split()[0].lower()):
                            if len(k) >= 3:
                                out.setdefault(k, name)
            except OSError:
                continue
    return out


def user_names(game_dir):
    """Свои имена из game/tm_names.json ({путь: имя}); нет файла — {}."""
    try:
        with open(os.path.join(game_dir, "tm_names.json"), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _parts(label, path, chars, names, engine_src):
    """(подпись, уровень): "full" — всё понятно, "partial" — часть слов не переведена,
    "none" — ничего не переведено (подпись лишь переформатирует имя)."""
    names = names or {}
    if path in names:
        return names[path], "full"
    if label and label != path and not _IDENT.match(label):
        return label, "full"  # уже человеческая подпись
    words, generic = vocabulary(engine_src)
    chars = chars or {}
    toks = tokens(label or path)
    who, who_at = None, -1
    for i, (t, _k) in enumerate(toks):
        if t in chars:
            who, who_at = chars[t], i
            break
    if who_at >= 0:
        toks = (
            toks[who_at + 1 :]
            if toks[who_at][1]
            else toks[:who_at] + toks[who_at + 1 :]
        )
    base, keys, hit, miss = [], [], 0, 0
    for t, is_key in toks:
        if t in generic and not is_key:
            continue
        w = word(t, words)
        if w:
            hit += 1
        elif not is_key:
            miss += 1  # ключ словаря (inv["apple"]) — название предмета, переводить не нужно
        (keys if is_key else base).append(w or t)
    title, kt = " ".join(base), " ".join(keys)
    title = f"{title}: {kt}" if (title and kt) else (title or kt) or path
    title = title[:1].upper() + title[1:]
    text = f"{who} | {title}" if who else title
    known = hit + (1 if who else 0)
    return text, ("none" if not known else "partial" if miss else "full")


def nice(label, path, chars=None, names=None, engine_src=ENGINE_SRC):
    """(подпись, уверенно?) — как tm_nice в движке (без живых объектов и реплик)."""
    text, level = _parts(label, path, chars, names, engine_src)
    return text, level != "none"


def label_for(label, path, chars=None, names=None):
    """Подпись для строки кандидатов: человеческая метка как есть, иначе — по пути
    (у «Girl.love -> anna.love» путь говорит больше, чем класс)."""
    if label and label != path and not _IDENT.match(label):
        return label
    return nice(path, path, chars, names)[0]


ANNOT = "  // "  # отделяет подсказку-имя в просмотре кандидатов (parse_candidates её отрезает)


def annotate(text, parse, chars=None, names=None):
    """Дописать к строкам-кандидатам понятное имя: «alice_love = 3  // Alice | Симпатия».
    Частичный перевод помечается «(догадка)»; если ничего не понятно — строка как есть."""
    out = []
    for line in text.splitlines():
        pairs = (
            parse(line)
            if line.strip() and not line.lstrip().startswith(("#", "["))
            else []
        )
        if len(pairs) == 1:
            path = pairs[0][1]
            n, level = _parts(path, path, chars, names, ENGINE_SRC)
            if level != "none":
                line = f"{line}{ANNOT}{n}{' (догадка)' if level == 'partial' else ''}"
        out.append(line)
    return "\n".join(out)
