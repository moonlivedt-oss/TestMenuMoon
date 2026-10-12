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

# Свой манифест (tmkit/games_data.py) — личный и в git не идёт. Свежий клон получает
# копию примера с тестовыми играми (tmkit/games_example.py), дальше правит студия.
_here = _os.path.dirname(_os.path.abspath(__file__))
if not _os.path.exists(_os.path.join(_here, "games_data.py")):
    _shutil.copyfile(_os.path.join(_here, "games_example.py"), _os.path.join(_here, "games_data.py"))
