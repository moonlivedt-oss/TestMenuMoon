#!/usr/bin/env python3
"""CLI: сгенерировать per-game zzz_testmenu_data.rpy из манифеста.
Логика — в tmkit.generate. Запуск:  python gen_data.py [N ...]  (без аргументов — все)."""
import sys

from tmkit import generate, report
from tmkit.games import GAMES
from tmkit.cli import parse_game_targets

if __name__ == "__main__":
    targets = parse_game_targets(__doc__, lambda: sorted(GAMES))
    for i in targets:
        try:
            generate.gen(i)
        except Exception as e:
            report.err(i, str(e))
    sys.exit(report.exit_code())
