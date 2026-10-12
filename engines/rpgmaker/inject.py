#!/usr/bin/env python3
"""Внедрить/убрать тест-меню в RPG Maker MV/MZ игру.

Основной способ — штатный плагин: файл js/plugins/TM_Menu.js + строка в js/plugins.js
(так подключает плагины сам редактор MV/MZ). index.html не трогается, поэтому способ
работает и там, где index.html лежит не в корне.

Игра упакована в package.nw (zip рядом с Game.exe): архив переименовывается в
package.nw.tm_bak и распаковывается в папку package.nw — NW.js принимает и папку,
и архив. Сохранения после этого пишутся внутрь папки, поэтому при снятии меню она
остаётся (убирается только плагин).

Запасной способ (нет js/plugins.js — демо, нестандартные сборки): <script>-блок
в index.html перед </body>, помеченный маркерами — повтор заменяет, --remove убирает.

Ресурсы, вшитые прямо в .exe (Enigma Virtual Box), недоступны — сначала распаковать.

Использование:
    python inject.py <папка_игры|index.html>
    python inject.py <папка_игры|index.html> --remove
"""

import os, re, sys, json, shutil, zipfile, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
MENU_JS = os.path.join(HERE, "tm_menu.js")  # адаптер движка
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "_shared"))
import tm_htmlio  # noqa: E402  (кодировка HTML игры: BOM / UTF-8 / meta charset)
import tm_webinject  # noqa: E402  (запасной способ: <script>-блок в index.html)

PLUGIN_NAME = "TM_Menu"
PLUGIN_ENTRY = {
    "name": PLUGIN_NAME,
    "status": True,
    "description": "TestMenuMoon: test menu (Shift+T)",
    "parameters": {},
}
PACKAGE = "package.nw"
# где может лежать корень веб-части игры относительно папки с Game.exe
_BASES = ("", "www", PACKAGE, os.path.join(PACKAGE, "www"))
_PLUGINS_ARRAY = re.compile(r"\$plugins\s*=\s*")


def _menu_js():
    """Значки + адаптер движка + общее UI-ядро."""
    return tm_webinject.menu_js(MENU_JS)


def _plugin_js():
    """Текст js/plugins/TM_Menu.js. ASCII: <script src> без charset читается в кодировке
    страницы, а кириллица меню в \\uXXXX от неё не зависит."""
    head = (
        "//=============================================================================\n"
        "// TM_Menu.js - TestMenuMoon (Shift+T). Generated, do not edit.\n"
        "//=============================================================================\n"
        "/*:\n * @plugindesc TestMenuMoon: test menu (Shift+T)\n * @author TestMenuMoon\n */\n"
    )
    return head + tm_htmlio.ascii_js(_menu_js()) + "\n"


# ------------------------------------------------------------------ поиск частей игры
def _folder(path):
    return os.path.dirname(path) if os.path.isfile(path) else path


def web_root(path):
    """Папка с index.html / js/ игры (корень, www/, package.nw/, package.nw/www) или None."""
    base = _folder(path)
    for sub in _BASES:
        d = os.path.join(base, sub) if sub else base
        if os.path.isfile(os.path.join(d, "js", "plugins.js")) or os.path.isfile(
            os.path.join(d, "index.html")
        ):
            return d
    return None


def plugins_js(path):
    """Путь к js/plugins.js игры или None."""
    root = web_root(path)
    p = os.path.join(root, "js", "plugins.js") if root else None
    return p if p and os.path.isfile(p) else None


def target_html(path):
    """Разрешить путь к index.html: сам файл, папка/index.html, www/, package.nw/."""
    if os.path.isfile(path):
        return path
    root = web_root(path)
    if root and os.path.exists(os.path.join(root, "index.html")):
        return os.path.join(root, "index.html")
    raise FileNotFoundError(f"index.html не найден в {path}")


def packed_package(path):
    """package.nw-архив игры (zip-файл) или None."""
    p = os.path.join(_folder(path), PACKAGE)
    return p if os.path.isfile(p) and zipfile.is_zipfile(p) else None


def _zip_name(info):
    """Имя файла в архиве. Без флага UTF-8 zipfile читает имя как cp437, а архиваторы
    японских игр пишут cp932 (или UTF-8 без флага) — тогда ресурсы распаковывались
    с кракозябрами в именах, и игра их не находила."""
    if info.flag_bits & 0x800:
        return info.filename
    raw = info.filename.encode("cp437")
    for enc in ("utf-8", "cp932"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return info.filename


def unpack_package(path):
    """package.nw (zip) -> папка package.nw; архив остаётся как package.nw.tm_bak."""
    pkg = packed_package(path)
    if pkg is None:
        return None
    bak = pkg + ".tm_bak"
    if os.path.exists(bak):
        raise FileExistsError(f"{bak} уже есть — разберись с ним вручную")
    os.replace(pkg, bak)
    try:
        with zipfile.ZipFile(bak) as z:
            dest = os.path.abspath(pkg)
            entries = [(_zip_name(i), i) for i in z.infolist()]
            for name, _i in entries:  # без выхода за пределы папки (../)
                if not os.path.abspath(os.path.join(dest, name)).startswith(
                    dest + os.sep
                ):
                    raise ValueError(f"подозрительный путь в архиве: {name}")
            for name, info in entries:
                out = os.path.join(dest, name)
                if name.endswith(("/", "\\")):
                    os.makedirs(out, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with z.open(info) as src, open(out, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    except Exception:
        shutil.rmtree(pkg, ignore_errors=True)
        os.replace(bak, pkg)
        raise
    return pkg


# ------------------------------------------------------------------ plugins.js
def _parse_plugins(text):
    """(начало, конец, список) массива $plugins в тексте plugins.js."""
    m = _PLUGINS_ARRAY.search(text)
    if not m:
        raise ValueError("в plugins.js нет $plugins = [...]")
    arr, end = json.JSONDecoder().raw_decode(text, m.end())
    if not isinstance(arr, list):
        raise ValueError("$plugins — не массив")
    return m.end(), end, arr


def _dump_plugins(arr):
    # формат редактора MV/MZ: по объекту на строку, без пробелов
    rows = [json.dumps(p, ensure_ascii=False, separators=(",", ":")) for p in arr]
    return "[\n" + ",\n".join(rows) + "\n]"


def _edit_plugins(path, fn):
    """Прочитать plugins.js, применить fn(список) -> список, записать, если изменилось."""
    text, enc = tm_htmlio.read(path)
    start, end, arr = _parse_plugins(text)
    new = fn(list(arr))
    if new == arr:
        return False
    out = text[:start] + _dump_plugins(new) + text[end:]
    _parse_plugins(out)  # страховка: результат снова разбирается
    tm_htmlio.write(path, out, enc)
    return True


def _with_plugin(arr):
    arr = [p for p in arr if not (isinstance(p, dict) and p.get("name") == PLUGIN_NAME)]
    return arr + [dict(PLUGIN_ENTRY)]  # последним: игра и её плагины уже загружены


def _without_plugin(arr):
    return [
        p for p in arr if not (isinstance(p, dict) and p.get("name") == PLUGIN_NAME)
    ]


def _plugin_entry_ok(path):
    try:
        arr = _parse_plugins(tm_htmlio.read(path)[0])[2]
    except (OSError, ValueError):
        return False
    return any(
        isinstance(p, dict) and p.get("name") == PLUGIN_NAME and p.get("status")
        for p in arr
    )


def _plugin_file(pjs):
    return os.path.join(os.path.dirname(pjs), "plugins", PLUGIN_NAME + ".js")


# ------------------------------------------------------------------ index.html (запасной)
MENU = tm_webinject.HtmlMenu(MENU_JS, "TM_RPGM_MENU", target_html)
MARK_START, MARK_END = MENU.start, MENU.end
inject, remove, block = MENU.inject, MENU.remove, MENU.block
_html_has_block = MENU.has_block


def _drop_html_block(path):
    """Убрать <script>-блок из index.html, если он там есть (переход на плагин / снятие)."""
    return MENU.undeploy(path) is not None


# ------------------------------------------------------------------ API
def deploy_file(path):
    note = ""
    if plugins_js(path) is None and web_root(path) is None and packed_package(path):
        unpack_package(path)
        note = f" (package.nw распакован, архив: {PACKAGE}.tm_bak)"
    pjs = plugins_js(path)
    if pjs is not None:
        if not os.path.exists(pjs + ".tm_bak"):
            shutil.copy2(pjs, pjs + ".tm_bak")
        pf = _plugin_file(pjs)
        os.makedirs(os.path.dirname(pf), exist_ok=True)
        with open(pf, "w", encoding="utf-8", newline="\n") as f:
            f.write(_plugin_js())
        _edit_plugins(pjs, _with_plugin)
        _drop_html_block(
            path
        )  # старая установка <script>-ом — иначе меню было бы два раза
        return f"{pf}: меню подключено плагином (Shift+T в игре){note}"
    try:
        html = target_html(path)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"не нашёл ни js/plugins.js, ни index.html, ни package.nw в {path} "
            "(ресурсы вшиты в .exe? сначала распакуй, например EnigmaVBUnpacker)"
        ) from None
    MENU.deploy(html)
    return f"{html}: меню внедрено в index.html (Shift+T в игре){note}"


def remove_file(path):
    done = []
    pjs = plugins_js(path)
    if pjs is not None:
        if _edit_plugins(pjs, _without_plugin):
            done.append("plugins.js")
        pf = _plugin_file(pjs)
        if os.path.exists(pf):
            os.remove(pf)
            done.append(os.path.basename(pf))
    if _drop_html_block(path):
        done.append("index.html")
    where = web_root(path) or path
    return f"{where}: меню убрано ({', '.join(done) or 'нечего убирать'})"


def is_installed(path):
    """Есть ли меню: плагин в plugins.js или блок в index.html. Терпимо к отсутствию файлов."""
    pjs = plugins_js(path)
    if pjs is not None and _plugin_entry_ok(pjs):
        return True
    return _html_has_block(path)


def is_current(path):
    """Установленное меню совпадает с текущими адаптером + ядром (иначе пора обновить)."""
    pjs = plugins_js(path)
    if pjs is not None:
        pf = _plugin_file(pjs)
        try:
            with open(pf, encoding="utf-8", newline="") as f:
                same = f.read() == _plugin_js()
        except OSError:
            return False
        return same and _plugin_entry_ok(pjs) and not _html_has_block(path)
    return MENU.is_current(path)


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("target", help="папка игры или index.html")
    p.add_argument("--remove", action="store_true", help="убрать меню вместо внедрения")
    args = p.parse_args()
    print(remove_file(args.target) if args.remove else deploy_file(args.target))
