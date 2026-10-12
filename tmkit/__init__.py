"""tmkit — библиотека тулкита TestMenuMoon.

Вся логика CLI (tm.py) и студии (tmstudio/). Здесь нет ни argparse, ни Qt.

  paths      — все пути в одном месте;
  games_data — данные манифеста (личные, не в git; при первом запуске — копия games_example);
  manifest   — чтение/запись манифеста + add/remove игр;
  games      — ROOTS и автопоиск лаунчера/python из манифеста;
  engines    — реестр движков (Ren'Py, RPG Maker, HTML5, Twine, Godot, Unity, Unreal);
  rpa        — распаковка .rpa-архивов;
  collect    — подготовка исходников игры для анализа (tm.py collect);
  analysis   — поиск кандидатов статов/инвентаря (tm.py curate);
  generate   — рендер per-game data-файлов (tm.py gen);
  validate   — офлайн-проверка данных манифеста (tm.py validate);
  deploy     — разложить/снести меню в game/ (tm.py deploy / uninstall);
  verify     — проверка установки + Ren'Py lint (tm.py verify);
  report     — единый формат вывода CLI;
  saves      — форматы сохранений (редактор сейвов);
  naming     — понятные имена переменных (словарь — из движка Ren'Py);
  lzstring   — порт lz-string (сейвы RPG Maker MV).
"""

import os as _os
import shutil as _shutil

from tmkit.paths import GAMES_DATA_PATH as _DATA, GAMES_EXAMPLE_PATH as _EXAMPLE

# Свой манифест (tmkit/games_data.py) — личный и в git не идёт. Свежий клон получает
# копию примера с тестовыми играми (tmkit/games_example.py), дальше правит студия.
if not _os.path.exists(_DATA) and _os.path.exists(_EXAMPLE):
    _shutil.copyfile(_EXAMPLE, _DATA)
