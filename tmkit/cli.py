#!/usr/bin/env python3
"""Общие помощники для CLI-обёрток в корне проекта (argparse)."""
import argparse


def parse_game_targets(description, default_factory, *, epilog=None):
    """Разобрать номера игр из argv.

    Позиционные аргументы — номера игр (int). Без аргументов возвращается
    default_factory() (напр. все игры из манифеста). Бесплатно даёт -h/--help
    и внятную ошибку на нечисловой ввод.
    """
    parser = argparse.ArgumentParser(
        description=description, epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "games", nargs="*", type=int, metavar="N",
        help="номера игр; без аргументов — все по умолчанию",
    )
    args = parser.parse_args()
    return args.games or default_factory()
