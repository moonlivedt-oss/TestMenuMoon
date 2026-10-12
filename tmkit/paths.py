#!/usr/bin/env python3
"""Единственное место со всеми путями тулкита.

Раньше пути (build/, D:/_ta, D:/_ta/cand, расположение движка и games_data)
были захардкожены в каждом скрипте по-своему. Теперь — здесь.
"""
import os

_PKG = os.path.dirname(os.path.abspath(__file__))
# Корень проекта = папка НАД пакетом tmkit/
ROOT = os.path.dirname(_PKG)

# Данные манифеста живут внутри пакета (генерируются manifest.save_games).
GAMES_DATA_PATH = os.path.join(_PKG, "games_data.py")

# Канонический движок — источник правды; deploy копирует ИМЕННО его.
ENGINE_SRC = os.path.join(ROOT, "zzz_testmenu_engine.rpy")
# Модуль перевода реплик через AutoTranslator (необязателен: нет файла — не кладём).
TRANSLATE_SRC = os.path.join(ROOT, "zzz_testmenu_translate.rpy")

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
