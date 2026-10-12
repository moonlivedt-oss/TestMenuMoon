#!/usr/bin/env python3
"""Единственное место со всеми путями тулкита.

Раньше пути (build/, D:/_ta, D:/_ta/cand, расположение движка и games_data)
были захардкожены в каждом скрипте по-своему. Теперь — здесь.
"""
import os
import sys

_PKG = os.path.dirname(os.path.abspath(__file__))
# Собранная студия (TestMenuStudio.exe, tools/build_exe.py): код внутри .exe, а всё, что
# правится и ставится в игры (манифест, engines/, assets/, tools/), — рядом с .exe.
FROZEN = bool(getattr(sys, "frozen", False))
# Корень проекта = папка НАД пакетом tmkit/ (у .exe — папка самого .exe)
ROOT = os.path.dirname(os.path.abspath(sys.executable)) if FROZEN else os.path.dirname(_PKG)

# Данные манифеста — файл на диске (не модуль): manifest.load_games читает его заново.
GAMES_DATA_PATH = os.path.join(ROOT, "tmkit", "games_data.py")
GAMES_EXAMPLE_PATH = os.path.join(ROOT, "tmkit", "games_example.py")


def python_cmd(script, *args):
    """Команда «запустить Python-скрипт»: у .exe — он сам в режиме --py (Python внутри)."""
    if FROZEN:
        return [sys.executable, "--py", script, *args]
    return [sys.executable, script, *args]

# Меню для Ren'Py — источник правды. Исходник разбит на части по разделам
# (engines/renpy/engine/NN_*.rpy); в игру ставится их склейка одним файлом
# zzz_testmenu_engine.rpy (см. read_source). ENGINE_SRC может быть и одним файлом (тесты).
RENPY_DIR = os.path.join(ROOT, "engines", "renpy")
ENGINE_SRC = os.path.join(RENPY_DIR, "engine")
# Модуль перевода реплик через AutoTranslator (необязателен: нет файла — не кладём).
TRANSLATE_SRC = os.path.join(RENPY_DIR, "zzz_testmenu_translate.rpy")

# Твики отдельных игр (поле "tweak" в манифесте): код Ren'Py, который generate дописывает
# в data-файл игры — ставится и снимается вместе с меню.
TWEAKS_DIR = os.path.join(ROOT, "tweaks")

# Вендоренный декомпилятор.
UNRPYC = os.path.join(ROOT, "unrpyc", "unrpyc.py")


def _env(name, default):
    """Значение переменной окружения name или default (пустая строка = default)."""
    v = os.environ.get(name)
    return v if v else default


# --- переопределяемые пути (env-оверрайд — чтобы пережить смену диска/машины) ---
# Куда generate кладёт per-game data-файлы.               TM_BUILD
BUILD = _env("TM_BUILD", os.path.join(ROOT, "build"))
# Рабочая зона анализа. Короткий путь — под Windows MAX_PATH (260).   TM_ANA_BASE
ANA_BASE = _env("TM_ANA_BASE", "D:/_ta" if os.path.isdir("D:/_ta") else os.path.join(ROOT, "_ta"))
# Файлы кандидатов. По умолчанию — рядом с распаковкой.    TM_CAND_DIR
CAND_DIR = _env("TM_CAND_DIR", ANA_BASE + "/cand")


def ana_dir(i):
    """Папка с распакованными исходниками игры N."""
    return f"{ANA_BASE}/game_{i}"


def cand_file(i):
    """Файл кандидатов игры N."""
    return f"{CAND_DIR}/game_{i}.txt"


def game_data_file(i):
    """Собранный data-файл игры N в build/."""
    return os.path.join(BUILD, f"game_{i}", "zzz_testmenu_data.rpy")


def source_parts(path):
    """Файлы источника по порядку: части папки (NN_*.rpy) или сам файл."""
    if os.path.isdir(path):
        return [
            os.path.join(path, n) for n in sorted(os.listdir(path)) if n.endswith(".rpy")
        ]
    return [path]


def source_stamp(path):
    """Ключ для кэшей: (имя, mtime, размер) каждой части; None — источника нет."""
    try:
        return tuple(
            (p, os.stat(p).st_mtime_ns, os.stat(p).st_size) for p in source_parts(path)
        ) or None
    except OSError:
        return None


def read_source(path):
    """Текст источника: склейка частей по порядку (концы строк как в файлах).
    OSError — источника нет."""
    parts = source_parts(path)
    if not parts:
        raise FileNotFoundError(path)
    out = []
    for p in parts:
        with open(p, encoding="utf-8", newline="") as f:
            out.append(f.read())
    return "".join(out)
