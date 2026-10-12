#!/usr/bin/env python3
"""Unity: поставить/снять загрузчик модов, UnityExplorer (F7 — все объекты и поля) и наше меню
(Shift+T / F9).

  IL2CPP (есть GameAssembly.dll) — BepInEx 6 + меню engines/unity/plugin (собранное заранее);
  Mono (есть <игра>_Data/Managed) — BepInEx 5 + меню engines/unity/mono, которое собирается при
  установке системным csc.exe против библиотек самой игры (engines/unity/mono_build.py).

Файлы берутся из tools/unity/ (их скачивает tools/fetch_unity_tools.py). Список всего,
что положено в игру, пишется в tm_unity_files.txt — снятие удаляет ровно это, плюс
папки, которые BepInEx создал сам при первом запуске (BepInEx/interop, cache, logs…).
Если у игры уже есть свой загрузчик (winhttp.dll / version.dll) — установка отказывается.

Первый запуск игры после установки долгий (1–3 минуты): BepInEx скачивает базовые
библиотеки Unity нужной версии и строит interop-сборки. Дальше — как обычно.

Использование:
    python inject.py <папка игры | .exe>
    python inject.py <...> --remove
"""

import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "_shared"))
import tm_load  # noqa: E402

tm_load.use_tmkit()
BEPINEX = os.path.join(ROOT, "tools", "unity", "BepInEx_IL2CPP")
EXPLORER = os.path.join(ROOT, "tools", "unity", "UnityExplorer")
BEPINEX5 = os.path.join(ROOT, "tools", "unity", "BepInEx5_x64")
BEPINEX5_X86 = os.path.join(ROOT, "tools", "unity", "BepInEx5_x86")  # 32-битные Mono-игры
EXPLORER5 = os.path.join(ROOT, "tools", "unity", "UnityExplorer_Mono")
MONO_DLL = "TestMenu.Mono.dll"
# своё меню (engines/unity/plugin, собрать: dotnet build -c Release)
MENU_DLL = os.path.join(HERE, "plugin", "bin", "TestMenu.Unity.dll")
LIST = "tm_unity_files.txt"
LOADERS = ("winhttp.dll", "version.dll")


def _words_json():
    # tm_words.json — тот же словарь, что у меню Godot и движка Ren'Py
    from tmkit import naming

    return naming.words_json()


def game_dir(path):
    """Папка Unity-игры (рядом *_Data и UnityPlayer.dll) или ValueError."""
    d = os.path.dirname(path) if os.path.isfile(path) else path
    if not os.path.isdir(d) or not os.path.exists(os.path.join(d, "UnityPlayer.dll")):
        raise ValueError(f"не похоже на игру Unity (нет UnityPlayer.dll): {path}")
    return d


def backend(d):
    """'il2cpp' (GameAssembly.dll) или 'mono' (*_Data/Managed)."""
    if os.path.exists(os.path.join(d, "GameAssembly.dll")):
        return "il2cpp"
    return "mono"


def unity_version(d):
    for name in os.listdir(d):
        if name.endswith("_Data"):
            p = os.path.join(d, name, "globalgamemanagers")
            if os.path.exists(p):
                import re

                with open(p, "rb") as f:
                    m = re.search(rb"(20\d\d|6\d\d\d)\.\d+\.\d+[abfp]\d+", f.read(4096))
                return m.group(0).decode() if m else None
    return None


def _copy_tree(src, dst_root, rel, added):
    for base, _dirs, files in os.walk(src):
        for fn in files:
            s = os.path.join(base, fn)
            r = (
                os.path.join(rel, os.path.relpath(s, src))
                if rel
                else os.path.relpath(s, src)
            )
            t = os.path.join(dst_root, r)
            os.makedirs(os.path.dirname(t), exist_ok=True)
            shutil.copy2(s, t)
            added.append(r.replace("\\", "/"))


def managed_dir(d):
    for name in os.listdir(d):
        p = os.path.join(d, name, "Managed")
        if name.endswith("_Data") and os.path.isdir(p):
            return p
    return None


def is_64bit(d):
    """Разрядность игры по заголовку PE у UnityPlayer.dll."""
    import struct

    try:
        with open(os.path.join(d, "UnityPlayer.dll"), "rb") as f:
            f.seek(0x3C)
            pe = struct.unpack("<I", f.read(4))[0]
            f.seek(pe + 4)
            return struct.unpack("<H", f.read(2))[0] == 0x8664
    except OSError:
        return True


def _mono_signature():
    """Что должно лежать в игре: исходник меню + словарь (для is_current)."""
    import hashlib

    with open(os.path.join(HERE, "mono", "TestMenuMono.cs"), "rb") as f:
        src = f.read()
    return hashlib.sha1(src + _words_json().encode("utf-8")).hexdigest()


def _deploy_mono(d):
    # загрузчик (winhttp.dll) должен совпадать с разрядностью игры; сам плагин — AnyCPU
    bits = "x64" if is_64bit(d) else "x86"
    bepinex5 = BEPINEX5 if bits == "x64" else BEPINEX5_X86
    managed = managed_dir(d)
    if not managed:
        raise ValueError("нет <игра>_Data/Managed — это не Mono-игра Unity")
    if not os.path.isdir(bepinex5) or not os.path.isdir(EXPLORER5):
        raise FileNotFoundError(
            f"нет tools/unity/{os.path.basename(bepinex5)} — запусти tools/fetch_unity_tools.py"
        )
    if not os.path.exists(os.path.join(d, LIST)):
        for ld in LOADERS:
            if os.path.exists(os.path.join(d, ld)):
                raise ValueError(f"в игре уже есть {ld} (свой загрузчик модов) — не трогаю")
    mono_build = tm_load.load("unity", "mono_build.py")

    menu = os.path.join(d, "BepInEx", "plugins", "TestMenu")
    os.makedirs(menu, exist_ok=True)
    ok, log = mono_build.build(managed, os.path.join(bepinex5, "BepInEx", "core"), os.path.join(menu, MONO_DLL))
    if not ok:
        with open(os.path.join(menu, "build_error.txt"), "w", encoding="utf-8") as f:
            f.write(log)
        raise ValueError("меню не собралось под эту игру — подробности в BepInEx/plugins/TestMenu/build_error.txt")
    added = ["BepInEx/plugins/TestMenu/" + MONO_DLL]
    for name in os.listdir(bepinex5):
        if name in (".version", "changelog.txt"):
            continue
        s = os.path.join(bepinex5, name)
        if os.path.isdir(s):
            _copy_tree(s, d, name, added)
        else:
            shutil.copy2(s, os.path.join(d, name))
            added.append(name)
    _copy_tree(os.path.join(EXPLORER5, "plugins"), d, "BepInEx/plugins", added)
    with open(os.path.join(menu, "tm_words.json"), "w", encoding="utf-8") as f:
        f.write(_words_json())
    with open(os.path.join(menu, "tm_source.sha1"), "w", encoding="utf-8") as f:
        f.write(_mono_signature())
    added += ["BepInEx/plugins/TestMenu/tm_words.json", "BepInEx/plugins/TestMenu/tm_source.sha1"]
    with open(os.path.join(d, LIST), "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(set(added))) + "\n")
    v = unity_version(d) or "?"
    return (f"{d}: меню + BepInEx 5 + UnityExplorer установлены (Unity {v}, Mono {bits}). "
            "В игре: Shift+T / F9 — меню, F7 — UnityExplorer")


def _unhide(d):
    """Скрытые файлы меню (пользователь их спрятал) Windows не даёт перезаписать: снимаем
    атрибут на время установки. -> пути, которым его вернуть."""
    import ctypes

    k32 = ctypes.windll.kernel32
    paths = []
    lst = os.path.join(d, LIST)
    if os.path.exists(lst):
        with open(lst, encoding="utf-8") as f:
            paths += [os.path.join(d, x) for x in f.read().splitlines() if x]
        paths.append(lst)
    for top in ("BepInEx", "winhttp.dll", "doorstop_config.ini", ".doorstop_version", "dotnet"):
        paths.append(os.path.join(d, top))
    for top in ("BepInEx", "dotnet"):
        for base, dirs, files in os.walk(os.path.join(d, top)):
            paths += [os.path.join(base, x) for x in dirs + files]
    hidden = []
    for p in dict.fromkeys(paths):
        a = k32.GetFileAttributesW(p)
        if a != 0xFFFFFFFF and a & 2:
            k32.SetFileAttributesW(p, a & ~2)
            hidden.append(p)
    return hidden


def _rehide(paths):
    if not paths:
        return
    import ctypes

    k32 = ctypes.windll.kernel32
    for p in paths:
        a = k32.GetFileAttributesW(p)
        if a != 0xFFFFFFFF:
            k32.SetFileAttributesW(p, a | 2)


def deploy_file(path):
    d = game_dir(path)
    hidden = _unhide(d) if os.name == "nt" else []
    try:
        return _deploy(d)
    finally:
        _rehide(hidden)


def _deploy(d):
    if backend(d) != "il2cpp":
        return _deploy_mono(d)
    if not os.path.isdir(BEPINEX) or not os.path.isdir(EXPLORER):
        raise FileNotFoundError("нет tools/unity — запусти tools/fetch_unity_tools.py")
    if not os.path.exists(os.path.join(d, LIST)):
        for ld in LOADERS:
            if os.path.exists(os.path.join(d, ld)):
                raise ValueError(
                    f"в игре уже есть {ld} (свой загрузчик модов) — не трогаю"
                )
    added = []
    for name in os.listdir(BEPINEX):
        if name in (".version", "changelog.txt"):
            continue
        s = os.path.join(BEPINEX, name)
        if os.path.isdir(s):
            _copy_tree(s, d, name, added)
        else:
            shutil.copy2(s, os.path.join(d, name))
            added.append(name)
    _copy_tree(os.path.join(EXPLORER, "plugins"), d, "BepInEx/plugins", added)
    menu = os.path.join(d, "BepInEx", "plugins", "TestMenu")
    os.makedirs(menu, exist_ok=True)
    has_menu = os.path.exists(MENU_DLL)
    if has_menu:
        shutil.copy2(MENU_DLL, os.path.join(menu, "TestMenu.Unity.dll"))
        added.append("BepInEx/plugins/TestMenu/TestMenu.Unity.dll")
    with open(os.path.join(menu, "tm_words.json"), "w", encoding="utf-8") as f:
        f.write(_words_json())
    added.append("BepInEx/plugins/TestMenu/tm_words.json")
    with open(os.path.join(d, LIST), "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(set(added))) + "\n")
    v = unity_version(d) or "?"
    if not has_menu:
        # свежий клон: плагин не собран — ставим только BepInEx + UnityExplorer и говорим об этом
        return (
            f"{d}: BepInEx + UnityExplorer установлены (Unity {v}), но своего меню нет — "
            "не собран engines/unity/plugin (dotnet build -c Release), потом переустанови. "
            "В игре: F7 — UnityExplorer"
        )
    return (
        f"{d}: меню + BepInEx + UnityExplorer установлены (Unity {v}). Первый запуск долгий "
        "(BepInEx готовит библиотеки). В игре: Shift+T / F9 — меню, F7 — UnityExplorer"
    )


def remove_file(path):
    d = game_dir(path)
    lst = os.path.join(d, LIST)
    if not os.path.exists(lst):
        return f"{d}: меню не ставилось (нет {LIST})"
    with open(lst, encoding="utf-8") as f:
        files = [x for x in f.read().splitlines() if x]
    n = 0
    for r in files:
        p = os.path.join(d, r)
        if os.path.isfile(p):
            os.remove(p)
            n += 1
    for extra in ("BepInEx/LogOutput.log", "BepInEx/ErrorLog.log"):
        if os.path.isfile(os.path.join(d, extra)):
            os.remove(os.path.join(d, extra))
    # BepInEx — целиком наша папка (игре она не нужна); dotnet — тоже наш
    for top in ("BepInEx", "dotnet"):
        if os.path.isdir(os.path.join(d, top)):
            shutil.rmtree(os.path.join(d, top))
    os.remove(lst)
    return f"{d}: BepInEx и UnityExplorer убраны ({n} файлов)"


def is_current(path):
    """Меню в игре — текущая сборка плагина и словаря (иначе студия покажет «устарело»)."""
    try:
        d = game_dir(path)
        menu = os.path.join(d, "BepInEx", "plugins", "TestMenu")
        if backend(d) == "mono":
            with open(os.path.join(menu, "tm_source.sha1"), encoding="utf-8") as f:
                return f.read().strip() == _mono_signature()
        with (
            open(os.path.join(menu, "TestMenu.Unity.dll"), "rb") as a,
            open(MENU_DLL, "rb") as b,
        ):
            if a.read() != b.read():
                return False
        with open(os.path.join(menu, "tm_words.json"), encoding="utf-8") as f:
            return f.read() == _words_json()
    except (ValueError, OSError):
        return False


def is_installed(path):
    try:
        return os.path.exists(os.path.join(game_dir(path), LIST))
    except ValueError:
        return False


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("target", help="папка Unity-игры или её .exe")
    ap.add_argument("--remove", action="store_true")
    a = ap.parse_args()
    print(remove_file(a.target) if a.remove else deploy_file(a.target))
