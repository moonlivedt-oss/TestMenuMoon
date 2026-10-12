#!/usr/bin/env python3
"""Ядро tm.py collect: подготовить исходники игры для анализа.

Для игры N: распаковать её .rpa (только скрипты), скопировать уже лежащие .rpy/.rpyc,
затем декомпилировать вендоренным unrpyc те .rpyc, у которых нет парного .rpy.
Результат — дерево .rpy в ANA_BASE/game_N (короткий путь ради Windows MAX_PATH).
"""

import os, sys, glob, shutil, subprocess

from tmkit.games import ROOTS
from tmkit.paths import ANA_BASE, UNRPYC
from tmkit import rpa
from tmkit import report

# файлы самого тест-меню в игре — не исходники игры, в анализ не берём
OWN_PREFIX = "zzz_testmenu_"


def collect(i):
    """Собрать распакованные .rpy игры game_{i} в ANA_BASE/game_{i} (печатает статус)."""
    root = ROOTS[i]
    if not os.path.isdir(root):
        report.bad(i, f"нет папки игры ({root}) — проверь root в манифесте")
        return
    ana = f"{ANA_BASE}/game_{i}"
    if os.path.exists(ana):
        shutil.rmtree(ana)
    os.makedirs(ana, exist_ok=True)

    # 1. извлечь все .rpa (только скрипты) — в процессе, без subprocess
    for arch in glob.glob(f"{glob.escape(root)}/**/*.rpa", recursive=True):
        try:
            rpa.extract(arch, ana, scripts_only=True)
        except Exception as e:
            report.detail(f"extract {os.path.basename(arch)}: {e}")

    # 2. скопировать уже присутствующие .rpy и .rpyc из дерева игры
    for ext in ("rpy", "rpyc"):
        for src in glob.glob(f"{glob.escape(root)}/**/*.{ext}", recursive=True):
            if os.path.basename(src).startswith(OWN_PREFIX):
                continue
            rel = os.path.relpath(src, root)
            dest = os.path.join(ana, "src", rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)

    # 3. декомпилировать .rpyc, у которых нет парного .rpy
    if os.path.exists(UNRPYC):
        # вывод unrpyc — utf-8 с именами файлов игры; дефолтная cp1251 на нём падает
        r = subprocess.run(
            [sys.executable, UNRPYC, ana],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        )
        out = (r.stdout or "").strip()
        tail = out.splitlines()[-1] if out else (r.stderr or "").strip()[:80]
    else:
        tail = f"нет {UNRPYC} — .rpyc не декомпилированы"

    n_rpy = len(glob.glob(f"{glob.escape(ana)}/**/*.rpy", recursive=True))
    report.info(i, f"{n_rpy} .rpy ready  (unrpyc tail: {tail})")
