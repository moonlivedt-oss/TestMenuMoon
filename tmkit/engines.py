#!/usr/bin/env python3
"""Абстракция «engine backend»: единый реестр движков и их возможностей.

Пока два реальных бэкенда, у которых РАЗНЫЙ набор шагов — это и есть смысл абстракции:
  • Ren'Py — полный пайплайн (extract → scan → generate → deploy → verify), управляется
    манифестом по индексу игры (см. CLI в корне). deploy/uninstall здесь = None,
    потому что это батч по манифесту, а не операция над одним путём.
  • Twine  — переменные видны в рантайме, поэтому extract/scan/generate НЕ нужны;
    только deploy/uninstall (внедрить/убрать меню в один HTML-файл).

`detect_engine(path)` определяет подходящий бэкенд по цели (папке game/ или .html).
"""
import os, glob, importlib.util
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from tmkit.paths import ROOT

ALL_STEPS = ("extract", "scan", "generate", "deploy", "verify", "uninstall")


@dataclass
class Engine:
    key: str
    title: str
    target_kind: str                 # что такое «цель»: renpy-game-folder | twine-html
    steps: Sequence[str]             # поддержанные шаги пайплайна
    detect: Callable[[str], bool]    # распознать цель по пути
    deploy: Optional[Callable[[str], str]] = None
    uninstall: Optional[Callable[[str], str]] = None
    scan: Optional[Callable[[str], str]] = None       # статический поиск кандидатов по пути
    installed: Optional[Callable[[str], bool]] = None  # установлено ли меню в цели
    current: Optional[Callable[[str], bool]] = None    # установленное меню = текущая версия

    def supports(self, step):
        return step in self.steps


# ------------------------------------------------------------------ Ren'Py
def _has_renpy_scripts(d):
    """Есть ли в папке скрипты Ren'Py — исходные .rpy или скомпилированные .rpyc.
    .rpyc важны: собранные/распространяемые игры часто идут без исходников."""
    return bool(glob.glob(os.path.join(glob.escape(d), "*.rpy"))
                or glob.glob(os.path.join(glob.escape(d), "*.rpyc")))


def _renpy_detect(path):
    if not os.path.isdir(path):
        return False
    # 1) сама папка game/ — канонич. цель деплоя (даже пустая, до сборки)
    if os.path.basename(path.rstrip("/\\")).lower() == "game":
        return True
    # 2) папка со скриптами Ren'Py прямо внутри
    if _has_renpy_scripts(path):
        return True
    # 3) корень проекта/дистрибутива: внутри game/ со скриптами или движок renpy/
    game = os.path.join(path, "game")
    if os.path.isdir(game) and (_has_renpy_scripts(game) or os.path.isdir(os.path.join(path, "renpy"))):
        return True
    return False


RENPY = Engine(
    key="renpy", title="Ren'Py", target_kind="renpy-game-folder",
    steps=("extract", "scan", "generate", "deploy", "verify", "uninstall"),
    detect=_renpy_detect,
    deploy=None,      # батч по манифесту: gen_data.py N + deploy.py N
    uninstall=None,   # uninstall.py N
    installed=lambda p: os.path.exists(os.path.join(p, "zzz_testmenu_engine.rpy")),
)


# --- общий загрузчик top-level модуля движка (engines/<name>/<file>.py) ---
def _load_engine_module(name, filename):
    path = os.path.join(ROOT, "engines", name, filename)
    stem = os.path.splitext(filename)[0]
    spec = importlib.util.spec_from_file_location(f"tm_{name}_{stem}", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _load_inject(name):
    return _load_engine_module(name, "inject.py")


# ------------------------------------------------------------------ Twine
_TWINE_MARKS = (b"<tw-storydata", b"<tw-story", b"SugarCube")


def _is_twine_html(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return False
    return any(m in data for m in _TWINE_MARKS)


def _twine_detect(path):
    # только настоящие истории Twine (маркеры в HTML); прочий HTML — движок WEB
    if os.path.isfile(path):
        return path.lower().endswith(".html") and _is_twine_html(path)
    if os.path.isdir(path):
        return any(_is_twine_html(h) for h in glob.glob(os.path.join(glob.escape(path), "*.html")))
    return False


TWINE = Engine(
    key="twine", title="Twine / SugarCube", target_kind="twine-html",
    # значения правятся в рантайме, но имена $var есть в исходниках пассажей -> scan
    steps=("scan", "deploy", "uninstall"),
    detect=_twine_detect,
    deploy=lambda p: _load_inject("twine").deploy_file(p),
    uninstall=lambda p: _load_inject("twine").remove_file(p),
    scan=lambda p: _load_engine_module("twine", "scan.py").report(p),
    installed=lambda p: _load_inject("twine").is_installed(p),
    current=lambda p: _load_inject("twine").is_current(p),
)


# ------------------------------------------------------------------ любая HTML5-игра
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
    if os.path.isfile(pkg):
        try:
            import zipfile

            with zipfile.ZipFile(pkg) as z:
                return "index.html" in z.namelist()
        except (OSError, zipfile.BadZipFile):
            return False
    return False


WEB = Engine(
    key="web", title="HTML5", target_kind="web-html",
    # Phaser, Construct 2, GDevelop и свои движки: всё ищется в рантайме
    steps=("deploy", "uninstall"),
    detect=_web_detect,
    deploy=lambda p: _load_inject("web").deploy_file(p),
    uninstall=lambda p: _load_inject("web").remove_file(p),
    installed=lambda p: _load_inject("web").is_installed(p),
    current=lambda p: _load_inject("web").is_current(p),
)


# ------------------------------------------------------------------ RPG Maker MV/MZ
_RPGM_BASES = ("", "www", "package.nw", os.path.join("package.nw", "www"))
_RPGM_CORES = (("js", "rpg_core.js"), ("js", "rmmz_core.js"), ("data", "System.json"))


def _rpgmaker_detect(path):
    if not os.path.isdir(path):
        return False
    for sub in _RPGM_BASES:
        d = os.path.join(path, sub) if sub else path
        has_index = any(os.path.exists(os.path.join(d, *p))
                        for p in (("index.html",), ("js", "plugins.js")))
        if has_index and any(os.path.exists(os.path.join(d, *p)) for p in _RPGM_CORES):
            return True
    # игра в package.nw-архиве рядом с Game.exe (inject распакует при деплое)
    pkg = os.path.join(path, "package.nw")
    if os.path.isfile(pkg):
        try:
            import zipfile

            with zipfile.ZipFile(pkg) as z:
                names = {n.replace("\\", "/").lower() for n in z.namelist()}
        except (OSError, zipfile.BadZipFile):
            return False
        cores = {"/".join(c).lower() for c in _RPGM_CORES}
        return any(n in cores or n[len("www/"):] in cores for n in names)
    return False


RPGMAKER = Engine(
    key="rpgmaker", title="RPG Maker MV/MZ", target_kind="rpgmaker-folder",
    # значения правятся в рантайме, но имена переменных/предметов есть в data/*.json -> scan
    steps=("scan", "deploy", "uninstall"),
    detect=_rpgmaker_detect,
    deploy=lambda p: _load_inject("rpgmaker").deploy_file(p),
    uninstall=lambda p: _load_inject("rpgmaker").remove_file(p),
    scan=lambda p: _load_engine_module("rpgmaker", "scan.py").report(p),
    installed=lambda p: _load_inject("rpgmaker").is_installed(p),
    current=lambda p: _load_inject("rpgmaker").is_current(p),
)


# ------------------------------------------------------------------ Godot 4
def _godot_detect(path):
    # папка с .pck (или .exe/.pck) Godot; Godot 3 тоже опознаём — inject откажет понятно
    if os.path.isfile(path):
        if not path.lower().endswith((".pck", ".exe")):
            return False
        path = os.path.dirname(path)
    if not os.path.isdir(path) or os.path.exists(os.path.join(path, "UnityPlayer.dll")):
        return False
    pck = _load_engine_module("godot", "pck.py")
    try:
        return pck.find_pack(path) is not None
    except Exception:
        return False


GODOT = Engine(
    key="godot", title="Godot 4", target_kind="godot-folder",
    # меню находит переменные само в рантайме; scan — подсказка по сценам Dialogic из .pck
    steps=("scan", "deploy", "uninstall"),
    detect=_godot_detect,
    deploy=lambda p: _load_engine_module("godot", "inject.py").deploy_file(p),
    uninstall=lambda p: _load_engine_module("godot", "inject.py").remove_file(p),
    scan=lambda p: _load_engine_module("godot", "scan.py").report(p),
    installed=lambda p: _load_engine_module("godot", "inject.py").is_installed(p),
    current=lambda p: _load_engine_module("godot", "inject.py").is_current(p),
)


# ------------------------------------------------------------------ Unity (IL2CPP)
def _unity_detect(path):
    if os.path.isfile(path):
        path = os.path.dirname(path)
    return os.path.isdir(path) and os.path.exists(os.path.join(path, "UnityPlayer.dll"))


UNITY = Engine(
    key="unity", title="Unity (BepInEx)", target_kind="unity-folder",
    # BepInEx 6 + UnityExplorer + своё меню (engines/unity/plugin); scan не нужен — всё в рантайме
    steps=("deploy", "uninstall"),
    detect=_unity_detect,
    deploy=lambda p: _load_engine_module("unity", "inject.py").deploy_file(p),
    uninstall=lambda p: _load_engine_module("unity", "inject.py").remove_file(p),
    installed=lambda p: _load_engine_module("unity", "inject.py").is_installed(p),
    current=lambda p: _load_engine_module("unity", "inject.py").is_current(p),
)


# ------------------------------------------------------------------ Unreal Engine 4/5 (UE4SS)
UNREAL = Engine(
    key="unreal", title="Unreal (UE4SS)", target_kind="unreal-folder",
    # UE4SS + Lua-мод TestMenu; значения — Live View в окне UE4SS
    steps=("deploy", "uninstall"),
    detect=lambda p: _load_engine_module("unreal", "inject.py").is_unreal(p),
    deploy=lambda p: _load_engine_module("unreal", "inject.py").deploy_file(p),
    uninstall=lambda p: _load_engine_module("unreal", "inject.py").remove_file(p),
    installed=lambda p: _load_engine_module("unreal", "inject.py").is_installed(p),
    current=lambda p: _load_engine_module("unreal", "inject.py").is_current(p),
)


# ------------------------------------------------------------------ реестр
# порядок важен для detect: папочные движки до Ren'Py, затем Twine (по маркерам в HTML),
# последний — WEB: любой оставшийся HTML
REGISTRY = {e.key: e for e in (RPGMAKER, UNITY, GODOT, UNREAL, RENPY, TWINE, WEB)}


def detect_engine(path):
    """Вернуть Engine, чей detect() опознал цель, иначе None."""
    for e in REGISTRY.values():
        try:
            if e.detect(path):
                return e
        except Exception:
            pass
    return None


# ------------------------------------------------------------------ установка в любую игру
HOTKEYS = {
    "renpy": "Shift+T / F9", "twine": "Shift+T", "rpgmaker": "Shift+T",
    "godot": "Shift+T / F9", "unity": "Shift+T / F9 (F7 — UnityExplorer)", "web": "Shift+T", "unreal": "Ctrl+Shift+H (справка), окно UE4SS — Live View",
}


def _root_for(path):
    # .exe/.html/.pck -> папка, кроме HTML (цель Twine и WEB — сам .html)
    if os.path.isfile(path) and not path.lower().endswith((".html", ".htm")):
        return os.path.dirname(path)
    return path


def quick_install_any(path):
    """Поставить меню в игру по пути, движок — по detect. -> (Engine, цель, сообщение)."""
    path = _root_for(path)
    eng = detect_engine(path)
    if eng is None or eng.key == "renpy":
        from tmkit import deploy as _deploy

        root = _deploy.quick_install(path)      # ValueError, если это не Ren'Py
        return REGISTRY["renpy"], root, f"меню установлено: {root}"
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
        return REGISTRY["renpy"], root, f"снято ({_deploy.remove_from(root)} файлов): {root}"
    return eng, path, eng.uninstall(path)
