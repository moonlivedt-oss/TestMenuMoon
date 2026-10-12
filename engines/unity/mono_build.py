"""Сборка меню для Mono-игр Unity (engines/unity/mono/TestMenuMono.cs) при установке.

Компилятор — csc.exe из .NET Framework 4 (есть в каждой Windows), ссылки — библиотеки самой
игры (<игра>_Data/Managed: mscorlib, UnityEngine*) и BepInEx 5. Так плагин совпадает с версией
Unity и рантаймом игры без готовых сборок под каждую.
"""
import glob
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "mono", "TestMenuMono.cs")


def csc_path():
    win = os.environ.get("WINDIR", r"C:\Windows")
    for fw in ("Framework64", "Framework"):
        p = os.path.join(win, "Microsoft.NET", fw, "v4.0.30319", "csc.exe")
        if os.path.isfile(p):
            return p
    return None


def references(managed, bepinex_core):
    """Список /r: — только то, что нужно плагину (без кода самой игры)."""
    refs = []
    names = ("mscorlib.dll", "System.dll", "System.Core.dll", "netstandard.dll")
    for n in names:
        p = os.path.join(managed, n)
        if os.path.isfile(p):
            refs.append(p)
    refs += sorted(glob.glob(os.path.join(glob.escape(managed), "UnityEngine*.dll")))
    refs.append(os.path.join(bepinex_core, "BepInEx.dll"))
    return refs


def build(managed, bepinex_core, out_dll, source=SOURCE):
    """Собрать плагин. -> (ok, текст вывода компилятора)."""
    csc = csc_path()
    if not csc:
        return False, "нет csc.exe (.NET Framework 4) — собрать меню для Mono нечем"
    refs = references(managed, bepinex_core)
    args = [csc, "/nologo", "/target:library", "/optimize+", "/out:" + out_dll]
    if os.path.isfile(os.path.join(managed, "mscorlib.dll")):
        args += ["/noconfig", "/nostdlib+"]  # mscorlib игры, а не системный
    args += ["/r:" + r for r in refs]
    args.append(source)
    p = subprocess.run(args, capture_output=True)
    text = (p.stdout + p.stderr).decode("cp866", "replace")
    return p.returncode == 0 and os.path.isfile(out_dll), text
