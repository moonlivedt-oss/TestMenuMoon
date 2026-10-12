#!/usr/bin/env python3
"""CLI: проверить установку тест-меню — файлы на месте + lint игры без ошибок в нашем коде.
Логика — в tmkit.verify. Автоопределяет лаунчер и python.exe через tmkit.games.
Использование:  python verify.py            (все — у больших игр lint долгий)
                python verify.py 4 6 8 10   (конкретные)"""
import sys

from tmkit import verify, report
from tmkit.games import GAMES
from tmkit.cli import parse_game_targets

if __name__ == "__main__":
    targets = parse_game_targets(
        __doc__, lambda: sorted(GAMES),
        epilog="Без аргументов проверяются все игры — у больших lint долгий.",
    )
    for i in targets:
        try:
            verify.verify(i)
        except Exception as e:
            report.err(i, str(e))
    sys.exit(report.exit_code())
