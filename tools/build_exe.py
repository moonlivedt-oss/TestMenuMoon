#!/usr/bin/env python3
"""Собрать студию в один TestMenuStudio.exe (PyInstaller) — без установки Python и PyQt6.

    pip install pyinstaller
    python tools/build_exe.py            -> TestMenuStudio.exe в корне проекта

Внутри .exe — Python, PyQt6 и код (tmkit, tmstudio, tm.py). Рядом с .exe должны лежать
файлы проекта, которые меню ставит в игры и правит студия: engines/, assets/, tools/,
tweaks/, tmkit/games_example.py (манифест tmkit/games_data.py создастся сам). Поэтому
раздавать — весь проект (архивом с GitHub) + этот .exe в его корне.

Свой манифест (games_data.py) и архив игр в .exe не попадают: они читаются с диска.
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "TestMenuStudio"
WORK = os.path.join(ROOT, "build", "pyinstaller")


def icon():
    """assets/tm_icon.png -> .ico (Pillow); нет Pillow — сборка без значка."""
    png = os.path.join(ROOT, "assets", "tm_icon.png")
    ico = os.path.join(WORK, "tm_icon.ico")
    try:
        from PIL import Image

        os.makedirs(WORK, exist_ok=True)
        Image.open(png).save(ico, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        return ico
    except Exception as e:
        print(f"[!] без значка: {e}")
        return None


def main():
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        NAME,
        "--distpath",
        os.path.join(WORK, "dist"),
        "--workpath",
        WORK,
        "--specpath",
        WORK,
        "--paths",
        ROOT,
        "--collect-submodules",
        "tmkit",
        "--collect-submodules",
        "tmstudio",
        "--hidden-import",
        "tm",
        # модули движков (engines/*.py) и unrpyc грузятся с диска во время работы — их импорты
        # из стандартной библиотеки должны быть внутри .exe
        *sum(
            (
                ["--hidden-import", m]
                for m in (
                    "zipfile",
                    "struct",
                    "hashlib",
                    "codecs",
                    "html",
                    "argparse",
                    "tempfile",
                    "ctypes",
                    "winreg",
                    "pickletools",
                    "threading",
                    "runpy",
                    "urllib.request",
                    "shutil",
                    "glob",
                    "importlib.util",
                    "dataclasses",
                    "typing",
                    "pathlib",
                    "traceback",
                    "multiprocessing",
                )
            ),
            [],
        ),
        # личное: свой манифест и архив игр читаются с диска, в .exe их быть не должно
        "--exclude-module",
        "tmkit.games_data",
        "--exclude-module",
        "tmkit.games_archive",
        "--exclude-module",
        "tkinter",
    ]
    ico = icon()
    if ico:
        args += ["--icon", ico]
    args.append(os.path.join(ROOT, "tools", "exe_main.py"))
    print("$ " + " ".join(args[3:]))
    r = subprocess.run(args, cwd=ROOT)
    if r.returncode:
        sys.exit(r.returncode)
    out = os.path.join(ROOT, NAME + ".exe")
    shutil.copy2(os.path.join(WORK, "dist", NAME + ".exe"), out)
    print(f"[OK] {out}  ({os.path.getsize(out) / 1e6:.1f} МБ)")


if __name__ == "__main__":
    main()
