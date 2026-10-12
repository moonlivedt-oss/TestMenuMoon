#!/usr/bin/env python3
"""Ядро deploy/uninstall: разложить движок+data (+UI) в game/ и снести меню.

CLI — tm.py deploy / uninstall / quick. Работа по путям (deploy_to, quick_install,
remove_from) юнит-тестится на temp-папке без манифеста; deploy / uninstall — по индексу игры.
"""

import os, re, glob, shutil

from tmkit.games import ROOTS
from tmkit.paths import (
    BUILD, ENGINE_SRC, ROOT, TRANSLATE_SRC, game_data_file, read_source, source_stamp,
)
from tmkit import generate, report

ENGINE_NAME = "zzz_testmenu_engine.rpy"
DATA_NAME = "zzz_testmenu_data.rpy"
TRANSLATE_NAME = "zzz_testmenu_translate.rpy"
UI_DIRNAME = "tm_ui"
# UI-ассеты (9-slice рамки) лежат рядом с движком, в корне проекта.
UI_SRC = os.path.join(ROOT, "assets", "tm_ui")


def clean_rpyc(root):
    """Снести скомпилированные zzz_testmenu_*.rpyc (иначе Ren'Py возьмёт устаревший).
    Возвращает число удалённых файлов."""
    removed = 0
    for rpyc in glob.glob(os.path.join(glob.escape(root), "zzz_testmenu_*.rpyc")):
        try:
            os.remove(rpyc)
            removed += 1
        except OSError:
            pass
    return removed


def _text(path):
    """Текст файла с едиными концами строк или None, если файла нет."""
    try:
        with open(path, encoding="utf-8", errors="replace", newline="") as f:
            return f.read().replace("\r\n", "\n")
    except OSError:
        return None


_SRC_CACHE = {}


def _src_text(path):
    """Текст исходника (файл или папка частей) с едиными концами строк и кэшем по mtime:
    студия спрашивает статус каждой игры при каждом обновлении списка, а движок весит ~300 КБ."""
    key = source_stamp(path)
    if key is None:
        return None
    if key not in _SRC_CACHE:
        try:
            _SRC_CACHE[key] = read_source(path).replace("\r\n", "\n")
        except OSError:
            return None
    return _SRC_CACHE[key]


def renpy_version(root):
    """(major, minor) Ren'Py игры — по renpy/ рядом с game/; None, если не найдено."""
    base = os.path.dirname(os.path.abspath(root))
    for fn in ("vc_version.py", "__init__.py"):
        t = _text(os.path.join(base, "renpy", fn)) or ""
        m = re.search(r"^version\s*=\s*u?['\"](\d+)\.(\d+)", t, re.M) or re.search(
            r"version_tuple\s*=\s*\((\d+),\s*(\d+)", t
        )
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def engine_text(root, engine_src=ENGINE_SRC):
    """Текст движка под версию Ren'Py игры. До 7.2 у input нет свойства copypaste —
    lint и запуск падали; там его убираем (вставка Ctrl+V в поля меню недоступна)."""
    text = _src_text(engine_src)
    if text is None:
        return None
    v = renpy_version(root)
    if v is not None and v < (7, 2):
        text = text.replace(" copypaste True", "")
    return text


_HIDDEN = 0x2  # FILE_ATTRIBUTE_HIDDEN


def _attrs(path):
    try:
        import ctypes

        # & 0xFFFFFFFF: ctypes отдаёт результат знаковым — «нет файла» приходило как -1, и
        # -1 & HIDDEN считался «скрытым»: после установки меню прятались все его файлы
        a = ctypes.windll.kernel32.GetFileAttributesW(str(path)) & 0xFFFFFFFF
        return None if a == 0xFFFFFFFF else a
    except (AttributeError, OSError):
        return None  # не Windows


def _unhide_menu(root):
    """Скрытые файлы меню (пользователь их спрятал) Windows не даёт перезаписать: снимаем
    «скрытый» на время записи. -> список путей, которым его надо вернуть."""
    import ctypes

    names = [ENGINE_NAME, TRANSLATE_NAME, DATA_NAME, UI_DIRNAME]
    paths = [os.path.join(root, n) for n in names]
    ui = os.path.join(root, UI_DIRNAME)
    if os.path.isdir(ui):
        for base, dirs, files in os.walk(ui):
            paths += [os.path.join(base, x) for x in dirs + files]
    hidden = []
    for p in paths:
        a = _attrs(p)
        if a is not None and a & _HIDDEN:
            ctypes.windll.kernel32.SetFileAttributesW(p, a & ~_HIDDEN)
            hidden.append(p)
    return hidden


def _rehide(paths):
    import ctypes

    for p in paths:
        a = _attrs(p)
        if a is not None:
            ctypes.windll.kernel32.SetFileAttributesW(p, a | _HIDDEN)


def _write_engine(root, engine_src):
    text = engine_text(root, engine_src)
    with open(os.path.join(root, ENGINE_NAME), "w", encoding="utf-8", newline="") as f:
        f.write(text)
    # модуль перевода реплик (AutoTranslator) едет вместе с движком — но только
    # рядом с настоящим движком проекта (в юнит-тестах с temp-движком не кладём)
    if os.path.abspath(engine_src) == os.path.abspath(ENGINE_SRC) and os.path.exists(
        TRANSLATE_SRC
    ):
        shutil.copyfile(TRANSLATE_SRC, os.path.join(root, TRANSLATE_NAME))


def status(root, data_text=None, engine_src=ENGINE_SRC):
    """Состояние меню в папке игры: 'none' — не установлено, 'stale' — установлено,
    но движок отличается от исходника (или data — от data_text, если он передан),
    'ok' — установлено и актуально."""
    installed = _text(os.path.join(root, ENGINE_NAME))
    if installed is None:
        return "none"
    if installed != engine_text(root, engine_src):
        return "stale"
    if os.path.abspath(engine_src) == os.path.abspath(ENGINE_SRC) and os.path.exists(
        TRANSLATE_SRC
    ):
        if _text(os.path.join(root, TRANSLATE_NAME)) != _src_text(TRANSLATE_SRC):
            return "stale"
    if data_text is not None and _text(
        os.path.join(root, DATA_NAME)
    ) != data_text.replace("\r\n", "\n"):
        return "stale"
    return "ok"


def status_of(i):
    """status() для игры манифеста game_{i} (data сверяется с текущим манифестом)."""
    return status(ROOTS[i], generate.render(i))


def deploy_to(root, data_file, engine_src=ENGINE_SRC, ui_src=UI_SRC):
    """Скопировать движок + data (+ tm_ui) в root и снести старые .rpyc.

    Возвращает число снесённых .rpyc. Кидает FileNotFoundError, если нет движка
    или data-файла (проверяемо до записи чего-либо в игру)."""
    if not os.path.exists(engine_src):
        raise FileNotFoundError(f"движок ({engine_src})")
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"data ({data_file})")
    hidden = _unhide_menu(root)
    try:
        return _deploy_files(root, data_file, engine_src, ui_src)
    finally:
        _rehide(hidden)


def _deploy_files(root, data_file, engine_src, ui_src):
    _write_engine(root, engine_src)
    shutil.copy2(data_file, os.path.join(root, DATA_NAME))
    # UI-ассеты рядом с движком -> game/tm_ui/ (без служебных _*.png)
    if os.path.isdir(ui_src):
        shutil.copytree(
            ui_src,
            os.path.join(root, UI_DIRNAME),
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("_*"),
        )
    return clean_rpyc(root)


def resolve_game_dir(path):
    """Папка game/ по любому пути игры: сама game/, корень дистрибутива (с game/
    внутри) или .exe/.py лаунчер рядом с game/. None — если не похоже на Ren'Py."""
    p = os.path.abspath(path)
    if os.path.isfile(p):
        p = os.path.dirname(p)
    if os.path.basename(p.rstrip("/\\")).lower() == "game" and os.path.isdir(p):
        return p
    sub = os.path.join(p, "game")
    if os.path.isdir(sub):
        return sub
    if glob.glob(os.path.join(glob.escape(p), "*.rpy")) or glob.glob(
        os.path.join(glob.escape(p), "*.rpyc")
    ):
        return p
    return None


def quick_install(path, engine_src=ENGINE_SRC, ui_src=UI_SRC):
    """Поставить меню в ЛЮБУЮ Ren'Py-игру без манифеста: только движок + tm_ui.

    Без data-файла движок сам находит статы (режим «авто»), подсказки к выборам,
    сканер, сюжет — всё работает. Уже лежащий data-файл не трогаем.
    Возвращает папку game/; ValueError, если путь не похож на игру Ren'Py."""
    root = resolve_game_dir(path)
    if root is None:
        raise ValueError(f"не похоже на игру Ren'Py (нет game/ или .rpy/.rpyc): {path}")
    if not os.path.exists(engine_src):
        raise FileNotFoundError(f"движок ({engine_src})")
    clean_rpyc(root)
    hidden = _unhide_menu(root)
    try:
        _write_engine(root, engine_src)
        if os.path.isdir(ui_src):
            shutil.copytree(
                ui_src,
                os.path.join(root, UI_DIRNAME),
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("_*"),
            )
    finally:
        _rehide(hidden)
    return root


def remove_from(root):
    """Снести файлы меню (zzz_testmenu_*.rpy/.rpyc) и tm_ui/ из root.
    Возвращает число удалённых объектов (папка tm_ui считается за один)."""
    removed = 0
    # glob.escape: «Game [v0.5]» иначе читается как шаблон, и движок оставался в игре
    esc = glob.escape(root)
    for f in glob.glob(os.path.join(esc, "zzz_testmenu_*.rpy")) + glob.glob(
        os.path.join(esc, "zzz_testmenu_*.rpyc")
    ):
        try:
            os.remove(f)
            removed += 1
        except OSError:
            pass
    ui_dir = os.path.join(root, UI_DIRNAME)
    if os.path.isdir(ui_dir):
        shutil.rmtree(ui_dir, ignore_errors=True)
        removed += 1
    # следы самого меню: состояние (избранное, HUD) и быстрые слоты в game/saves.
    # Свои имена переменных (tm_names.json), скриншоты и отчёты тестера — работа
    # пользователя, их не трогаем.
    for f in [os.path.join(root, "tm_state.json")] + glob.glob(
        os.path.join(esc, "saves", "tm_quick_*")
    ):
        if os.path.isfile(f):
            try:
                os.remove(f)
                removed += 1
            except OSError:
                pass
    return removed


def deploy(i):
    """Разложить меню в game_{i} по манифесту (печатает статус).

    Явные проверки до записи дают точное сообщение по каждой причине
    (нет движка / нет data / нет папки игры), а не одно общее «запусти gen».
    """
    if i not in ROOTS:
        report.warn(i, "нет в манифесте (tmkit/games_data.py) — пропуск")
        return
    root = ROOTS[i]
    data = game_data_file(i)
    if not os.path.exists(ENGINE_SRC):
        report.bad(i, f"нет движка ({ENGINE_SRC}) — источник правды пропал")
        return
    if not os.path.isdir(root):
        report.bad(i, f"нет папки игры ({root}) — проверь root в манифесте")
        return
    # data в build/ нет или он отстал от манифеста — пересобрать, а не раскладывать старьё
    if generate.OUT == BUILD and generate.is_stale(i):
        generate.gen(i)
    if not os.path.exists(data):
        report.bad(i, f"нет data (game_{i}) — сначала  python tm.py gen {i}")
        return
    removed = deploy_to(root, data)
    report.info(i, f"deployed -> {root}  (снесено .rpyc: {removed})")


def uninstall(i):
    """Снести меню из game_{i} по манифесту (печатает статус)."""
    if i not in ROOTS:
        report.warn(i, "нет в манифесте — пропуск")
        return
    root = ROOTS[i]
    removed = remove_from(root)
    report.info(i, f"удалено {removed} файлов из {root}")
