#!/usr/bin/env python3
"""Реестр движков: как опознать игру, поставить и снять меню, проверить установку.

Ren'Py — полный пайплайн по манифесту (collect -> curate -> gen -> deploy -> verify),
поэтому deploy/uninstall у него None: это батч по индексам игр (tm.py), а установка
по пути без манифеста — tmkit.deploy.quick_install. Остальные движки (RPG Maker, HTML5,
Twine, Godot, Unity, Unreal) находят данные в рантайме: им нужны только установка и
снятие по пути, их код — в engines/<движок>/inject.py (и scan.py, где он есть).

`detect_engine(path)` — какой движок у игры; `quick_install_any(path)` — поставить меню.
"""

import glob
import os
import re
import sys
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from tmkit.paths import ROOT

sys.path.insert(0, os.path.join(ROOT, "engines", "_shared"))
import tm_load  # noqa: E402  (модули движков по пути, с кэшем)

ALL_STEPS = ("extract", "scan", "generate", "deploy", "verify", "uninstall")


@dataclass
class Engine:
    key: str
    title: str
    target_kind: str  # что такое «цель»: папка game/, HTML-файл, папка игры
    steps: Sequence[str]  # поддержанные шаги пайплайна
    detect: Callable[[str], bool]  # распознать цель по пути
    deploy: Optional[Callable[[str], str]] = None
    uninstall: Optional[Callable[[str], str]] = None
    scan: Optional[Callable[[str], str]] = None  # статический поиск кандидатов по пути
    installed: Optional[Callable[[str], bool]] = None  # установлено ли меню в цели
    current: Optional[Callable[[str], bool]] = (
        None  # установленное меню = текущая версия
    )

    def supports(self, step):
        return step in self.steps


def _load_engine_module(name, filename):
    """engines/<name>/<filename> — один экземпляр на процесс (tm_load)."""
    return tm_load.load(name, filename)


def _load_inject(name):
    return _load_engine_module(name, "inject.py")


def _call(engine, func, filename="inject.py"):
    """Ленивая ссылка на функцию модуля движка: модуль грузится при первом вызове."""
    return lambda p: getattr(_load_engine_module(engine, filename), func)(p)


def _injector(engine, scan=False):
    """deploy/uninstall/installed/current (+scan) из engines/<engine>/inject.py."""
    out = dict(
        deploy=_call(engine, "deploy_file"),
        uninstall=_call(engine, "remove_file"),
        installed=_call(engine, "is_installed"),
        current=_call(engine, "is_current"),
    )
    if scan:
        out["scan"] = _call(engine, "report", "scan.py")
    return out


# ------------------------------------------------------------------ Ren'Py
def _has_renpy_scripts(d):
    """Есть ли в папке скрипты Ren'Py — исходные .rpy или скомпилированные .rpyc
    (собранные игры часто идут без исходников)."""
    e = glob.escape(d)
    return bool(
        glob.glob(os.path.join(e, "*.rpy")) or glob.glob(os.path.join(e, "*.rpyc"))
    )


def _renpy_detect(path):
    if not os.path.isdir(path):
        return False
    # 1) сама папка game/ — каноническая цель (даже пустая, до сборки)
    if os.path.basename(path.rstrip("/\\")).lower() == "game":
        return True
    # 2) папка со скриптами Ren'Py прямо внутри
    if _has_renpy_scripts(path):
        return True
    # 3) корень дистрибутива: внутри game/ со скриптами или движок renpy/
    game = os.path.join(path, "game")
    return os.path.isdir(game) and (
        _has_renpy_scripts(game) or os.path.isdir(os.path.join(path, "renpy"))
    )


RENPY = Engine(
    key="renpy",
    title="Ren'Py",
    target_kind="renpy-game-folder",
    steps=ALL_STEPS,
    detect=_renpy_detect,
    installed=lambda p: os.path.exists(os.path.join(p, "zzz_testmenu_engine.rpy")),
)


# ------------------------------------------------------------------ Twine
_TWINE_MARKS = (b"<tw-storydata", b"<tw-story", b"SugarCube")
# наш же блок меню (в нём есть слово SugarCube) — не повод считать игру историей Twine
_OUR_BLOCK = re.compile(rb"<!-- TM_\w+_MENU_START -->.*?<!-- TM_\w+_MENU_END -->", re.S)


def _is_twine_html(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return False
    data = _OUR_BLOCK.sub(b"", data)
    return any(m in data for m in _TWINE_MARKS)


def _twine_detect(path):
    # только настоящие истории Twine (маркеры в HTML); прочий HTML — движок HTML5
    if os.path.isfile(path):
        return path.lower().endswith(".html") and _is_twine_html(path)
    if os.path.isdir(path):
        return any(
            _is_twine_html(h)
            for h in glob.glob(os.path.join(glob.escape(path), "*.html"))
        )
    return False


TWINE = Engine(
    key="twine",
    title="Twine / SugarCube",
    target_kind="twine-html",
    # значения правятся в рантайме, но имена $var есть в исходниках пассажей -> scan
    steps=("scan", "deploy", "uninstall"),
    detect=_twine_detect,
    **_injector("twine", scan=True),
)


# ------------------------------------------------------------------ любая HTML5-игра
def _zip_has(path, names):
    """Есть ли в zip-архиве path хоть одно из имён (без учёта регистра и вида слэшей)."""
    import zipfile

    try:
        with zipfile.ZipFile(path) as z:
            have = {n.replace("\\", "/").lower() for n in z.namelist()}
    except (OSError, zipfile.BadZipFile):
        return False
    return any(n.lower() in have for n in names)


def _web_detect(path):
    if os.path.isfile(path):
        return path.lower().endswith((".html", ".htm"))
    if not os.path.isdir(path):
        return False
    for sub in ("", "www", "package.nw", "app"):
        if os.path.isfile(os.path.join(path, sub, "index.html")):
            return True
    if glob.glob(os.path.join(glob.escape(path), "*.html")):
        return True
    # nw.js-игра с упакованным package.nw (zip): inject распакует при установке
    pkg = os.path.join(path, "package.nw")
    return os.path.isfile(pkg) and _zip_has(pkg, ["index.html"])


WEB = Engine(
    key="web",
    title="HTML5",
    target_kind="web-html",
    # Phaser, Construct 2, GDevelop и свои движки: всё ищется в рантайме
    steps=("deploy", "uninstall"),
    detect=_web_detect,
    **_injector("web"),
)


# ------------------------------------------------------------------ RPG Maker MV/MZ
_RPGM_BASES = ("", "www", "package.nw", os.path.join("package.nw", "www"))
_RPGM_CORES = (("js", "rpg_core.js"), ("js", "rmmz_core.js"), ("data", "System.json"))


def _rpgmaker_detect(path):
    if not os.path.isdir(path):
        return False
    for sub in _RPGM_BASES:
        d = os.path.join(path, sub) if sub else path
        has_index = any(
            os.path.exists(os.path.join(d, *p))
            for p in (("index.html",), ("js", "plugins.js"))
        )
        if has_index and any(os.path.exists(os.path.join(d, *p)) for p in _RPGM_CORES):
            return True
    # игра в package.nw-архиве рядом с Game.exe (inject распакует при установке)
    pkg = os.path.join(path, "package.nw")
    if os.path.isfile(pkg):
        cores = ["/".join(c) for c in _RPGM_CORES]
        return _zip_has(pkg, cores + ["www/" + c for c in cores])
    return False


RPGMAKER = Engine(
    key="rpgmaker",
    title="RPG Maker MV/MZ",
    target_kind="rpgmaker-folder",
    # значения правятся в рантайме, но имена переменных/предметов есть в data/*.json -> scan
    steps=("scan", "deploy", "uninstall"),
    detect=_rpgmaker_detect,
    **_injector("rpgmaker", scan=True),
)


# ------------------------------------------------------------------ Godot 4
def _godot_detect(path):
    # папка с .pck (или .exe со вшитым пакетом): Godot 4 и 3 (у 3 — своё меню tm_menu3.gd)
    if os.path.isfile(path):
        if not path.lower().endswith((".pck", ".exe")):
            return False
        path = os.path.dirname(path)
    if not os.path.isdir(path) or os.path.exists(os.path.join(path, "UnityPlayer.dll")):
        return False
    try:
        return _load_engine_module("godot", "pck.py").find_pack(path) is not None
    except Exception:
        return False


GODOT = Engine(
    key="godot",
    title="Godot 3 / 4",
    target_kind="godot-folder",
    # меню находит переменные само в рантайме; scan — подсказка по сценам Dialogic из .pck
    steps=("scan", "deploy", "uninstall"),
    detect=_godot_detect,
    **_injector("godot", scan=True),
)


# ------------------------------------------------------------------ Unity (BepInEx)
def _unity_detect(path):
    if os.path.isfile(path):
        path = os.path.dirname(path)
    return os.path.isdir(path) and os.path.exists(os.path.join(path, "UnityPlayer.dll"))


UNITY = Engine(
    key="unity",
    title="Unity (BepInEx)",
    target_kind="unity-folder",
    # IL2CPP — BepInEx 6 + engines/unity/plugin, Mono — BepInEx 5 + engines/unity/mono
    steps=("deploy", "uninstall"),
    detect=_unity_detect,
    **_injector("unity"),
)


# ------------------------------------------------------------------ Unreal Engine 4/5 (UE4SS)
UNREAL = Engine(
    key="unreal",
    title="Unreal (UE4SS)",
    target_kind="unreal-folder",
    # UE4SS + Lua-мод TestMenu; значения — Live View в окне UE4SS
    steps=("deploy", "uninstall"),
    detect=_call("unreal", "is_unreal"),
    **_injector("unreal"),
)


# ------------------------------------------------------------------ реестр
# порядок важен для detect: папочные движки до Ren'Py, затем Twine (по маркерам в HTML),
# последний — HTML5: любой оставшийся HTML
REGISTRY = {e.key: e for e in (RPGMAKER, UNITY, GODOT, UNREAL, RENPY, TWINE, WEB)}


def detect_engine(path):
    """Engine, чей detect() опознал цель, иначе None."""
    for e in REGISTRY.values():
        try:
            if e.detect(path):
                return e
        except Exception:
            pass
    return None


# ------------------------------------------------------------------ установка в любую игру
HOTKEYS = {
    "renpy": "Shift+T / F9",
    "twine": "Shift+T",
    "rpgmaker": "Shift+T",
    "godot": "Shift+T / F9",
    "unity": "Shift+T / F9 (F7 — UnityExplorer)",
    "web": "Shift+T",
    "unreal": "Ctrl+Shift+H (справка), окно UE4SS — Live View",
}


def _root_for(path):
    # .exe/.pck -> папка; HTML остаётся файлом (цель Twine и HTML5 — сам .html)
    if os.path.isfile(path) and not path.lower().endswith((".html", ".htm")):
        return os.path.dirname(path)
    return path


def quick_install_any(path):
    """Поставить меню в игру по пути, движок — по detect. -> (Engine, цель, сообщение)."""
    path = _root_for(path)
    eng = detect_engine(path)
    if eng is None or eng.key == "renpy":
        from tmkit import deploy as _deploy

        root = _deploy.quick_install(path)  # ValueError, если это не Ren'Py
        return RENPY, root, f"меню установлено: {root}"
    if eng.deploy is None:
        raise ValueError(f"{eng.title}: установка по пути не поддерживается")
    return eng, path, eng.deploy(path)


def quick_remove_any(path):
    path = _root_for(path)
    eng = detect_engine(path)
    if eng is None or eng.key == "renpy":
        from tmkit import deploy as _deploy

        root = _deploy.resolve_game_dir(path)
        if root is None:
            raise ValueError(f"не похоже на игру: {path}")
        return RENPY, root, f"снято ({_deploy.remove_from(root)} файлов): {root}"
    return eng, path, eng.uninstall(path)
