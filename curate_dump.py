#!/usr/bin/env python3
"""CLI: собрать кандидатов статов/инвентаря по каждой игре в cand/game_X.txt.
Логика — в tmkit.analysis. Без аргументов курирует реально распакованные папки в D:/_ta."""
import sys

from tmkit import analysis, report
from tmkit.paths import ANA_BASE
from tmkit.cli import parse_game_targets

if __name__ == "__main__":
    targets = parse_game_targets(__doc__, analysis.extracted_games)
    if not targets:
        print(f"Нет распакованных игр в {ANA_BASE} — сначала запусти collect_sources.py")
    for i in targets:
        try:
            analysis.dump(i)
        except Exception as e:
            report.err(i, str(e))
    sys.exit(report.exit_code())
