#!/usr/bin/env python3
"""CLI: офлайн-проверка данных манифеста (без запуска Ren'Py).
Код действий компилируется, нет дублей путей/кодов, метки на месте — быстрый
пре-флайт перед deploy. Запуск:  python validate.py [N ...]  (без аргументов — все)."""
import sys

from tmkit import validate, manifest, report
from tmkit.cli import parse_game_targets


def check(i, games):
    g = games[i]
    issues = validate.check_game(g.get("stats", []), g.get("actions", []), g.get("accent"), g.get("tweak"))
    if issues:
        report.bad(i, f"проблем: {len(issues)}")
        for s in issues:
            report.detail(s)
    else:
        report.ok(i, "данные чисты")
    return len(issues)


if __name__ == "__main__":
    games, _G, _ACCENT = manifest.load_games()
    targets = parse_game_targets(__doc__, lambda: sorted(games))
    total = 0
    for i in targets:
        if i in games:
            total += check(i, games)
        else:
            report.warn(i, "нет в манифесте")
    print(f"\nвсего проблем: {total}")
    sys.exit(report.exit_code())
