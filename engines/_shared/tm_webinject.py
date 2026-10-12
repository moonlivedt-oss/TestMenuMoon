"""Блок меню <script> в HTML игры — общее для Twine, HTML5 и запасного способа RPG Maker.

Меню (значки + адаптер движка + общее ядро tm_menu_core.js) вставляется перед последним
</body> между маркерами-комментариями: повторная установка заменяет блок, снятие убирает
его начисто. Перед первой правкой оригинал один раз копируется в <файл>.tm_bak. HTML
читается и пишется в своей кодировке (tm_htmlio); для не-UTF страниц скрипт — чистый ASCII.

    MENU = HtmlMenu("tm_menu.js у движка", "TM_TWINE_MENU", find_html)
    MENU.deploy(path) / MENU.undeploy(path) / MENU.is_installed(path) / MENU.is_current(path)
"""

import os
import re
import shutil

import tm_htmlio

SHARED = os.path.dirname(os.path.abspath(__file__))
CORE_JS = os.path.join(SHARED, "tm_menu_core.js")  # общий UI
ICONS_JS = os.path.join(SHARED, "tm_icons.js")  # значки (data-URI), tools/make_icons.py


def read_js(path):
    """Наши .js — всегда UTF-8; newline="": концы строк не трогаем."""
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def menu_js(adapter_js):
    """Значки + адаптер движка + общее ядро (именно в таком порядке)."""
    icons = read_js(ICONS_JS) if os.path.exists(ICONS_JS) else ""
    return icons + "\n" + read_js(adapter_js) + "\n" + read_js(CORE_JS)


class HtmlMenu:
    def __init__(self, adapter_js, mark, find_html):
        self.adapter_js = adapter_js
        self.start = f"<!-- {mark}_START -->"
        self.end = f"<!-- {mark}_END -->"
        self.find_html = find_html  # путь (папка/файл) -> .html или FileNotFoundError

    # ---------------------------------------------------------- текст
    def js(self):
        return menu_js(self.adapter_js)

    def block(self, js):
        return f"\n{self.start}\n<script>\n{js}\n</script>\n{self.end}\n"

    def remove(self, html):
        """Убрать блок меню вместе с обрамляющими \\n (иначе повторы копили пустые строки)."""
        pattern = r"\n?" + re.escape(self.start) + r".*?" + re.escape(self.end) + r"\n?"
        return re.sub(pattern, "", html, flags=re.S)

    def inject(self, html, js):
        """Вставить (или заменить) блок перед последним </body>. Идемпотентно."""
        if self.start in html:
            html = self.remove(html)
        b = self.block(js)
        idx = html.lower().rfind("</body>")
        return html + b if idx == -1 else html[:idx] + b + html[idx:]

    # ---------------------------------------------------------- файлы
    def has_block(self, path):
        try:
            return self.start in tm_htmlio.read(self.find_html(path))[0]
        except OSError:
            return False

    def backup(self, html):
        """Один раз сохранить нетронутый оригинал рядом (<файл>.tm_bak) — до первой правки."""
        bak = html + ".tm_bak"
        if not os.path.exists(bak) and self.start not in tm_htmlio.read(html)[0]:
            shutil.copy2(html, bak)

    def deploy(self, path):
        """Внедрить/обновить меню. -> путь к HTML."""
        html = self.find_html(path)
        self.backup(html)
        text, enc = tm_htmlio.read(html)
        tm_htmlio.write(html, self.inject(text, tm_htmlio.js_for(enc, self.js())), enc)
        return html

    def undeploy(self, path):
        """Убрать блок, если он есть. -> путь к HTML или None (блока не было)."""
        if not self.has_block(path):
            return None
        html = self.find_html(path)
        text, enc = tm_htmlio.read(html)
        tm_htmlio.write(html, self.remove(text), enc)
        return html

    def is_installed(self, path):
        return self.has_block(path)

    def is_current(self, path):
        """Внедрённый блок совпадает с текущими адаптером + ядром (иначе пора обновить)."""
        try:
            text, enc = tm_htmlio.read(self.find_html(path))
        except OSError:
            return False
        return self.block(tm_htmlio.js_for(enc, self.js())) in text
