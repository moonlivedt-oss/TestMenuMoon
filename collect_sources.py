#!/usr/bin/env python3
"""CLI: для каждой игры — распаковать .rpa (скрипты), декомпилировать .rpyc,
собрать .rpy в ANA_BASE/game_X. Логика — в tmkit.collect.
Запуск:  python collect_sources.py [N ...]  (без аргументов — все)."""
import sys

from tmkit import collect, report
from tmkit.games import ROOTS
from tmkit.cli import parse_game_targets

if __name__ == "__main__":
    targets = parse_game_targets(__doc__, lambda: sorted(ROOTS))
    for i in targets:
        try:
            collect.collect(i)
        except Exception as e:
            report.err(i, str(e))
    sys.exit(report.exit_code())
