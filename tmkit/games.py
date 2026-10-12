#!/usr/bin/env python3
"""Логика поверх данных манифеста: ROOTS и автопоиск basedir/launcher/python.exe.

Данные (title/root/status/stats/actions по каждой игре) — в games_data.py.
Здесь — производные вещи, которые нужны скриптам пайплайна и студии.

GAMES/ROOTS — снимок манифеста на момент импорта: для CLI (один запуск = один
процесс) этого достаточно. Студия правит манифест на лету (добавляет игры), поэтому
зовёт *_of(root) — они работают по пути и от снимка не зависят.
"""

import os, re, glob

from tmkit.manifest import load_games

GAMES, G, ACCENT = load_games()  # снимок манифеста на момент импорта (см. выше)

# производное: индекс -> папка game/
ROOTS = {i: g["root"] for i, g in GAMES.items()}


def basedir_of(root):
    """Папка с лаунчером (.py/.exe) — на уровень выше game/."""
    return os.path.dirname(root)


def launcher_of(root):
    """Автопоиск .py-лаунчера Ren'Py (тот, у кого есть парный .exe)."""
    pys = sorted(glob.glob(os.path.join(glob.escape(basedir_of(root)), "*.py")))
    for py in pys:
        if os.path.exists(py[:-3] + ".exe"):
            return py
    return pys[0] if pys else None


def python_exe_of(root):
    """Автопоиск встроенного python.exe (py2/py3); из нескольких — x86_64 вперёд."""
    hits = glob.glob(
        os.path.join(glob.escape(basedir_of(root)), "lib", "**", "python.exe"), recursive=True
    )
    hits.sort(key=lambda p: ("x86_64" not in p, p))
    return hits[0] if hits else None


# служебные .exe рядом с игрой: помощники nw.js/Unity/Chromium, деинсталляторы, редисты
_EXE_SKIP = re.compile(
    r"^(notification_helper|unitycrashhandler\w*|crashpad_handler|unins\d*|uninstall\w*"
    r"|python\w*|zsync\w*|nwjc|payload|vc_?redist\w*|dxsetup|dxwebsetup|setup)$",
    re.I,
)


def pick_exe(folder):
    """Главный .exe игры в папке или None: без служебных; Game.exe и .exe с именем
    папки — вперёд, дальше самый крупный файл (у nw.js/Unity это сама игра)."""
    exes = [
        p for p in glob.glob(os.path.join(glob.escape(folder), "*.exe"))
        if not _EXE_SKIP.match(os.path.splitext(os.path.basename(p))[0])
    ]
    if not exes:
        return None
    dirname = os.path.basename(os.path.normpath(folder)).lower()

    def rank(p):
        stem = os.path.splitext(os.path.basename(p))[0].lower()
        try:
            size = os.path.getsize(p)
        except OSError:
            size = 0
        return (stem != "game", stem != dirname, -size, p)

    return sorted(exes, key=rank)[0]


def basedir(i):
    return basedir_of(GAMES[i]["root"])


def launcher(i):
    return launcher_of(GAMES[i]["root"])


def python_exe(i):
    return python_exe_of(GAMES[i]["root"])
