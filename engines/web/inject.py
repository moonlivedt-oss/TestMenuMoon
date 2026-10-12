#!/usr/bin/env python3
"""Внедрить/убрать тест-меню в любую HTML5-игру (Phaser, Construct 2, GDevelop, свой движок).

Тот же блок <script> перед </body>, что и у Twine (engines/twine/inject.py), но
с адаптером engines/web/tm_menu.js и своими маркерами. Цель — папка игры
(index.html в приоритете) или сам .html. Оригинал HTML один раз копируется в .tm_bak.

Использование:
    python inject.py <папка или .html>            внедрить/обновить меню
    python inject.py <папка или .html> --remove   убрать меню
"""

import os, sys, glob, argparse, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))


def _twine_base():
    # отдельный экземпляр модуля Twine: подменяем адаптер и маркеры, логику берём как есть
    path = os.path.join(HERE, "..", "twine", "inject.py")
    spec = importlib.util.spec_from_file_location("tm_web_base_inject", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.MENU_JS = os.path.join(HERE, "tm_menu.js")
    m.MARK_START = "<!-- TM_WEB_MENU_START -->"
    m.MARK_END = "<!-- TM_WEB_MENU_END -->"
    m.target_html = target_html
    return m


def target_html(path):
    """Папка -> index.html (у nw.js-сборок бывает в www/ или package.nw/), иначе крупнейший .html."""
    if os.path.isfile(path):
        return path
    for sub in ("", "www", "package.nw", "app"):
        p = os.path.join(path, sub, "index.html")
        if os.path.isfile(p):
            return p
    htmls = glob.glob(os.path.join(glob.escape(path), "*.html"))
    if htmls:
        return max(htmls, key=os.path.getsize)
    raise FileNotFoundError(f"HTML игры не найден: {path}")


_B = _twine_base()
MARK_START, MARK_END = _B.MARK_START, _B.MARK_END
inject, remove = _B.inject, _B.remove


def deploy_file(path):
    return _B.deploy_file(path)


def remove_file(path):
    return _B.remove_file(path)


def is_installed(path):
    return _B.is_installed(path)


def is_current(path):
    return _B.is_current(path)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", help="папка HTML5-игры или её .html")
    p.add_argument("--remove", action="store_true", help="убрать меню вместо внедрения")
    a = p.parse_args()
    print(remove_file(a.path) if a.remove else deploy_file(a.path))
