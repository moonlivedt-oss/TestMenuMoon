#!/usr/bin/env python3
"""Внедрить/убрать тест-меню в HTML-файл Twine-игры (SugarCube).

Меню (адаптер tm_menu.js + общее ядро) вставляется блоком перед </body> между маркерами
(engines/_shared/tm_webinject.py): повтор заменяет старую версию, --remove убирает начисто.

Использование:
    python inject.py <game.html | папка>            внедрить/обновить меню
    python inject.py <game.html | папка> --remove   убрать меню
"""

import argparse
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "_shared"))
import tm_webinject  # noqa: E402

MENU_JS = os.path.join(HERE, "tm_menu.js")  # адаптер движка


def target_html(path):
    """Сам .html или папка с ним (крупнейший *.html — история, а не заглушка)."""
    if os.path.isfile(path):
        return path
    htmls = glob.glob(os.path.join(glob.escape(path), "*.html"))
    if htmls:
        return max(htmls, key=os.path.getsize)
    raise FileNotFoundError(f"HTML Twine-игры не найден: {path}")


MENU = tm_webinject.HtmlMenu(MENU_JS, "TM_TWINE_MENU", target_html)
MARK_START, MARK_END = MENU.start, MENU.end
inject, remove, block = MENU.inject, MENU.remove, MENU.block
_menu_js = MENU.js


def deploy_file(path):
    return f"{MENU.deploy(path)}: меню внедрено (Shift+T в игре)"


def remove_file(path):
    html = MENU.undeploy(path)
    return f"{html}: меню убрано" if html else f"{target_html(path)}: меню не было"


is_installed = MENU.is_installed
is_current = MENU.is_current


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("html", help="путь к HTML-файлу Twine-игры или папке с ним")
    p.add_argument("--remove", action="store_true", help="убрать меню вместо внедрения")
    args = p.parse_args()
    print(remove_file(args.html) if args.remove else deploy_file(args.html))
