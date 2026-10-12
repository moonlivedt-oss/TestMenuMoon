"""Загрузка модулей движков по пути: engines/<движок>/<файл>.py.

У каждого движка свои inject.py / scan.py с одинаковыми именами, поэтому обычный
`import inject` через sys.path брал тот модуль, чья папка оказалась в sys.path раньше
(Unity получал инжектор Godot только благодаря порядку вставок). Здесь каждый файл
грузится под своим уникальным именем tm_<движок>_<файл> и кэшируется: студия
опрашивает статус игр часто, а повторное исполнение модуля на каждый вызов — лишняя работа.

    from tm_load import load
    pck = load("godot", "pck.py")
"""

import importlib.util
import os
import sys

ENGINES = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(ENGINES)


def path_of(engine, filename="inject.py"):
    return os.path.join(ENGINES, engine, filename)


def load(engine, filename="inject.py", fresh=False):
    """Модуль engines/<engine>/<filename>. fresh=True — отдельный экземпляр без кэша."""
    stem = os.path.splitext(filename)[0]
    name = f"tm_{engine.strip('_')}_{stem}"
    if not fresh and name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path_of(engine, filename))
    m = importlib.util.module_from_spec(spec)
    if not fresh:
        sys.modules[name] = m
    try:
        spec.loader.exec_module(m)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return m


def use_tmkit():
    """Сделать пакет tmkit импортируемым из скрипта движка, запущенного напрямую."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
