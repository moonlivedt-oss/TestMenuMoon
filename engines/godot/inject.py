#!/usr/bin/env python3
"""Поставить/снять тест-меню в игре на Godot 4 или 3 — без перепаковки .pck.

Godot при старте читает override.cfg рядом с .exe. Туда добавляется автозагрузка
TestMenu с абсолютным путём к tm_godot/tm_menu.gd (относительный путь Godot считает от
текущей папки процесса, а не от .exe — при запуске ярлыком меню бы не нашлось).
В tm_godot/ кладутся скрипт меню, словарь имён (tm_words.json, из движка Ren'Py) и значки.

Свой override.cfg у игры сохраняется (override.cfg.tm_bak) и дополняется одной строкой;
снятие возвращает его как было. Перенёс папку игры — переустанови меню (студия покажет
«устарело»).

Использование:
    python inject.py <папка игры | .exe | .pck>
    python inject.py <...> --remove
"""

import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "_shared"))
import tm_load  # noqa: E402

tm_load.use_tmkit()
pckmod = tm_load.load("godot", "pck.py")

MENU_SRC = os.path.join(HERE, "tm_menu.gd")  # Godot 4 (GDScript 2)
MENU_SRC3 = os.path.join(HERE, "tm_menu3.gd")  # Godot 3 (GDScript 1), меню попроще
ICONS_SRC = os.path.join(ROOT, "assets", "tm_ui", "ic")
DIRNAME = "tm_godot"
CFG = "override.cfg"
KEY = "TestMenu"
MARK = "; TestMenuMoon"  # строка-метка над нашей записью
OLD_MARKS = ("; RenpyTestMenu",)  # прежнее имя проекта: такие записи тоже наши


def game_dir(path):
    """Папка игры Godot (где .exe и .pck) или ValueError."""
    d = os.path.dirname(path) if os.path.isfile(path) else path
    if not os.path.isdir(d):
        raise ValueError(f"нет такой папки: {path}")
    pack = pckmod.find_pack(d)
    if pack is None:
        raise ValueError(
            f"не похоже на игру Godot (нет .pck или пакета в .exe): {path}"
        )
    return d


def godot_version(path):
    try:
        return pckmod.Pck(pckmod.find_pack(game_dir(path))).version
    except (pckmod.PckError, ValueError, OSError):
        return None


def menu_src(version):
    """Исходник меню под версию движка: Godot 3 — своё меню на GDScript 1."""
    return MENU_SRC3 if version and version[0] == 3 else MENU_SRC


def _words_json():
    from tmkit import naming

    return naming.words_json()


def _menu_path(d):
    # realpath: длинные имена вместо 8.3 (MOONLI~1) — путь как его видит пользователь
    return os.path.join(os.path.realpath(d), DIRNAME, "tm_menu.gd").replace("\\", "/")


def _entry(d):
    return f'{MARK}\n{KEY}="*{_menu_path(d)}"\n'


def _strip_ours(text):
    for m in (MARK,) + OLD_MARKS:
        text = re.sub(
            r"(?m)^" + re.escape(m) + r"\n" + KEY + r'="[^"\n]*"\n?', "", text
        )
    return text


def _add_autoload(text, entry):
    text = _strip_ours(text)
    m = re.search(r"(?m)^\[autoload\]\s*\n", text)
    if m:
        return text[: m.end()] + entry + text[m.end() :]
    sep = "" if (not text or text.endswith("\n")) else "\n"
    return text + sep + ("\n" if text.strip() else "") + "[autoload]\n\n" + entry


def deploy_file(path):
    d = game_dir(path)
    v = godot_version(d)
    if v and v[0] < 3:
        raise ValueError(f"Godot {'.'.join(map(str, v))}: меню есть для Godot 3 и 4")
    out = os.path.join(d, DIRNAME)
    os.makedirs(os.path.join(out, "ic"), exist_ok=True)
    shutil.copy2(menu_src(v), os.path.join(out, "tm_menu.gd"))
    with open(os.path.join(out, "tm_words.json"), "w", encoding="utf-8") as f:
        f.write(_words_json())
    if os.path.isdir(ICONS_SRC):
        for fn in os.listdir(ICONS_SRC):
            if fn.endswith(".png"):
                shutil.copy2(os.path.join(ICONS_SRC, fn), os.path.join(out, "ic", fn))
    cfg = os.path.join(d, CFG)
    old = ""
    if os.path.exists(cfg):
        with open(cfg, encoding="utf-8") as f:
            old = f.read()
        if not any(m in old for m in (MARK,) + OLD_MARKS) and not os.path.exists(
            cfg + ".tm_bak"
        ):
            shutil.copy2(cfg, cfg + ".tm_bak")
    with open(cfg, "w", encoding="utf-8", newline="\n") as f:
        f.write(_add_autoload(old, _entry(d)))
    ver = ".".join(map(str, v)) if v else "?"
    return f"{d}: меню установлено (Godot {ver}, в игре Shift+T / F9)"


def remove_file(path):
    d = game_dir(path)
    cfg = os.path.join(d, CFG)
    done = []
    if os.path.exists(cfg + ".tm_bak"):
        os.replace(cfg + ".tm_bak", cfg)
        done.append("override.cfg восстановлен")
    elif os.path.exists(cfg):
        with open(cfg, encoding="utf-8") as f:
            text = f.read()
        rest = _strip_ours(text)
        if re.sub(r"\[autoload\]|\s", "", rest) == "":
            os.remove(cfg)  # файл был только наш
            done.append("override.cfg удалён")
        elif rest != text:
            with open(cfg, "w", encoding="utf-8", newline="\n") as f:
                f.write(rest)
            done.append("строка меню убрана из override.cfg")
    if os.path.isdir(os.path.join(d, DIRNAME)):
        shutil.rmtree(os.path.join(d, DIRNAME))
        done.append(DIRNAME + "/")
    return f"{d}: меню убрано ({', '.join(done) or 'нечего убирать'})"


def is_installed(path):
    try:
        d = game_dir(path)
        with open(os.path.join(d, CFG), encoding="utf-8") as f:
            t = f.read()
            return any(m in t for m in (MARK,) + OLD_MARKS)
    except (ValueError, OSError):
        return False


def is_current(path):
    """Установлено, путь совпадает с текущим местом игры и файлы меню свежие."""
    try:
        d = game_dir(path)
        with open(os.path.join(d, CFG), encoding="utf-8") as f:
            if _entry(d) not in f.read():
                return False
        with (
            open(os.path.join(d, DIRNAME, "tm_menu.gd"), "rb") as a,
            open(menu_src(godot_version(d)), "rb") as b,
        ):
            if a.read() != b.read():
                return False
        with open(os.path.join(d, DIRNAME, "tm_words.json"), encoding="utf-8") as f:
            return f.read() == _words_json()
    except (ValueError, OSError):
        return False


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("target", help="папка игры, её .exe или .pck")
    ap.add_argument("--remove", action="store_true", help="убрать меню")
    a = ap.parse_args()
    print(remove_file(a.target) if a.remove else deploy_file(a.target))
