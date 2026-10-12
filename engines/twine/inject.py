#!/usr/bin/env python3
"""Внедрить/убрать тест-меню в HTML-файл Twine-игры (PoC для SugarCube).

Меню (tm_menu.js) вставляется блоком перед </body>, помеченным маркерами —
поэтому повторное внедрение заменяет старую версию, а --remove убирает начисто.

Использование:
    python inject.py <game.html>            внедрить/обновить меню
    python inject.py <game.html> --remove   убрать меню
"""

import os, re, sys, glob, shutil, argparse

MARK_START = "<!-- TM_TWINE_MENU_START -->"
MARK_END = "<!-- TM_TWINE_MENU_END -->"
HERE = os.path.dirname(os.path.abspath(__file__))
MENU_JS = os.path.join(HERE, "tm_menu.js")  # адаптер движка
CORE_JS = os.path.normpath(
    os.path.join(HERE, "..", "_shared", "tm_menu_core.js")
)  # общий UI
ICONS_JS = os.path.normpath(
    os.path.join(HERE, "..", "_shared", "tm_icons.js")
)  # значки (data-URI), tools/make_icons.py
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "_shared")))
import tm_htmlio  # noqa: E402  (кодировка HTML игры: BOM / UTF-8 / meta charset)


def _menu_js():
    """Адаптер движка + общее UI-ядро (в порядке: сначала адаптер, потом ядро)."""
    icons = _read(ICONS_JS) if os.path.exists(ICONS_JS) else ""
    return icons + "\n" + _read(MENU_JS) + "\n" + _read(CORE_JS)


def block(js):
    return f"\n{MARK_START}\n<script>\n{js}\n</script>\n{MARK_END}\n"


def remove(html):
    """Убрать ранее внедрённый блок меню (если он есть)."""
    # вместе с обрамляющими \n блока: иначе каждый повторный деплой копил пустую строку
    pattern = r"\n?" + re.escape(MARK_START) + r".*?" + re.escape(MARK_END) + r"\n?"
    return re.sub(pattern, "", html, flags=re.S)


def inject(html, js):
    """Вставить (или заменить) блок меню перед последним </body>. Идемпотентно."""
    if MARK_START in html:
        html = remove(html)
    b = block(js)
    idx = html.lower().rfind("</body>")
    if idx == -1:
        return html + b  # нет </body> — просто дописываем в конец
    return html[:idx] + b + html[idx:]


def _read(path):
    """Исходники меню (наши .js) — всегда UTF-8."""
    # newline="": не трогаем концы строк (иначе LF-файл целиком уезжал в CRLF)
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _read_html(path):
    """HTML игры в её кодировке: (текст, кодировка)."""
    return tm_htmlio.read(path)


def _write(path, text, enc="utf-8"):
    tm_htmlio.write(path, text, enc)


def _backup(path):
    """Один раз сохранить нетронутый оригинал рядом (<файл>.tm_bak) — до первой правки."""
    bak = path + ".tm_bak"
    if not os.path.exists(bak) and MARK_START not in _read_html(path)[0]:
        shutil.copy2(path, bak)


def target_html(path):
    """Разрешить путь к HTML: сам .html или папка (крупнейший *.html — история, не заглушка)."""
    if os.path.isfile(path):
        return path
    htmls = glob.glob(os.path.join(glob.escape(path), "*.html"))
    if htmls:
        return max(htmls, key=os.path.getsize)
    raise FileNotFoundError(f"HTML Twine-игры не найден: {path}")


def deploy_file(path):
    """Внедрить/обновить меню в HTML (принимает .html или папку с ним). Возвращает сообщение."""
    html = target_html(path)
    _backup(html)
    text, enc = _read_html(html)
    _write(html, inject(text, tm_htmlio.js_for(enc, _menu_js())), enc)
    return f"{html}: меню внедрено (Shift+T в игре)"


def remove_file(path):
    """Убрать меню из HTML (принимает .html или папку с ним). Возвращает сообщение."""
    html = target_html(path)
    text, enc = _read_html(html)
    _write(html, remove(text), enc)
    return f"{html}: меню убрано"


def is_installed(path):
    """Есть ли уже внедрённое меню (по маркеру). Терпимо к отсутствию файла."""
    try:
        return MARK_START in _read_html(target_html(path))[0]
    except (FileNotFoundError, OSError):
        return False


def is_current(path):
    """Внедрённое меню совпадает с текущими адаптером + ядром (иначе пора обновить)."""
    try:
        text, enc = _read_html(target_html(path))
        return block(tm_htmlio.js_for(enc, _menu_js())) in text
    except (FileNotFoundError, OSError):
        return False


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("html", help="путь к HTML-файлу Twine-игры")
    p.add_argument("--remove", action="store_true", help="убрать меню вместо внедрения")
    args = p.parse_args()

    print(remove_file(args.html) if args.remove else deploy_file(args.html))
