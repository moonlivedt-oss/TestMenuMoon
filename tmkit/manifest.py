#!/usr/bin/env python3
"""Чтение/запись данных манифеста (tmkit/games_data.py) + правка состава игр.

games_data.py — чистые данные (G, ACCENT, GAMES); правится студией или руками.
games.py — логика (ROOTS, автопоиск лаунчера) поверх этих данных.
Здесь — единственное место, которое ПЕРЕЗАПИСЫВАЕТ games_data.py, чтобы формат
был детерминированным и не терял структуру.
"""

import os, re, copy, shutil, importlib

from tmkit.paths import GAMES_DATA_PATH

HEADER = '''#!/usr/bin/env python3
"""ДАННЫЕ манифеста тест-меню (правится GUI-студией studio.py или руками).
Логика (ROOTS / автопоиск лаунчера) — в games.py, который импортирует отсюда."""

G = {G!r}
ACCENT = {ACCENT!r}

GAMES = {{
'''


def trim_row(row):
    """Строка стата/действия -> кортеж строк без хвостовых пустых полей сверх двух.
    ("Метка", "путь") | ("Метка", "путь", "min", "max"); ("Метка", "путь", "", "4") —
    только max. Пустые min и max -> просто пара (старый формат не меняется)."""
    row = tuple("" if x is None else str(x) for x in row)
    row = (row + ("", ""))[:max(2, len(row))]
    if len(row) > 2 and not any(row[2:]):
        return row[:2]
    if len(row) == 3:
        row = row + ("",)
    return row[:4]


def _rows(pairs):
    out = []
    for row in pairs:
        out.append("        (%s)," % ", ".join(repr(x) for x in trim_row(row)))
    return "\n".join(out)


def dumps(games, G, ACCENT):
    """Сериализовать GAMES в текст games_data.py (детерминированно)."""
    parts = [HEADER.format(G=G, ACCENT=ACCENT)]
    for i in sorted(games):
        g = games[i]
        parts.append("%d: {" % i)
        parts.append("    %r: %r," % ("title", g.get("title", "TEST MENU")))
        parts.append("    %r: %r," % ("root", g.get("root", "")))
        parts.append("    %r: %r," % ("status", g.get("status", "")))
        if g.get("accent"):  # per-game акцент; пусто = наследует глобальный
            parts.append("    %r: %r," % ("accent", g["accent"]))
        if g.get("tweak"):  # твик игры: файл в tweaks/, дописывается в data-файл
            parts.append("    %r: %r," % ("tweak", g["tweak"]))
        parts.append('    "stats": [')
        parts.append(_rows(g.get("stats", [])))
        parts.append("    ],")
        parts.append('    "actions": [')
        parts.append(_rows(g.get("actions", [])))
        parts.append("    ],")
        parts.append("},")
    parts.append("}")
    parts.append("")
    return "\n".join(parts)


def next_index(games):
    """Наименьший свободный положительный индекс (заполняет дыры от удалённых игр)."""
    i = 1
    while i in games:
        i += 1
    return i


def add_game(games, root, title="TEST MENU", status="", index=None):
    """Добавить игру в манифест (in-place). Возвращает присвоенный индекс.
    index=None -> берётся next_index. stats/actions пустые."""
    if index is None:
        index = next_index(games)
    if index in games:
        raise ValueError(f"game_{index} уже есть в манифесте")
    games[index] = {
        "title": title or "TEST MENU",
        "root": root.replace("\\", "/"),
        "status": status,
        "stats": [],
        "actions": [],
    }
    return index


def remove_game(games, index):
    """Удалить игру из манифеста (in-place). Возвращает удалённую запись.
    Трогает только манифест — файлы игры и build/ не затрагивает."""
    if index not in games:
        raise KeyError(f"game_{index} нет в манифесте")
    return games.pop(index)


def default_title(root):
    """Заголовок меню по папке игры (родитель game/) без версий и платформ:
    «Game [v0.5]» / «Game-0.5-pc» / «My_Game v1.2b» -> «Game» / «My Game».
    Фигурные скобки выкидываются (в Ren'Py это текст-теги)."""
    norm = os.path.normpath(root or "")
    # Ren'Py: цель — папка game/, имя игры у родителя; Godot/Unity/RPG Maker — сама папка игры
    name = os.path.basename(os.path.dirname(norm)) if os.path.basename(norm).lower() == "game" else os.path.basename(norm)
    name = re.sub(r"[\[(][^\])]*[\])]", " ", name)
    name = re.sub(r"[-_ .]+v?\d+(?:\.\d+)+[a-z]?\b.*$", "", name, flags=re.I)
    name = re.sub(r"[-_ .]+v\d+[a-z]?\b.*$", "", name, flags=re.I)
    name = re.sub(r"[-_ ](pc|win|windows|linux|mac|market|android)$", "", name, flags=re.I)
    name = re.sub(r"[_{}]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip(" -.")
    return name or "TEST MENU"


def find_by_root(games, root):
    """Индекс игры с таким же root (без учёта регистра и вида слэшей) или None."""

    def norm(p):
        return os.path.normcase(os.path.normpath(p or ""))

    want = norm(root)
    for i in sorted(games):
        if norm(games[i].get("root")) == want:
            return i
    return None


def save_games(games, G, ACCENT, path=GAMES_DATA_PATH):
    """Записать манифест атомарно, оставив прошлую версию в <path>.bak.

    games_data.py импортируется всем тулкитом: оборванная запись (или текст, который
    не компилируется) ломает сразу и студию, и CLI — поэтому сначала проверка и
    временный файл, потом подмена."""
    text = dumps(games, G, ACCENT)
    compile(text, path, "exec")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")
    os.replace(tmp, path)


def load_games():
    """Вернуть (GAMES-копия, G, ACCENT), свежесчитанные с диска."""
    from tmkit import games_data

    importlib.reload(games_data)
    return copy.deepcopy(games_data.GAMES), games_data.G, games_data.ACCENT
