#!/usr/bin/env python3
"""Внедрить/убрать тест-меню в любую HTML5-игру (Phaser, Construct 2, GDevelop, свой движок).

Тот же блок <script> перед </body>, что и у Twine (engines/_shared/tm_webinject.py), но
с адаптером engines/web/tm_menu.js и своими маркерами. Цель — папка игры
(index.html в приоритете) или сам .html. Оригинал HTML один раз копируется в .tm_bak.
Упакованный package.nw (zip рядом с .exe nw.js) сначала распаковывается в папку.

Использование:
    python inject.py <папка или .html>            внедрить/обновить меню
    python inject.py <папка или .html> --remove   убрать меню
"""

import argparse
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "_shared"))
import tm_load  # noqa: E402
import tm_webinject  # noqa: E402

MENU_JS = os.path.join(HERE, "tm_menu.js")  # адаптер движка
_SUBDIRS = ("", "www", "package.nw", "app")  # где nw.js-сборки держат index.html


def target_html(path):
    """Папка -> index.html (в корне, www/, package.nw/, app/), иначе крупнейший .html."""
    if os.path.isfile(path):
        return path
    for sub in _SUBDIRS:
        p = os.path.join(path, sub, "index.html")
        if os.path.isfile(p):
            return p
    htmls = glob.glob(os.path.join(glob.escape(path), "*.html"))
    if htmls:
        return max(htmls, key=os.path.getsize)
    raise FileNotFoundError(f"HTML игры не найден: {path}")


MENU = tm_webinject.HtmlMenu(MENU_JS, "TM_WEB_MENU", target_html)
MARK_START, MARK_END = MENU.start, MENU.end
inject, remove, block = MENU.inject, MENU.remove, MENU.block
_menu_js = MENU.js


def deploy_file(path):
    note = ""
    if os.path.isdir(path):
        try:
            target_html(path)
        except FileNotFoundError:
            # nw.js-игра с упакованным package.nw: распаковать (как у RPG Maker)
            if tm_load.load("rpgmaker").unpack_package(path):
                note = " (package.nw распакован, архив: package.nw.tm_bak)"
    return f"{MENU.deploy(path)}: меню внедрено (Shift+T в игре){note}"


def remove_file(path):
    html = MENU.undeploy(path)
    return f"{html}: меню убрано" if html else f"{target_html(path)}: меню не было"


is_installed = MENU.is_installed
is_current = MENU.is_current


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("path", help="папка HTML5-игры или её .html")
    p.add_argument("--remove", action="store_true", help="убрать меню вместо внедрения")
    a = p.parse_args()
    print(remove_file(a.path) if a.remove else deploy_file(a.path))
