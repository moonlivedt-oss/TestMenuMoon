#!/usr/bin/env python3
"""Unreal Engine 4/5: поставить/снять UE4SS (загрузчик модов, окно с консолью и Live View)
и наш Lua-мод TestMenu (скорость, бессмертие, полёт, сквозь стены, телепорт, профиль).

UE4SS кладётся рядом с <Проект>-Win64-Shipping.exe (папка <Проект>/Binaries/Win64): dwmapi.dll
загружает UE4SS.dll, тот — моды из Mods/. Файлы берутся из tools/unity/UE4SS
(tools/fetch_unity_tools.py). Всё положенное — в tm_unreal_files.txt рядом с .exe; снятие
убирает ровно это (если у игры уже был свой UE4SS, установка отказывается).

Игры с античитом (EasyAntiCheat, BattlEye и т.п.) не трогаем: инъекция там — бан аккаунта.

Использование:
    python inject.py <папка игры | .exe>
    python inject.py <...> --remove
"""

import argparse
import glob
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
UE4SS = os.path.join(ROOT, "tools", "unity", "UE4SS")
MOD = os.path.join(HERE, "TestMenu")
LIST = "tm_unreal_files.txt"
ANTICHEAT = (
    "EasyAntiCheat",
    "BattlEye",
    "EasyAntiCheat_EOS",
    "AntiCheat",
    "ACE",
    "XIGNCODE",
)
# моды UE4SS, которые нам нужны (остальные встроенные — как в архиве)
ENABLE = {
    "CheatManagerEnablerMod": 1,
    "ConsoleEnablerMod": 1,
    "ConsoleCommandsMod": 1,
    "Keybinds": 1,
    "TestMenu": 1,
}


def shipping_dir(path):
    """Папка с <Проект>-Win64-Shipping.exe (или None)."""
    d = os.path.dirname(path) if os.path.isfile(path) else path
    if not os.path.isdir(d):
        return None
    for pat in (
        "*-Shipping.exe",
        os.path.join("*", "Binaries", "Win64", "*-Shipping.exe"),
        os.path.join("Binaries", "Win64", "*-Shipping.exe"),
    ):
        hits = glob.glob(os.path.join(glob.escape(d), pat))
        if hits:
            return os.path.dirname(hits[0])
    return None


def is_unreal(path):
    d = os.path.dirname(path) if os.path.isfile(path) else path
    if shipping_dir(path):
        return True
    return os.path.isdir(os.path.join(d, "Engine", "Binaries")) and bool(
        glob.glob(os.path.join(glob.escape(d), "*", "Content", "Paks"))
    )


def game_root(win64):
    """<корень игры>: на 3 уровня выше Win64 (<корень>/<Проект>/Binaries/Win64)."""
    return os.path.normpath(os.path.join(win64, "..", "..", ".."))


def anticheat(win64):
    root = game_root(win64)
    for d in (root, os.path.dirname(win64), win64):
        for name in ANTICHEAT:
            if os.path.isdir(os.path.join(d, name)):
                return name
        for f in glob.glob(os.path.join(glob.escape(d), "*")):
            low = os.path.basename(f).lower()
            if low.endswith((".exe", ".sys", ".dll")) and (
                "_eac" in low
                or "_be." in low
                or "battleye" in low
                or "easyanticheat" in low
            ):
                return os.path.basename(f)
    return None


def _mods_txt(text):
    """mods.txt: наши моды включить, TestMenu добавить; порядок и прочее — как было."""
    lines = text.splitlines()
    seen = set()
    out = []
    for ln in lines:
        name = ln.split(":")[0].strip().lstrip("﻿")
        if name in ENABLE and ":" in ln:
            out.append("%s : %d" % (name, ENABLE[name]))
            seen.add(name)
        else:
            out.append(ln)
    if "TestMenu" not in seen:
        # «Keybinds» по правилам UE4SS — последней строкой
        idx = next(
            (i for i, ln in enumerate(out) if ln.split(":")[0].strip() == "Keybinds"),
            len(out),
        )
        if idx > 0 and out[idx - 1].lstrip().startswith(";"):
            idx -= 1  # над комментарием «Keybinds — последней»
        out.insert(idx, "TestMenu : 1")
    return "\n".join(out) + "\n"


def _settings(text):
    """Окно UE4SS (консоль + Live View) — открыто: туда меню пишет ответы."""
    out = []
    for ln in text.splitlines():
        key = ln.split("=")[0].strip()
        if key == "GuiConsoleEnabled":
            ln = "GuiConsoleEnabled = 1"
        elif key == "GuiConsoleVisible":
            ln = "GuiConsoleVisible = 1"
        out.append(ln)
    return "\n".join(out) + "\n"


def deploy_file(path):
    win64 = shipping_dir(path)
    if not win64:
        raise ValueError(f"не нашёл <Проект>-Win64-Shipping.exe: {path}")
    ac = anticheat(win64)
    if ac:
        raise ValueError(
            f"в игре античит ({ac}) — не ставлю: инъекция в онлайн-игру с античитом грозит баном"
        )
    if not os.path.isdir(UE4SS):
        raise FileNotFoundError(
            "нет tools/unity/UE4SS — запусти tools/fetch_unity_tools.py UE4SS"
        )
    if not os.path.exists(os.path.join(win64, LIST)) and os.path.exists(
        os.path.join(win64, "UE4SS.dll")
    ):
        raise ValueError(
            "в игре уже стоит свой UE4SS — не трогаю (TestMenu можно положить в его Mods/ вручную)"
        )
    added = []
    for base, _dirs, files in os.walk(UE4SS):
        for fn in files:
            src = os.path.join(base, fn)
            rel = os.path.relpath(src, UE4SS)
            if rel in (".version", "Changelog.md", "README.md"):
                continue
            dst = os.path.join(win64, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if rel in ("UE4SS-settings.ini", os.path.join("Mods", "mods.txt")):
                with open(src, encoding="utf-8-sig") as f:
                    text = f.read()
                text = _settings(text) if rel.endswith(".ini") else _mods_txt(text)
                with open(dst, "w", encoding="utf-8") as f:
                    f.write(text)
            else:
                shutil.copy2(src, dst)
            added.append(rel.replace("\\", "/"))
    for base, _dirs, files in os.walk(MOD):
        for fn in files:
            src = os.path.join(base, fn)
            rel = os.path.join("Mods", "TestMenu", os.path.relpath(src, MOD))
            dst = os.path.join(win64, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            added.append(rel.replace("\\", "/"))
    with open(os.path.join(win64, "Mods", "TestMenu", "enabled.txt"), "w") as f:
        f.write("")
    added.append("Mods/TestMenu/enabled.txt")
    with open(os.path.join(win64, LIST), "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(set(added))) + "\n")
    return (
        f"{win64}: UE4SS + TestMenu установлены. В игре: Ctrl+Shift+H — справка; рядом откроется "
        "окно UE4SS (ответы меню, консоль, Live View — значения игры)"
    )


def remove_file(path):
    win64 = shipping_dir(path)
    if not win64 or not os.path.exists(os.path.join(win64, LIST)):
        return f"{path}: меню не ставилось (нет {LIST})"
    with open(os.path.join(win64, LIST), encoding="utf-8") as f:
        files = [x for x in f.read().splitlines() if x]
    n = 0
    for r in files:
        p = os.path.join(win64, r)
        if os.path.isfile(p):
            os.remove(p)
            n += 1
    # логи и кэш UE4SS, профиль меню; пустые папки модов
    for extra in ("UE4SS.log", os.path.join("Mods", "TestMenu", "profile.txt")):
        p = os.path.join(win64, extra)
        if os.path.isfile(p):
            os.remove(p)
    for base, dirs, _files in sorted(
        os.walk(os.path.join(win64, "Mods")), key=lambda x: -len(x[0])
    ):
        if os.path.isdir(base) and not os.listdir(base):
            os.rmdir(base)
    os.remove(os.path.join(win64, LIST))
    return f"{win64}: UE4SS и TestMenu убраны ({n} файлов)"


def is_installed(path):
    win64 = shipping_dir(path)
    return bool(win64) and os.path.exists(os.path.join(win64, LIST))


def is_current(path):
    win64 = shipping_dir(path)
    try:
        with (
            open(
                os.path.join(win64, "Mods", "TestMenu", "Scripts", "main.lua"), "rb"
            ) as a,
            open(os.path.join(MOD, "Scripts", "main.lua"), "rb") as b,
        ):
            return a.read() == b.read()
    except (OSError, TypeError):
        return False


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("target", help="папка игры Unreal или её .exe")
    ap.add_argument("--remove", action="store_true")
    a = ap.parse_args()
    print(remove_file(a.target) if a.remove else deploy_file(a.target))
