#!/usr/bin/env python3
"""Lint меню на настоящем Ren'Py: копия the_question из SDK + меню (как tm.py quick) + renpy lint.

    python tools/ci_renpy_lint.py D:/_sdk/renpy-8.5.3-sdk [ещё SDK …]

Код возврата 1, если lint ругается на файлы меню (zzz_testmenu_*) или не дошёл до конца.
В CI SDK скачивается с renpy.org (см. .github/workflows/tests.yml).
"""

import glob
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tmkit import deploy  # noqa: E402


def sdk_python(sdk):
    """python.exe SDK: 8.x — lib/py3-…, 7.5+ — lib/py2-…, старые — lib/windows-…."""
    for pat in ("py3-windows-x86_64", "py2-windows-x86_64", "windows-x86_64", "windows-i686"):
        p = os.path.join(sdk, "lib", pat, "python.exe")
        if os.path.isfile(p):
            return p
    hits = glob.glob(os.path.join(sdk, "lib", "*", "python.exe"))
    return hits[0] if hits else None


def lint(sdk):
    py = sdk_python(sdk)
    if not py:
        print(f"[X] {sdk}: нет python.exe в lib/")
        return False
    tmp = tempfile.mkdtemp(prefix="tm_lint_")
    try:
        proj = os.path.join(tmp, "the_question")
        shutil.copytree(os.path.join(sdk, "the_question"), proj)
        game = os.path.join(proj, "game")
        # копия вне SDK: версию Ren'Py берём у самого SDK (для copypaste и т.п.)
        text = deploy.engine_text(os.path.join(sdk, "game"))
        deploy.quick_install(game)
        with open(os.path.join(game, deploy.ENGINE_NAME), "w", encoding="utf-8", newline="") as f:
            f.write(text)
        r = subprocess.run([py, "-O", "renpy.py", proj, "lint"], cwd=sdk, capture_output=True, timeout=900)
        out = (r.stdout + r.stderr).decode("utf-8", "replace")
        bad = [ln.strip() for ln in out.splitlines() if "zzz_testmenu" in ln.lower()]
        name = os.path.basename(os.path.normpath(sdk))
        if bad:
            print(f"[X] {name}: lint нашёл проблемы в меню:")
            for ln in bad[:20]:
                print("     " + ln)
            return False
        if "Statistics" not in out:
            print(f"[X] {name}: lint не дошёл до конца (код {r.returncode}):")
            print("\n".join("     " + ln for ln in out.strip().splitlines()[-15:]))
            return False
        print(f"[OK] {name}: lint чист")
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    ok = all([lint(s) for s in sys.argv[1:]])
    sys.exit(0 if ok else 1)
