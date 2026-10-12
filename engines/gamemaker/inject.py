#!/usr/bin/env python3
"""Поставить/снять тест-меню в игре на GameMaker 2.3+ (data.win) через UndertaleModTool CLI.

Меню — объект obj_tm_menu на GML (menu_*.gml: глобальные переменные с правкой и заморозкой,
список комнат с переходом, темп игры), его в data.win кладёт скрипт TestMenu.csx. Оригинал
один раз копируется в data.win.tm_bak, и меню всегда собирается из него — переустановка не
копит слои. Снятие возвращает оригинал. UTMT CLI скачивает tools/fetch_unity_tools.py UTMT_CLI.

В игре: Shift+T / F9 — меню, Tab — страница (глобальные / комнаты / игра), стрелки, Enter, F.
Текст меню — по-английски: у шрифта GameMaker по умолчанию нет кириллицы.

Использование:
    python inject.py <папка игры | .exe | data.win>
    python inject.py <...> --remove
"""

import argparse
import glob
import hashlib
import os
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
UTMT = os.path.join(ROOT, "tools", "unity", "UTMT_CLI")
DATA = "data.win"
BAK = DATA + ".tm_bak"
MARK = "tm_gamemaker.txt"  # подпись установленной версии меню
PARTS = ("TestMenu.csx", "menu_create.gml", "menu_step.gml", "menu_draw.gml")


def game_dir(path):
    """Папка игры с data.win или ValueError."""
    d = os.path.dirname(path) if os.path.isfile(path) else path
    if not os.path.isfile(os.path.join(d, DATA)):
        raise ValueError(f"не похоже на игру GameMaker (нет {DATA}): {path}")
    return d


def is_gamemaker(path):
    try:
        game_dir(path)
        return True
    except ValueError:
        return False


def cli_path():
    hits = glob.glob(os.path.join(UTMT, "**", "UndertaleModCli.exe"), recursive=True)
    return hits[0] if hits else None


def _read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def script_text():
    """TestMenu.csx с подставленным GML (в C#-строке @"…" кавычка удваивается)."""
    csx = _read("TestMenu.csx")
    for key, fn in (("%CREATE%", "menu_create.gml"), ("%STEP%", "menu_step.gml"), ("%DRAW%", "menu_draw.gml")):
        csx = csx.replace(key, _read(fn).replace('"', '""'))
    return csx


def signature():
    return hashlib.sha1("".join(_read(p) for p in PARTS).encode("utf-8")).hexdigest()


def deploy_file(path):
    d = game_dir(path)
    cli = cli_path()
    if cli is None:
        raise FileNotFoundError("нет UndertaleModTool CLI — запусти tools/fetch_unity_tools.py UTMT_CLI")
    data, bak = os.path.join(d, DATA), os.path.join(d, BAK)
    if not os.path.exists(bak):
        shutil.copy2(data, bak)
    tmp = tempfile.mkdtemp(prefix="tm_gm_")
    try:
        csx = os.path.join(tmp, "TestMenu.csx")
        with open(csx, "w", encoding="utf-8") as f:
            f.write(script_text())
        out = os.path.join(tmp, DATA)
        r = subprocess.run([cli, "load", bak, "-s", csx, "-o", out, "-f"], capture_output=True, timeout=600)
        log = (r.stdout + r.stderr).decode("utf-8", "replace")
        if r.returncode != 0 or not os.path.isfile(out) or "TestMenuMoon:" in log:
            reason = next((ln.strip() for ln in log.splitlines() if "TestMenuMoon:" in ln), "")
            raise ValueError("UTMT не собрал data.win: " + (reason or log.strip()[-400:]))
        shutil.copyfile(out, data)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with open(os.path.join(d, MARK), "w", encoding="utf-8") as f:
        f.write(signature())
    return f"{d}: меню внедрено в data.win (оригинал: {BAK}). В игре: Shift+T / F9"


def remove_file(path):
    d = game_dir(path)
    bak = os.path.join(d, BAK)
    if not os.path.exists(bak):
        return f"{d}: меню не ставилось (нет {BAK})"
    os.replace(bak, os.path.join(d, DATA))
    if os.path.exists(os.path.join(d, MARK)):
        os.remove(os.path.join(d, MARK))
    return f"{d}: data.win возвращён как был"


def is_installed(path):
    try:
        d = game_dir(path)
    except ValueError:
        return False
    return os.path.exists(os.path.join(d, BAK)) and os.path.exists(os.path.join(d, MARK))


def is_current(path):
    try:
        with open(os.path.join(game_dir(path), MARK), encoding="utf-8") as f:
            return f.read().strip() == signature()
    except (ValueError, OSError):
        return False


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="папка игры, её .exe или data.win")
    ap.add_argument("--remove", action="store_true")
    a = ap.parse_args()
    print(remove_file(a.target) if a.remove else deploy_file(a.target))
