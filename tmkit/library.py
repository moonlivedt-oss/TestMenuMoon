"""Библиотека игр: найти все игры в папке, определить движок и состояние меню у каждой.

    for g in find_games("D:/Games"):
        print(g.name, g.engine.key, g.status, g.target)

Обход — на `depth` уровней вниз: «Игра v1.0/» или «Игра v1.0/Игра/». Найденная игра
дальше вглубь не просматривается (папки game/, www/, Binaries/ — её части, не игры).
Цель установки (`target`) — то, что принимает движок: у Ren'Py папка game/, у остальных —
папка игры. Статус: 'none' — меню нет, 'stale' — стоит старая версия, 'ok' — актуальное.
"""

import os
from dataclasses import dataclass
from typing import Optional

from tmkit import engines, manifest

# папки, которые не бывают играми и в которые незачем заходить
_SKIP = {
    "$recycle.bin",
    "system volume information",
    "__pycache__",
    ".git",
    "node_modules",
    "saves",
    "save",
    "logs",
    "cache",
    "bepinex",
    "mods",
    "tm_godot",
    "tm_ui",
}


@dataclass
class Found:
    name: str  # подпись: имя папки игры без версии
    folder: str  # папка игры
    target: str  # цель установки для движка
    engine: object  # tmkit.engines.Engine
    status: str  # 'none' | 'stale' | 'ok' | '?' (статус не определить)
    index: Optional[int] = None  # номер в манифесте, если игра там есть


def status_of(engine, target, data_text=None):
    """'none' | 'stale' | 'ok' для цели движка; '?' — если проверка упала."""
    try:
        if engine.key == "renpy":
            from tmkit import deploy

            return deploy.status(target, data_text)
        if not (engine.installed and engine.installed(target)):
            return "none"
        return "ok" if engine.current is None or engine.current(target) else "stale"
    except Exception:
        return "?"


def _target(engine, folder):
    if engine.key == "renpy":
        from tmkit import deploy

        return deploy.resolve_game_dir(folder) or folder
    return folder


def _detect(folder):
    eng = engines.detect_engine(folder)
    # голая папка с одним HTML (документация, ярлык) — не игра; HTML5 опознаём по index.html
    if eng is not None and eng.key == "web" and not _web_like(folder):
        return None
    # папка просто называется game (например, D:/Downloads/game с играми внутри) — не Ren'Py
    if eng is not None and eng.key == "renpy" and not _renpy_like(folder):
        return None
    return eng


def _renpy_like(folder):
    import glob

    game = os.path.join(folder, "game")
    if os.path.isdir(os.path.join(folder, "renpy")) and os.path.isdir(game):
        return True
    for d in (folder, game):
        e = glob.escape(d)
        if any(glob.glob(os.path.join(e, "*." + x)) for x in ("rpy", "rpyc", "rpa")):
            return True
    return False


def _web_like(folder):
    for sub in ("", "www", "package.nw", "app"):
        if os.path.exists(os.path.join(folder, sub, "index.html")):
            return True
    return os.path.isfile(os.path.join(folder, "package.nw"))


def find_games(folder, depth=2, games=None):
    """Игры в папке folder (сама folder тоже может быть игрой). games — манифест
    (для номеров и data-файлов); None — прочитать с диска."""
    if games is None:
        games = manifest.load_games()[0]
    out = []
    _walk(os.path.abspath(folder), depth, games, out)
    out.sort(key=lambda g: g.name.lower())
    return out


def _walk(folder, depth, games, out):
    eng = _detect(folder)
    if eng is not None:
        out.append(_found(folder, eng, games))
        return
    if depth <= 0:
        return
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return
    for n in names:
        p = os.path.join(folder, n)
        if n.lower() in _SKIP or n.startswith(".") or not os.path.isdir(p):
            continue
        _walk(p, depth - 1, games, out)


def _found(folder, eng, games):
    target = _target(eng, folder)
    index = manifest.find_by_root(games, target) if games else None
    data = None
    if index is not None and eng.key == "renpy":
        from tmkit import generate

        data = generate.render_game(index, games[index])
    name = _own_title(eng.key, folder) or manifest.default_title(
        target if eng.key == "renpy" else folder
    )
    if index is not None and games[index].get("title") not in (None, "", "TEST MENU"):
        name = games[index]["title"]
    return Found(name, folder, target, eng, status_of(eng, target, data), index)


def _own_title(key, folder):
    """Название, которое игра пишет о себе: Unity — app.info, RPG Maker — System.json,
    HTML5 — <title> в index.html. None — не нашлось (тогда имя папки)."""
    import json
    import re

    try:
        if key == "unity":
            from tmkit import saves

            names = saves.unity_names(folder)
            return names[1] if names and names[1] else None
        if key == "rpgmaker":
            for sub in ("data", os.path.join("www", "data"), os.path.join("package.nw", "data")):
                p = os.path.join(folder, sub, "System.json")
                if os.path.isfile(p):
                    with open(p, encoding="utf-8-sig") as f:
                        return (json.load(f).get("gameTitle") or "").strip() or None
        if key == "web":
            for sub in ("", "www", "package.nw", "app"):
                p = os.path.join(folder, sub, "index.html")
                if os.path.isfile(p):
                    with open(p, "rb") as f:
                        m = re.search(rb"<title>([^<]{1,80})</title>", f.read(65536), re.I)
                    return m.group(1).decode("utf-8", "replace").strip() or None if m else None
    except (OSError, ValueError):
        return None
    return None


def install(found):
    """Поставить (или обновить) меню. -> сообщение. Ren'Py из манифеста — с его data-файлом."""
    if found.engine.key == "renpy":
        from tmkit import deploy, generate

        if found.index is not None:
            # data-файл из свежего манифеста (снимок GAMES в процессе студии может отстать)
            games = manifest.load_games()[0]
            path = generate.data_path(found.index)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(generate.render_game(found.index, games[found.index]))
            deploy.deploy_to(found.target, path)
            return f"меню и данные game_{found.index} разложены: {found.target}"
        root = deploy.quick_install(found.target)
        return f"меню установлено (статы найдутся сами): {root}"
    return found.engine.deploy(found.target)


def remove(found):
    if found.engine.key == "renpy":
        from tmkit import deploy

        return f"снято ({deploy.remove_from(found.target)} файлов): {found.target}"
    return found.engine.uninstall(found.target)


def refresh(found, games=None):
    """Перечитать статус после установки/снятия (in-place). -> found."""
    if games is None:
        games = manifest.load_games()[0]
    new = _found(found.folder, found.engine, games)
    found.status, found.index, found.target = new.status, new.index, new.target
    return found
