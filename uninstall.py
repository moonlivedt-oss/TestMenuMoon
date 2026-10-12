#!/usr/bin/env python3
"""CLI: удалить тест-меню из игры — снести zzz_testmenu_*.rpy/.rpyc и tm_ui/.
Логика — в tmkit.deploy. Использование:  python uninstall.py 3 5 7  |  python uninstall.py ALL"""
import argparse

import sys

from tmkit import deploy, report
from tmkit.games import GAMES

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("games", nargs="+", metavar="N|ALL",
                        help="номера игр для удаления, или ALL — из всех игр манифеста")
    args = parser.parse_args()
    if any(g.upper() == "ALL" for g in args.games):
        targets = sorted(GAMES)
    else:
        try:
            targets = [int(g) for g in args.games]
        except ValueError:
            parser.error("номера игр должны быть числами (или ALL)")
    for i in targets:
        try:
            deploy.uninstall(i)
        except Exception as e:
            report.err(i, str(e))
    sys.exit(report.exit_code())
