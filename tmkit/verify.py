#!/usr/bin/env python3
"""Ядро verify: файлы меню на месте + Ren'Py lint не ругается на наш код.

Сначала мгновенная офлайн-проверка данных (tmkit.validate), затем — что файлы
меню установлены, и только потом (дорого) запуск `renpy lint` установленной игры.
Логика вынесена сюда, чтобы root verify.py был тонкой обёрткой.
"""
import os, subprocess

from tmkit.games import GAMES, ROOTS, launcher, python_exe, basedir
from tmkit import validate, report

ENGINE_FILE = "zzz_testmenu_engine.rpy"
DATA_FILE = "zzz_testmenu_data.rpy"


def verify(i):
    """Проверить установку меню в game_{i} и прогнать lint (печатает статус)."""
    root = ROOTS[i]
    # быстрая офлайн-проверка данных — мгновенно, ДО запуска Ren'Py-lint
    issues = validate.check_game(GAMES[i].get("stats", []), GAMES[i].get("actions", []),
                                 GAMES[i].get("accent"), GAMES[i].get("tweak"))
    if issues:
        report.warn(i, f"данные: проблем {len(issues)} (подробнее — validate.py)")
        for s in issues:
            report.detail(s)

    # data-файл необязателен: после «быстрой установки» в игре только движок (режим «авто»)
    if not os.path.exists(os.path.join(root, ENGINE_FILE)):
        report.bad(i, f"движок меню не установлен (запусти deploy.py {i})")
        return
    if not os.path.exists(os.path.join(root, DATA_FILE)):
        report.note(i, "data-файла нет — меню работает в режиме «авто»")
    py, lnch, bd = python_exe(i), launcher(i), basedir(i)
    if not py or not lnch:
        report.warn(i, "файлы на месте, но нет python/launcher для lint")
        return
    try:
        r = subprocess.run([py, os.path.basename(lnch), ".", "lint"],
                           cwd=bd, capture_output=True, text=True, errors="ignore", timeout=600)
    except subprocess.TimeoutExpired:
        report.warn(i, "lint не уложился в таймаут (большая игра)")
        return
    out = (r.stdout or "") + (r.stderr or "")
    bad = [l.strip() for l in out.splitlines() if "zzz_testmenu" in l.lower()]
    if bad:
        report.bad(i, "lint нашёл проблемы в меню:")
        for b in bad[:5]:
            report.detail(b)
    elif "Statistics" in out:
        report.ok(i, "установлено, lint чист")
    else:
        report.warn(i, "lint не завершился штатно — проверь вручную")
