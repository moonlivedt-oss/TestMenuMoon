"""tmstudio — GUI-студия тулкита TestMenuMoon (PyQt6).

  theme       — палитра, QSS, значки, мелкие помощники;
  tabs        — вкладки карточки игры (Обзор, Характеристики/Действия, Кандидаты);
  window      — главное окно: список игр, лог, очередь команд tm.py;
  library     — библиотека игр: папка целиком, движок и статус каждой игры, установка пачкой;
  tour        — обучение (пошаговый тур с подсветкой кнопок);
  save_editor — редактор сохранений (форматы — tmkit/saves.py).

Запуск: python studio.py (или Запуск.bat).
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
