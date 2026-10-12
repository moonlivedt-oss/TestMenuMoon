#!/usr/bin/env python3
"""CLI: разложить движок + per-game data в папку game/ каждой игры.
Заодно сносит устаревшие zzz_testmenu_*.rpyc, чтобы Ren'Py пересобрал .rpy.
Логика — в tmkit.deploy. Запуск:  python deploy.py [N ...]  (без аргументов — все)."""
import sys

from tmkit import deploy, report
from tmkit.games import ROOTS
from tmkit.cli import parse_game_targets

if __name__ == "__main__":
    targets = parse_game_targets(__doc__, lambda: sorted(ROOTS))
    for i in targets:
        try:
            deploy.deploy(i)
        except Exception as e:
            report.err(i, str(e))
    sys.exit(report.exit_code())
