#!/usr/bin/env python3
"""Скачать инструменты для Unity-игр в tools/unity/ (сами файлы в git не кладутся).

    AssetRipper    — открыть и выгрузить ресурсы игры (картинки, тексты, сцены)
    Cpp2IL         — имена классов/полей IL2CPP-игры (GameAssembly.dll + global-metadata.dat)
    BepInEx 6 BE   — загрузчик плагинов для Unity IL2CPP (ставится в папку игры)
    UnityExplorer  — плагин BepInEx: окно в игре — объекты, поля, значения на лету
    BepInEx 5 (x64 и x86) и UnityExplorer Mono — то же для Mono-игр Unity
    UE4SS          — загрузчик модов для Unreal Engine 4/5 (кладётся в tools/unity/UE4SS)
    UTMT_CLI       — UndertaleModTool CLI: внедрение меню в data.win игр GameMaker 2.3+

Ссылки и версии закреплены ниже; обновить — поменять URL и запустить снова
(уже скачанное пропускается). Запуск:  python tools/fetch_unity_tools.py
"""

import os
import shutil
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "tools", "unity")

TOOLS = [
    (
        "AssetRipper",
        "2.0.0",
        "https://github.com/AssetRipper/AssetRipper/releases/download/2.0.0/AssetRipper_win_x64.zip",
    ),
    (
        "Cpp2IL",
        "2022.1.0-pre-release.21",
        "https://github.com/SamboyCoding/Cpp2IL/releases/download/2022.1.0-pre-release.21/"
        "Cpp2IL-2022.1.0-pre-release.21-Windows.exe",
    ),
    (
        "BepInEx_IL2CPP",
        "6.0.0-be.788",
        "https://builds.bepinex.dev/projects/bepinex_be/788/"
        "BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.788%2B5b766a3.zip",
    ),
    (
        "UnityExplorer",
        "4.13.6",
        "https://github.com/yukieiji/UnityExplorer/releases/download/v4.13.6/"
        "UnityExplorer.BepInEx.Unity.IL2CPP.CoreCLR.zip",
    ),
    # Mono-игры (есть <игра>_Data/Managed, нет GameAssembly.dll): BepInEx 5 и UnityExplorer для него
    (
        "BepInEx5_x64",
        "5.4.23.2",
        "https://github.com/BepInEx/BepInEx/releases/download/v5.4.23.2/BepInEx_win_x64_5.4.23.2.zip",
    ),
    # 32-битные Mono-игры (UnityPlayer.dll под x86): свой winhttp.dll (doorstop) той же разрядности
    (
        "BepInEx5_x86",
        "5.4.23.2",
        "https://github.com/BepInEx/BepInEx/releases/download/v5.4.23.2/BepInEx_win_x86_5.4.23.2.zip",
    ),
    (
        "UnityExplorer_Mono",
        "4.9.0",
        "https://github.com/sinai-dev/UnityExplorer/releases/download/4.9.0/UnityExplorer.BepInEx5.Mono.zip",
    ),
    # Unreal Engine 4/5: UE4SS — загрузчик Lua-модов, консоль и Live View объектов
    (
        "UE4SS",
        "3.0.1",
        "https://github.com/UE4SS-RE/RE-UE4SS/releases/download/v3.0.1/UE4SS_v3.0.1.zip",
    ),
    # GameMaker 2.3+: UndertaleModTool CLI собирает data.win с объектом меню
    (
        "UTMT_CLI",
        "0.9.2.0",
        "https://github.com/UnderminersTeam/UndertaleModTool/releases/download/0.9.2.0/UTMT_CLI_v0.9.2.0-Windows.zip",
    ),
]


def fetch(name, version, url):
    out = os.path.join(DEST, name)
    stamp = os.path.join(out, ".version")
    if (
        os.path.exists(stamp)
        and open(stamp, encoding="utf-8").read().strip() == version
    ):
        print(f"[=] {name} {version} уже есть")
        return
    os.makedirs(out, exist_ok=True)
    fn = os.path.join(out, url.rsplit("/", 1)[-1].replace("%2B", "+"))
    print(f"[>] {name} {version}: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "TestMenuMoon"})
    with urllib.request.urlopen(req, timeout=120) as r, open(fn, "wb") as f:
        shutil.copyfileobj(r, f)
    print(f"    {os.path.getsize(fn) / 1e6:.1f} МБ")
    if fn.endswith(".zip"):
        with zipfile.ZipFile(fn) as z:
            z.extractall(out)
        os.remove(fn)
    with open(stamp, "w", encoding="utf-8") as f:
        f.write(version)


if __name__ == "__main__":
    only = set(sys.argv[1:])
    for name, version, url in TOOLS:
        if not only or name in only:
            fetch(name, version, url)
    print(f"готово: {DEST}")
