"""tmkit — библиотека тулкита TestMenuMoon.

Переиспользуемая логика, вынесенная из плоских скриптов. Каждая root-обёртка
(deploy.py, gen_data.py, …) — тонкая: разбор argv + вызов функции отсюда.

  paths      — все пути в одном месте;
  games_data — данные манифеста (личные, не в git; при первом запуске — копия games_example);
  manifest   — чтение/запись манифеста + add/remove игр;
  games      — ROOTS и автопоиск лаунчера/python из манифеста;
  engines    — реестр движков (Ren'Py / Twine / RPG Maker) + detect_engine;
  rpa        — распаковка .rpa-архивов;
  collect    — подготовка исходников игры для анализа (ядро collect_sources);
  analysis   — поиск кандидатов статов/инвентаря (ядро curate_dump);
  generate   — рендер per-game data-файлов (ядро gen_data);
  validate   — офлайн-проверка данных манифеста (ядро validate);
  deploy     — разложить/снести меню в game/ (ядро deploy/uninstall);
  verify     — проверка установки + Ren'Py lint (ядро verify);
  report     — единый формат вывода CLI;
  cli        — общий argparse-хелпер для обёрток.

Тонкие CLI-обёртки лежат в корне проекта и запускаются как раньше:
`python deploy.py 3`.
"""

import os as _os
import shutil as _shutil

# Свой манифест (tmkit/games_data.py) — личный и в git не идёт. Свежий клон получает
# копию примера с тестовыми играми (tmkit/games_example.py), дальше правит студия.
_here = _os.path.dirname(_os.path.abspath(__file__))
if not _os.path.exists(_os.path.join(_here, "games_data.py")):
    _shutil.copyfile(_os.path.join(_here, "games_example.py"), _os.path.join(_here, "games_data.py"))
